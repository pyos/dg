import dis
import types
import itertools
import collections


CO_OPTIMIZED = 1   # does not use slow locals
CO_NEWLOCALS = 2   # has a local namespace
CO_VARARGS   = 4   # accepts any amount of positional arguments
CO_VARKWARGS = 8   # accepts any amount of keyword arguments
CO_NESTED    = 16  # uses free variables
CO_GENERATOR = 32  # uses YIELD_VALUE/YIELD_FROM
CO_NOFREE    = 64  # does not export free variables

EXTENDED_ARG      = dis.opmap['EXTENDED_ARG']
DEREF_OPCODE_DIFF = dis.opmap['LOAD_DEREF'] - dis.opmap['LOAD_FAST']

hasconst = set(dis.hasconst)
hasfree  = set(dis.hasfree)
hasname  = set(dis.hasname)
hasjrel  = set(dis.hasjrel)
hasjabs  = set(dis.hasjabs)
haslocal = set(dis.haslocal)
hascmp   = set(dis.hascompare)
hasjump  = hasjrel | hasjabs


def opcode(op, arg):

    return (opcode(EXTENDED_ARG, arg >> 16) if arg >= 0x10000 else b'') + \
           bytes([op, arg % 256, arg // 256 % 256])


def codelen(seq):

    return sum(
        1 if c < dis.HAVE_ARGUMENT else 3 + abs(int(v).bit_length() - 1) // 16 * 3
        for c, v in seq
    )


class IndexedSet (dict):
    '''
        A set that automatically assigns indices to its items.
        Well, not actually a set, but a hashmap.

        NOTE Python uses (==) to check for equality; therefore, some objects
          may be considered equal when they are not (e.g. 1 == 1.0).

    '''

    def __missing__(self, k):

        self[k] = len(self)
        return self[k]

    @property
    def sorted(self):
        '''Get items from this set in the order they were inserted in.'''

        return tuple(sorted(self, key=self.__getitem__))


class LazyInt:
    '''An "integer" that calculates its value on demand.'''

    def __init__(self, calculate):

        super().__init__()

        self.calculate = calculate

    def __int__(self):

        return self.calculate(self)


class JumpObject (LazyInt):
    '''An argument to a jump opcode.

        Call this object to set the jump target (in case of a forward jump)
        or a jump source (for a reverse jump.)

    '''

    def __init__(self, code, reverse, absolute=False, op=None):

        super().__init__(lambda self: self._value)

        self.op    = op
        self.code  = code
        self.start = len(code)

        assert not reverse or absolute, 'reverse => absolute'
        self.absolute = absolute
        self.reverse  = reverse
        self._value   = -1

        reverse or code.append((self.op, self))

    def __call__(self):

        assert self._value == -1, 'this jump is already targeted'

        self._value = codelen(
            itertools.islice(self.code,
                0          if self.absolute else self.start + 1,
                self.start if self.reverse  else len(self.code)
            )
        )

        if self.absolute:

            sz = 0x10000

            while self._value > sz:

                # This jump needs to account for itself.
                self._value += 3  # 1-byte opcode + 2-byte argument
                sz <<= 16

        self.reverse and self.code.append((self.op, self._value))


class MutableCode:
    '''Something like `types.CodeType`, only mutable.

        :param isfunc: whether to add function-specific flags (OPTIMIZED and NEWLOCALS)
        :param a:      list of positional argument names
        :param kw:     list of keyword-only argument names
        :param va:     a singleton list with a starred argument name, if any
        :param vkw:    a singleton list with a double-starred argument name, if any
        :param cell:   parent code object (e.g. enclosing function)

    '''

    def __init__(self, name, isfunc=False, a=(), kw=(), va=(), vkw=(), cell=None):

        super().__init__()

        self.name     = name
        self.qualname = (cell.qualname + (cell.qualname and '.') + ('<locals>.' * bool(cell.flags & CO_OPTIMIZED)) if cell else '') + name * bool(isfunc)

        self.argc   = len(a)
        self.kwargc = len(kw)

        # * slow locals are stored in a hash map, fast ones - in a `PyObject**`.
        self.names    = IndexedSet()  # globals, slow* locals, attributes, modules
        self.consts   = IndexedSet()  # (constant, type) pairs
        self.freevars = IndexedSet()  # locals exported into enclosed code objects
        self.cellvars = IndexedSet()  # locals imported from enclosing code objects
        self.varnames = IndexedSet(   # fast* locals and function arguments
            zip(itertools.chain(a, kw, va, vkw), itertools.count()))

        self.cell     = cell
        self.enclosed = cell.varnames.keys() | cell.enclosed if cell else set()

        self.flags = (
           (CO_OPTIMIZED | CO_NEWLOCALS) * bool(isfunc)
          | CO_VARARGS   * bool(va)
          | CO_VARKWARGS * bool(vkw)
        )

        # This is tracked separately from `flags` because slow locals
        # may be reenabled at runtime by using `STORE_LOCALS`.
        self.slowlocals = not isfunc

        self.bytecode = collections.deque()  # (opcode, argument) pairs
        self.f_locals = collections.defaultdict(set)
        self.m_depth  = 0   # maximum value of `depth` reached
        self.depth    = 0   # approx. amount of items on the value stack

        self.filename = '<generated>'
        self.lineno   = 1
        self.lnotab   = collections.deque()

    def mark(self, e):
        '''Mark the location of a `StructMixIn` in lnotab.

            NOTE this method assumes all objects you pass to it
              are taken from the same file.

        '''

        if not self.lnotab:

            self.filename = e.location.filename
            self.lineno   = e.location.start[1]
            return self.lnotab.append((0, 0, self.lineno, 0))

        byteoffabs = len(self.bytecode)
        lineoffabs = e.location.start[1]
        byteoff = codelen(itertools.islice(self.bytecode, self.lnotab[-1][3], None))
        lineoff = lineoffabs - self.lnotab[-1][2]

        if lineoff > 0 and byteoff > 0:

            self.lnotab.extend((0, 255, lineoffabs, byteoffabs) for _ in range(lineoff // 256))
            self.lnotab.extend((255, 0, lineoffabs, byteoffabs) for _ in range(byteoff // 256))
            self.lnotab.append((byteoff % 256, lineoff % 256, lineoffabs, byteoffabs))

    def cellify(self, name):
        '''Replace all uses of a fast local with a corresponding `cellvar`.

            If the fast local does not exist, the call to this function
            will be ignored.

        '''

        for i, c in self.f_locals[name]:

            self.bytecode[i] = c, self.cellvars[name]

        return name

    def append(self, name, value=0, delta=0):
        '''
            Append a new opcode to the bytecode sequence given its name and argument.
            Return the `JumpObject` for jumps, garbage value otherwise.

            :param name:  opcode, as a string in `dis.opmap`.
            :param value: argument, see below.
            :param delta: how the opcode affects the size of the value stack.

            Argument type is opcode-dependent.

              argumentless opcodes    object; ignored
              relative jumps          object; ignored
              LOAD_CONST              object; something to push onto the stack
              name-related stuff      str; name of the variable to use
              COMPARE_OP              str; the operator to use
              absolute jumps          int; if negative, jump direction is reversed
              everything else         int; added as-is

        '''

        code = dis.opmap[name]

        self.flags      |= name in ('YIELD_VALUE', 'YIELD_FROM') and CO_GENERATOR
        self.slowlocals |= name == 'STORE_LOCALS'

        self.m_depth += max(0, delta)
        self.depth   += delta

        if code in hasjump:

            return JumpObject(self.bytecode, value < 0, code in hasjabs, op=code)

        if code in haslocal:

            self.f_locals[value].add((len(self.bytecode), code + DEREF_OPCODE_DIFF))

        self.bytecode.append((code,
            dis.cmp_op.index(value)           if code in hascmp else
            self.names   [value]              if code in hasname else
            self.varnames[value]              if code in haslocal else
            self.consts  [value, type(value)] if code in hasconst else
            value                             if code not in hasfree else

            # Free and cell variables use the same index space.
            LazyInt(lambda _, i=self.freevars[value]: i + len(self.cellvars))
            if value in self.enclosed and value not in self.varnames else self.cellvars[value]
        ))

    @property
    def compiled(self):
        '''Freeze the code object, creating `types.CodeType`.'''

        return types.CodeType(
            self.argc, self.kwargc, len(self.varnames),
            self.m_depth, self.flags | CO_NESTED * bool(self.freevars)
                                     | CO_NOFREE * (not self.cellvars),
            b''.join(opcode(op, int(arg)) if op >= dis.HAVE_ARGUMENT else bytes([op]) for op, arg in self.bytecode),
            tuple(x for x, _ in self.consts.sorted),
            self.names.sorted,
            self.varnames.sorted,
            self.filename, self.name, self.lineno,
            bytes(a for b in self.lnotab for a in b[:2]),
            self.freevars.sorted,
            self.cellvars.sorted
        )
