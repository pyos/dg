import math
import types
import struct
import opcode
import functools
import itertools

from .. import const


iindex  = lambda it, v: next(i for i, q in enumerate(it) if q == v)
delay   = lambda f, g=None: type('delay', (), {'__int__': f, '__call__': g})()
codelen = lambda cs: sum(
    1 + (  # opcode length
        c >= opcode.HAVE_ARGUMENT and (  # 0 if no argument
            2 +  # argument length
            3 * int(math.log(int(v) or 1, 0x10000)) # EXTENDED_ARGs
        )
    ) for c, v in cs
)


class MutableCode:

    def __init__(self, isfunc, args=(), kwargs=(), varargs=(), varkwargs=(), cell=None):

        super().__init__()

        self.argc = len(args)
        self.kwargc = len(kwargs)

        self.names = []
        self.consts = []
        self.freevars = []
        self.cellvars = []
        self.varnames = list(itertools.chain(args, kwargs, varargs, varkwargs))

        self.cellnames = set(cell.varnames) | cell.cellnames if cell else set()
        self.slowlocals = not isfunc

        self.flags  = const.CO.OPTIMIZED | const.CO.NEWLOCALS if isfunc else 0
        self.flags |= const.CO.VARARGS   if varargs   else 0
        self.flags |= const.CO.VARKWARGS if varkwargs else 0
        self.bytecode = []

        self.stacksize = self.cstacksize = 0

        self.filename = '<generated>'
        self.lineno   = 1
        self.lnotab   = {}

    def __getattr__(self, name):

        if name.isupper():

            return functools.partial(self.append, name)

        raise AttributeError(name)

    def mark(self, e):

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

    def use(self, v, id, *containers):

        if not isinstance(v, str) and self.consts not in containers:

            raise Exception(const.ERR.NONCONST_ATTR)

        for i, ct in enumerate(containers):

            i < id and v in ct and ct.remove(v)

            if i >= id and v in ct:

                break

        else:

            containers[id].append(v)

        return delay(lambda _: iindex(itertools.chain.from_iterable(containers), v))

    def jump(self, absolute, reverse=False):

        start = len(self.bytecode)

        def finish(v):

            v.end = len(self.bytecode)
            hasattr(v, '_c') and delattr(v, '_c')  # Empty the value cache.

        # Returns 0 if recurring and the actual jump target otherwise.
        # Will fail given the length of bytecode is big enough
        # (i.e. the target for this jump >= 0x10000)
        #
        # FIXME given the size constraints of `int`, the value may increase
        #       by 3 (possibly 6). Repeating the calculation
        #       2 more times may fix the issue.
        #
        def to_int(v):

            if not hasattr(v, '_c'):

                v._c = 0
                v._c = codelen(
                    self.bytecode[0 if absolute else v.end + 1:start] if reverse else
                    self.bytecode[0 if absolute else start + 1:v.end]
                )

            return v._c

        return delay(to_int, finish)

    def append(self, name, value=0, delta=0):

        code = opcode.opmap[name]

        if code == opcode.opmap['YIELD_VALUE']:

            self.flags |= const.CO.GENERATOR

        if code == opcode.opmap['STORE_LOCALS']:

            self.slowlocals = True

        if code in (opcode.hasjrel + opcode.hasjabs) and value < 0:

            # Reverse jump.
            jmp = self.jump(absolute=code in opcode.hasjabs, reverse=True)
            return lambda: (jmp(), self.bytecode.append((code, jmp)))

        self.bytecode.append((
            code,
            0                                 if code <  opcode.HAVE_ARGUMENT else
            self.jump(absolute=False)         if code in opcode.hasjrel  else
            self.jump(absolute=True)          if code in opcode.hasjabs  else
            self.use(value, 0, self.names)    if code in opcode.hasname  else
            self.use(value, 0, self.varnames) if code in opcode.haslocal else
            self.use(value, 0, self.consts)   if code in opcode.hasconst else
            self.use(value, value in self.cellnames, self.cellvars, self.freevars)
                if code in opcode.hasfree else
            opcode.cmp_op.index(value) if code in opcode.hascompare else
            value
        ))

        self.cstacksize += delta
        self.stacksize = max(self.stacksize, self.cstacksize)
        return self.bytecode[-1][1]

    def make_bytecode(self):

        for code, value in self.bytecode:

            value = int(value)
            oparg = [value % 0x10000]

            while value > 0x10000:

                value //= 0x10000
                oparg.insert(0, value % 0x10000)

            for arg in oparg[:-1]:

                yield struct.pack('=BH', opcode.opmap['EXTENDED_ARG'], arg)

            yield struct.pack(*
                ('=BH', code, oparg[-1]) if code >= opcode.HAVE_ARGUMENT else
                ('=B',  code)
            )

    def compile(self, name='<lambda>'):

        return types.CodeType(
            self.argc,
            self.kwargc,
            len(self.varnames),
            self.stacksize,
            self.flags | (
                const.CO.NESTED if self.freevars else
                0               if self.cellvars else
                const.CO.NOFREE
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
