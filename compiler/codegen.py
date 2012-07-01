import math
import types
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

    # Add an entry to the lineno table.
    #
    # :param struct: a dg output structure that will produce an instruction.
    #
    def mark(self, e):

        self.lnotab[len(self.bytecode)] = e.reparse_location.start[1]

    def make_lnotab(self):

        e = 0, self.lineno

        for q in sorted(self.lnotab.items()):

            if q[1] > e[1]:

                dl = q[1] - e[1]
                do = codelen(self.bytecode[e[0]:q[0]])

                for _ in range(do // 256):

                    yield 255
                    yield 0

                for _ in range(dl // 256):

                    yield 0
                    yield 255

                yield do % 256
                yield dl % 256
                e = q

    # Add a name/constant to a name container.
    #
    # :param v: the variable name/constant value to append.
    #
    # :param id: index of the preferred container.
    #
    # :param containers: mutually exclusive containers sorted by their priority.
    #
    # :return: delayed computation of index of `v` in the sum of `containers`.
    #
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

    def jump(self, absolute):

        start  = len(self.bytecode)
        finish = lambda v: setattr(v, 'end', len(self.bytecode))
        to_int = lambda v: (
            # Returns 0 if recurring and the actual jump target otherwise.
            # Will fail given the length of bytecode is big enough
            # (i.e. the target for this jump >= 0x10000)
            #
            # FIXME given the size constraints of `int`, the value may increase
            #       by 3 (possibly 6). Repeating the calculation
            #       2 more times may fix the issue.
            #
            hasattr(v, '_c') or (
              setattr(v, '_c', 0),
              setattr(v, '_c', codelen(self.bytecode[0 if absolute else start:v.end])),
            ), v._c
        )[-1]
        return delay(to_int, finish)

    # Add an instruction to a mutable code object.
    #
    # :param name: the instruction name.
    #
    # :param value: an argument to that instruction, if necessary.
    #
    def append(self, name, value=0, delta=0):

        code = opcode.opmap[name]

        if code == opcode.opmap['YIELD_VALUE']:

            self.flags |= const.CO.GENERATOR

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

            for q in range(value and int(math.log(value, 0x10000)), 0, -1):

                yield opcode.opmap['EXTENDED_ARG']
                yield value // (0x10000 ** q) %  0x100
                yield value // (0x10000 ** q) // 0x100
                value %= (0x10000 ** q)

            yield code

            if code >= opcode.HAVE_ARGUMENT:

                # XXX see if it uses native byte ordering.
                # FIXME if it does, this will break on big-endian platforms.
                yield value %  0x100
                yield value // 0x100

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
            bytes(self.make_bytecode()),
            tuple(self.consts),
            tuple(self.names),
            tuple(self.varnames),
            self.filename,
            name,
            self.lineno,
            bytes(self.make_lnotab()),
            tuple(self.freevars),
            tuple(self.cellvars)
        )
