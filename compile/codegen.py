import dis
import math
import types
import struct
import functools

from .. import const

EXTENDED_ARG = functools.partial(struct.pack, '=BH', dis.opmap['EXTENDED_ARG'])

nsplit  = lambda x, q: nsplit(x // q, q) + [x % q] if x >= q else [x]
delay   = lambda f, g=None: type('delay', (), {'__int__': f, '__call__': g})()
codelen = lambda cs: sum(
    1 + (c >= dis.HAVE_ARGUMENT and (3 * len(nsplit(int(v), 0x10000)) - 1))
    for c, v in cs
)


class MutableCode:

    def __init__(self, isfunc, args=(), kwargs=(), varargs=(), varkwargs=(), cell=None):

        super().__init__()

        self.argc   = len(args)
        self.kwargc = len(kwargs)

        self.names    = []
        self.consts   = []
        self.freevars = []
        self.cellvars = []
        self.varnames = list(args) + list(kwargs) + list(varargs) + list(varkwargs)

        self.flags  = const.CO.OPTIMIZED | const.CO.NEWLOCALS if isfunc else 0
        self.flags |= const.CO.VARARGS   if varargs   else 0
        self.flags |= const.CO.VARKWARGS if varkwargs else 0
        self.bytecode   = []
        self.stacksize  = 0
        self.cstacksize = 0

        self.filename = '<generated>'
        self.lineno   = 1
        self.lnotab   = {}

        # Names of variables that could be added to `freevars`.
        self.cellnames = set(cell.varnames) | cell.cellnames if cell else set()

        # Whether to use the `f_locals` hashmap instead of fast locals.
        # Enabled for global NS and functions that do STORE_LOCALS.
        self.slowlocals = not isfunc

  ### LNOTAB

    def mark(self, e):

        '''Add an entry to the line number table.

        :param e: the statement that will generate the next instruction.

        '''

        self.lnotab[len(self.bytecode)] = e.reparse_location.start[1]

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

  ### OPCODE ARGUMENTS

    def name(self, v, container):

        if not isinstance(v, str) and container is not self.consts:

            # FIXME that should be done in `compile.__init__`, not here.
            raise Exception(const.ERR.NONCONST_ATTR)

        v in container or container.append(v)
        return container.index(v)

    def freevar(self, v):

        if v not in self.freevars:
        
            if v in self.cellnames:

                self.freevars.append(v)

            elif v not in self.cellvars:

                self.cellvars.append(v)

        # Free and cell variables use the same index space, so we
        # don't know their indices right now.
        return delay(lambda _: (self.cellvars + self.freevars).index(v))

    def jump(self, absolute, reverse=False):

        start = len(self.bytecode)

        def finish(v):

            v.end = len(self.bytecode)
            # Empty the value cache.
            hasattr(v, '_c') and delattr(v, '_c')

        def to_int(v):

            if not (reverse or hasattr(v, 'end')):

                raise Exception(dis.opname[self.bytecode[start][0]])

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

  ### OPCODE MANIPULATION

    def __getattr__(self, name):

        if name.isupper():

            # `MutableCode.SOME_OPCODE_NAME(...)` is an alias to
            # `MutableCode.append('SOME_OPCODE_NAME', ...)`
            return functools.partial(self.append, name)

        raise AttributeError(name)

    def append(self, name, value=0, delta=0):

        '''Append a new opcode to the bytecode sequence.

        :param name: name of the bytecode (should be in `dis.opmap`.)

        :param value: opcode-dependent.

          argumentless opcodes: ignored
          relative jumps:: ignored
          absolute jumps:: the jump is in reverse direction when negative
          name ops::       name of the variable to use
          LOAD_CONST::     the value to load
          COMPARE_OP::     the operator name
          all others::     passed as is (must be an integer)

        :param delta: how much items will this opcode push onto the stack.

        :return: the argument to that opcode.

        '''

        self.flags      |= name == 'YIELD_VALUE' and const.CO.GENERATOR
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
            self.jump(absolute=False)       if code in dis.hasjrel    else
            self.jump(absolute=True)        if code in dis.hasjabs    else
            self.name(value, self.names)    if code in dis.hasname    else
            self.name(value, self.varnames) if code in dis.haslocal   else
            self.name(value, self.consts)   if code in dis.hasconst   else
            self.freevar(value)             if code in dis.hasfree    else
            dis.cmp_op.index(value)         if code in dis.hascompare else
            value
        ))

        self.stacksize  += max(0, delta)
        self.cstacksize += delta
        return self.bytecode[-1][1]

    def make_bytecode(self):

        for code, value in self.bytecode:

            oparg = nsplit(int(value), 0x10000)
          # yield from map(EXTENDED_ARG, oparg[:-1])
            yield b''.join(map(EXTENDED_ARG, oparg[:-1]))
            yield struct.pack(*
                ('=BH', code, oparg[-1]) if code >= dis.HAVE_ARGUMENT else
                ('=B',  code)
            )

  ### MAIN

    def compile(self, name='<lambda>'):

        '''Compile the mutable code into an immutable code.

        :param name: name of the function/module/other stuff this code implements.

        :return: a Python code object.

        '''

        return types.CodeType(
            self.argc,
            self.kwargc,
            len(self.varnames),
            self.stacksize,
            self.flags | (
                const.CO.NESTED if self.freevars else
                const.CO.NOFREE if not self.cellvars else 0
            ),
            b''.join(self.make_bytecode()),
            tuple(self.consts),
            tuple(self.names),
            tuple(self.varnames),
            self.filename,
            name,
            self.lineno,
            b''.join(self.make_lnotab()),
            tuple(self.freevars),
            tuple(self.cellvars)
        )
