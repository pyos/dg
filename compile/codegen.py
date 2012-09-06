import dis
import types
import struct
import functools
import itertools
import collections

CO_OPTIMIZED = 1
CO_NEWLOCALS = 2
CO_VARARGS   = 4
CO_VARKWARGS = 8
CO_NESTED    = 16
CO_GENERATOR = 32
CO_NOFREE    = 64

OPCODE   = struct.Struct('<B').pack
OPCODE_A = struct.Struct('<BH').pack
EXTEND_A = functools.partial(OPCODE_A, dis.opmap['EXTENDED_ARG'])

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

        self.names    = collections.defaultdict(itertools.count().__next__)
        self.consts   = collections.defaultdict(itertools.count().__next__)
        self.freevars = collections.defaultdict(itertools.count().__next__)
        self.cellvars = collections.defaultdict(itertools.count().__next__)
        self.varnames = collections.defaultdict(itertools.count().__next__)

        for name in itertools.chain(args, kwargs, varargs, varkwargs):

            self.varnames[name]

        self.flags = (
            CO_OPTIMIZED | CO_NEWLOCALS * bool(isfunc)
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

    def make_lnotab(self):

        offset = 0
        lineno = self.lineno

        for offset_, lineno_ in sorted(self.lnotab.items()):

            if lineno_ > lineno:

                bytediff = codelen(self.bytecode[offset:offset_])
                linediff = lineno_ - lineno
                yield b'\xff\x00' * (bytediff // 256)
                yield b'\x00\xff' * (linediff // 256)
                yield bytes((bytediff % 256, linediff % 256))
                offset, lineno = offset_, lineno_

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
    # :param value: opcode-dependent.
    #
    #   argumentless opcodes: ignored
    #   relative jumps:: ignored
    #   absolute jumps:: the jump is in reverse direction when negative
    #   name ops::       name of the variable to use
    #   LOAD_CONST::     the value to load
    #   COMPARE_OP::     the operator name
    #   all others::     passed as is (must be an integer)
    #
    # :param delta: how much items will this opcode push onto the stack.
    #
    # :return: the argument to that opcode.
    #
    def append(self, name, value=0, delta=0):

        self.flags      |= name in ('YIELD_VALUE', 'YIELD_FROM') and CO_GENERATOR
        self.slowlocals |= name == 'STORE_LOCALS'

        code = dis.opmap[name]

        if code in dis.hasjabs and value < 0:

            # Reverse jump.
            # Note that relative jumps can't be in reverse direction.
            jmp = self.jump(absolute=True, reverse=True)
            # No need to call `jmp`, it will ignore that anyway.
            return lambda: self.bytecode.append((code, jmp))

        self.bytecode.append((
            code,
            dis.cmp_op.index(value)         if code in dis.hascompare else
            self.jump(absolute=False)       if code in dis.hasjrel    else
            self.jump(absolute=True)        if code in dis.hasjabs    else
            self.names[value]               if code in dis.hasname    else
            self.varnames[value]            if code in dis.haslocal   else
            self.consts[value]              if code in dis.hasconst   else
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

    def make_bytecode(self):

        for code, value in self.bytecode:

            oparg = nsplit(int(value), 0x10000)
          # yield from map(EXTEND_A, oparg[:-1])
            yield b''.join(map(EXTEND_A, oparg[:-1]))
            yield (OPCODE_A if code >= dis.HAVE_ARGUMENT else OPCODE)(
                code,
                *(oparg[-1],) if code >= dis.HAVE_ARGUMENT else ()
            )

    def compile(self, name='<lambda>'):

        return types.CodeType(
            self.argc,
            self.kwargc,
            len(self.varnames),
            self.m_depth,
            self.flags | (
                CO_NESTED * bool(self.freevars)
              | CO_NOFREE * (not self.cellvars)
            ),
            b''.join(self.make_bytecode()),
            tuple(sorted(self.consts,   key=self.consts.__getitem__)),
            tuple(sorted(self.names,    key=self.names.__getitem__)),
            tuple(sorted(self.varnames, key=self.varnames.__getitem__)),
            self.filename,
            name,
            self.lineno,
            b''.join(self.make_lnotab()),
            tuple(sorted(self.freevars, key=self.freevars.__getitem__)),
            tuple(sorted(self.cellvars, key=self.cellvars.__getitem__))
        )
