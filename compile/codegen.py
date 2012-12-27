import dis
import types
import itertools


CO_OPTIMIZED = 1
CO_NEWLOCALS = 2
CO_VARARGS   = 4
CO_VARKWARGS = 8
CO_NESTED    = 16
CO_GENERATOR = 32
CO_NOFREE    = 64


nsplit  = lambda x, q: nsplit(x // q, q) + [x % q] if x >= q else [x]
delay   = lambda f, g=None: type('delay', (), {'__int__': f, '__call__': g})()
codelen = lambda cs: sum(
    1 + (c >= dis.HAVE_ARGUMENT and (((int(v) or 1).bit_length() - 1) // 16 * 3 + 2))
    for c, v in cs
)


class MutableCode:

    def __init__(self, isfunc=False, args=(), kwargs=(), varargs=(), varkwargs=(), cell=None):

        super().__init__()

        self.argc   = len(args)
        self.kwargc = len(kwargs)

        self.names    = PartialOrderedMap()
        self.consts   = PartialOrderedMap()
        self.freevars = PartialOrderedMap()
        self.cellvars = PartialOrderedMap()
        self.varnames = PartialOrderedMap(zip(
            itertools.chain(args, kwargs, varargs, varkwargs),
            itertools.count()
        ))

        self.flags = (
           (CO_OPTIMIZED | CO_NEWLOCALS) * bool(isfunc)
          | CO_VARARGS   * bool(varargs)
          | CO_VARKWARGS * bool(varkwargs)
        )

        self.bytecode = []
        self.m_depth  = 0
        self.depth    = 0
        self.filename = '<generated>'
        self.lineno   = 1
        self.lnotab   = {}

        # Names of variables that could be added to `freevars`.
        self.cellnames = cell.varnames.keys() | cell.cellnames if cell else set()
        self.cell = cell

        # Whether to use the `f_locals` hashmap instead of fast locals.
        # Enabled for global NS and functions that do STORE_LOCALS.
        self.slowlocals = not isfunc

        hasattr(cell, 'cellhook') and cell.cellhook(self)

    def mark(self, e):

        self.lnotab[len(self.bytecode)] = e.location.start[1]

    def jump(self, absolute, reverse=False):

        start = len(self.bytecode)

        def finish(v):

            v.end = len(self.bytecode)
            # Empty the value cache.
            hasattr(v, '_c') and delattr(v, '_c')

        def to_int(v):

            if not hasattr(v, '_c'):

                # codelen() may call this function again,
                # so we need to prevent the infinite recursion.
                v._c = 0
                v._c = codelen(
                    self.bytecode[0:start] if reverse else
                    self.bytecode[0 if absolute else start + 1:v.end]
                )

            return v._c

        return delay(to_int, finish)

    # Synchronize fast local variable with its cell container.
    #
    # `name` need not be in `varnames` - it will be ignored if it isn't.
    #
    def cellify(self, name):

        if name in self.varnames:

            opmap = {
              # old opcode: new opcode
                dis.opmap['LOAD_FAST']:  dis.opmap['LOAD_DEREF']
              , dis.opmap['STORE_FAST']: dis.opmap['STORE_DEREF']
            }

            for offset, (opcode, argument) in enumerate(self.bytecode):

                if opcode in opmap and argument == self.varnames[name]:

                    del self.bytecode[offset]
                    self.bytecode.insert(offset, (opmap[opcode], self.cellvars[name]))

        return name

    # Append a new opcode to the bytecode sequence.
    #
    # :param name: name of the bytecode (should be in `dis.opmap`.)
    #
    # :param value: opcode-dependent::
    #
    #   argumentless opcodes | ignored
    #   relative jumps       | -
    #   absolute jumps       | the jump is in reverse direction when true
    #   name operations      | name of the variable to use
    #   LOAD_CONST           | the value to load
    #   COMPARE_OP           | the operator name
    #   all others           | an integer argument
    #
    # :param delta: how much items will this opcode push onto the stack.
    #
    # :return: opcode-dependent::
    #
    #   forward jumps  | a callable that sets the target
    #   backward jumps | a callable that inserts the jump opcode
    #   all others     | pretty much meaningless integer
    #
    def append(self, name, value=0, delta=0):

        self.flags      |= name in ('YIELD_VALUE', 'YIELD_FROM') and CO_GENERATOR
        self.slowlocals |= name == 'STORE_LOCALS'

        code = dis.opmap[name]

        if code in dis.hasjabs and value < 0:

            # Reverse jump.
            # Note that relative jumps can't be in reverse direction.
            jmp = self.jump(absolute=True, reverse=True)
            return lambda: self.bytecode.append((code, jmp))

        self.bytecode.append((code,
            dis.cmp_op.index(value)         if code in dis.hascompare else
            self.jump(absolute=False)       if code in dis.hasjrel    else
            self.jump(absolute=True)        if code in dis.hasjabs    else
            self.names[value]               if code in dis.hasname    else
            self.varnames[value]            if code in dis.haslocal   else
            self.consts[value, type(value)] if code in dis.hasconst   else
            (
                # Free and cell variables use the same index space, so we
                # don't know their indices right now.
                delay(lambda _, i=self.freevars[value]: i + len(self.cellvars))
                if value in self.cellnames else self.cellvars[value]
            )                               if code in dis.hasfree    else
            value
        ))

        self.m_depth += max(0, delta)
        self.depth   += delta
        return self.bytecode[-1][1]

    def compile(self, name):

        lnotab   = []
        coderes  = []
        offset_q = 0
        lineno_q = self.lineno

        for btoffset, (code, value) in enumerate(self.bytecode):

            lineno = self.lnotab.get(btoffset, 0)

            if lineno > lineno_q:

                offset = len(coderes)
                lnotab.extend((offset - offset_q) // 256 * [255, 0])
                lnotab.extend((lineno - lineno_q) // 256 * [0, 255])
                lnotab.extend([(offset - offset_q) % 256, (lineno - lineno_q) % 256])
                offset_q, lineno_q = offset, lineno

            *ext, arg = nsplit(int(value), 0x10000)

            for e in ext:

                coderes.extend([dis.opmap['EXTENDED_ARG'], e % 256, e // 256])

            coderes.extend([code] + [arg % 256, arg // 256] * (code >= dis.HAVE_ARGUMENT))

        return types.CodeType(
            self.argc,
            self.kwargc,
            len(self.varnames),
            self.m_depth,
            self.flags
              | CO_NESTED * bool(self.freevars)
              | CO_NOFREE * (not self.cellvars), bytes(coderes),
            tuple(x for x, _ in self.consts.sorted),
            tuple(self.names.sorted),
            tuple(self.varnames.sorted),
            self.filename, name,
            self.lineno, bytes(lnotab),
            tuple(self.freevars.sorted),
            tuple(self.cellvars.sorted)
        )


class PartialOrderedMap (dict):

    def __missing__(self, k):

        self[k] = len(self)
        return self[k]

    @property
    #
    # Sort keys by creation order.
    #
    def sorted(self):

        return sorted(self, key=self.__getitem__)
