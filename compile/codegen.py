import dis
import types
import itertools


CO_OPTIMIZED = 1   # does not use slow locals
CO_NEWLOCALS = 2   # has a local namespace
CO_VARARGS   = 4   # accepts any amount of positional arguments
CO_VARKWARGS = 8   # accepts any amount of keyword arguments
CO_NESTED    = 16  # uses free variables
CO_GENERATOR = 32  # uses YIELD_VALUE/YIELD_FROM
CO_NOFREE    = 64  # does not export free variables


#
# A set that automatically assigns indices to its items.
# Well, not actually a set, but a hashmap.
#
# NOTE Python uses (==) to check for equality; therefore, some objects
#   may be considered equal when they are not (e.g. 1 == 1.0).
#
class IndexedSet (dict):

    def __missing__(self, k):

        self[k] = len(self)
        return self[k]

    @property
    # sorted :: [object]
    #
    # Items from this set in the same order they were inserted in.
    #
    def sorted(self):

        return sorted(self, key=self.__getitem__)


#
# An "integer" that actually calculates its value on demand.
#
class LazyInt:

    def __init__(self, calculate):

        super().__init__()

        self.calculate = calculate

    def __int__(self):

        return self.calculate(self)


#
# An argument to a jump opcode.
# Calling this object will set the jump target.
#
class JumpObject (LazyInt):

    def __init__(self, code, reverse, absolute=False, op=None):

        super().__init__(lambda self: self._value)

        self.op    = op
        self.code  = code
        self.start = len(code.bytecode)

        assert not reverse or absolute, 'reverse => absolute'
        self.absolute = absolute
        self.reverse  = reverse
        self._value   = -1

        reverse or self.code.bytecode.append((self.op, self))

    def __call__(self):

        assert self._value == -1, 'this jump is already targeted'

        self._value = sum(
            1 if c < dis.HAVE_ARGUMENT else 3 + abs(int(v).bit_length() - 1) // 16 * 3
            for c, v in self.code.bytecode[
                0          if self.absolute else self.start + 1:
                self.start if self.reverse  else len(self.code.bytecode)
            ]
        )

        if self.absolute:

            sz = 0x10000

            while self._value > sz:

                # This jump needs to account for itself.
                self._value += 3  # 1-byte opcode + 2-byte argument
                sz <<= 16

        self.reverse and self.code.bytecode.append((self.op, self._value))


# MutableCode --
#   something like `types.CodeType`, only mutable, I think.
#
class MutableCode:

    # (bool, [Link], [Link], [Link], [Link], Maybe MutableCode) -> MutableCode
    #
    # isfunc    -- whether to add function-specific flags (OPTIMIZED and NEWLOCALS)
    # args      -- list of positional argument names
    # kwargs    -- list of keyword-only argument names
    # varargs   -- a singleton list with a starred argument name, if any
    # varkwargs -- a singleton list with a double-starred argument name, if any
    # cell      -- parent code object (e.g. enclosing function)
    #
    def __init__(self, isfunc=False, args=(), kwargs=(), varargs=(), varkwargs=(), cell=None):

        super().__init__()

        self.argc   = len(args)
        self.kwargc = len(kwargs)

        # * slow locals are stored in a hash map, fast ones - in a PyObject**.
        self.names    = IndexedSet()  # globals, slow* locals, attributes, modules
        self.consts   = IndexedSet()  # (constant, type) pairs
        self.freevars = IndexedSet()  # locals exported into enclosed code objects
        self.cellvars = IndexedSet()  # locals imported from enclosing code objects
        self.varnames = IndexedSet(   # fast* locals and function arguments
            zip(itertools.chain(args, kwargs, varargs, varkwargs), itertools.count())
        )

        self.cell     = cell
        self.enclosed = cell.varnames.keys() | cell.enclosed if cell else set()

        self.flags = (
           (CO_OPTIMIZED | CO_NEWLOCALS) * bool(isfunc)
          | CO_VARARGS   * bool(varargs)
          | CO_VARKWARGS * bool(varkwargs)
        )

        # This is tracked separately from `flags` because slow locals
        # may be reenabled at runtime by using `STORE_LOCALS`.
        self.slowlocals = not (self.flags & CO_OPTIMIZED)

        self.bytecode = []  # (opcode, argument) pairs
        self.m_depth  = 0   # maximum value of `depth` reached
        self.depth    = 0   # approx. amount of items on the value stack

        self.filename = '<generated>'
        self.lineno   = 1
        self.lnotab   = {}  # offset -> lineno mapping

    # mark :: StructMixIn -> NoneType
    #
    # Add a location to the code object's `lnotab`.
    #
    def mark(self, e):

        self.lnotab[len(self.bytecode)] = e.location.start[1]

    # cellify :: Link -> Link
    #
    # Replace all uses of a fast local with a corresponding `cellvar`.
    # If the fast local does not exist, the call to this function
    # will be ignored.
    #
    def cellify(self, name):

        if name in self.varnames:

            var  = self.varnames[name]
            cell = self.cellvars[var]

            for i, (op, arg) in enumerate(self.bytecode):
                # LOAD_FAST <= op <= STORE_FAST
                if 124 <= op <= 125 and arg == var:
                    # op + LOAD_DEREF - LOAD_FAST
                    self.bytecode[i] = op + 12, cell

        return name

    # append :: (str, optional object, optional int)
    #
    # Append a new opcode to the bytecode sequence given its name and argument.
    # Return the `JumpObject` for jumps, garbage value otherwise.
    #
    # Argument type is opcode-dependent.
    #
    #   argumentless opcodes    object; ignored
    #   relative jumps          object; ignored
    #   LOAD_CONST              object; something to push onto the stack
    #   name-related stuff      str; name of the variable to use
    #   COMPARE_OP              str; the operator to use
    #   absolute jumps          int; if negative, jump direction is reversed
    #   everything else         int; added as-is
    #
    # `delta` affects the size of the value stack.
    #
    def append(self, name, value=0, delta=0):

        code = dis.opmap[name]

        self.flags      |= name in ('YIELD_VALUE', 'YIELD_FROM') and CO_GENERATOR
        self.slowlocals |= name == 'STORE_LOCALS'

        self.m_depth += max(0, delta)
        self.depth   += delta

        if code in dis.hasjabs + dis.hasjrel:

            return JumpObject(self, value < 0, code in dis.hasjabs, op=code)

        self.bytecode.append((code,
            dis.cmp_op.index(value)           if code in dis.hascompare else
            self.names   [value]              if code     in dis.hasname  else
            self.varnames[value]              if code     in dis.haslocal else
            self.consts  [value, type(value)] if code     in dis.hasconst else
            value                             if code not in dis.hasfree  else

            # Free and cell variables use the same index space.
            LazyInt(lambda _, i=self.freevars[value]: i + len(self.cellvars))
            if value in self.enclosed and value not in self.varnames else self.cellvars[value]
        ))

    def compile(self, name):

        lnotab = []
        code   = []
        offset_q = 0
        lineno_q = self.lineno

        for i, (op, arg) in enumerate(self.bytecode):

            arg = int(arg)
            offset = len(code)
            lineno = self.lnotab.get(i, lineno_q)

            if lineno > lineno_q:

                lnotab +=  (offset - offset_q >> 8) * [255, 0]
                lnotab +=  (lineno - lineno_q >> 8) * [0, 255]
                lnotab += [(offset - offset_q) % 256, (lineno - lineno_q) % 256]
                offset_q, lineno_q = offset, lineno

            code.append(op)

            if op >= dis.HAVE_ARGUMENT:

                code.append(arg %  256)
                code.append(arg // 256 % 256)

                for q in range(1, 1 + abs(arg.bit_length() - 1) // 16):

                    arg //= 0x10000
                    code.insert(-q * 3, 144)  # EXTENDED_ARG
                    code.insert(-q * 3, arg % 256)
                    code.insert(-q * 3, arg // 256 % 256)

        return types.CodeType(
            self.argc, self.kwargc, len(self.varnames),
            self.m_depth, self.flags | CO_NESTED * bool(self.freevars)
                                     | CO_NOFREE * (not self.cellvars),
            bytes(code),
            tuple(x for x, _ in self.consts.sorted),
            tuple(self.names.sorted),
            tuple(self.varnames.sorted),
            self.filename, name, self.lineno, bytes(lnotab),
            tuple(self.freevars.sorted),
            tuple(self.cellvars.sorted)
        )
