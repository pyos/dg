import sys
import math
import types
import opcode
import struct
import operator
import functools
import itertools

import dg
import match
import const
import interactive


iindex  = lambda it, v: next(i for i, q in enumerate(it) if q == v)
delay   = lambda f: type('delay', (), {'__int__': f})()
unwrap  = lambda f: match.matchR(f, const.ST_CLOSURE, lambda f, q: q.pop(-1))[-1]
uncurry = lambda f, p: match.matchR(f, p, lambda f, q: q.pop(-2))[::-1]


class MutableCode:

    def __init__(self, e, argc=0, kwargc=0, locals=(), cell=(), flags=0):

        super().__init__()

        # Argument counts
        self.argc = argc
        self.kwargc = kwargc

        # Stuff used by `LOAD_*` and `STORE_*`
        self.names = []
        self.consts = []
        self.freevars = []
        self.cellvars = []
        self.varnames = list(locals)

        # Unused freevars
        self.cellnames = set(cell)
        # True if nothing should be added to `varnames`
        self.slowlocals = not flags & const.CO_NEWLOCALS

        # Main stuff
        self.flags = flags
        self.bytecode = []

        # Required & current stack depth
        self.stacksize  = 0
        self.cstacksize = 0

        # Some info about the location of this code object in source files
        self.filename = e.reparse_location.filename
        self.lineno   = e.reparse_location.start[1]
        self.lnotab   = []

    def __getattr__(self, name):

        return (
            functools.partial(self.append, name) if name.isupper() else
            super().__getattr__(name)
        )

    # Add an entry to the lineno table.
    #
    # :param struct: a dg output structure that will produce an instruction.
    #
    def mark(self, struct):

        self.lnotab.append((len(self.bytecode), struct.reparse_location.start[1]))

    def make_lnotab(self):

        e = 0, self.lineno

        for q in sorted(self.lnotab, key=lambda x: x[0]):

            if q[1] > e[1]:

                for _ in range((q[0] - e[0]) // 256):

                    yield 255
                    yield 0

                for _ in range((q[1] - e[1]) // 256):

                    yield 0
                    yield 255

                yield (q[0] - e[0]) % 256
                yield (q[1] - e[1]) % 256
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

        for i, ct in enumerate(containers):

            i < id and v in ct and ct.remove(v)

            if i >= id and v in ct:

                break

        else:

            containers[id].append(v)

        return delay(lambda _: iindex(itertools.chain.from_iterable(containers), v))

    # Add an instruction to a mutable code object.
    #
    # :param name: the instruction name.
    #
    # :param value: an argument to that instruction, if necessary.
    #
    def append(self, name, value=0, delta=0):

        code = opcode.opmap[name]

        self.bytecode.append((
            code,
            0                                 if code <  opcode.HAVE_ARGUMENT else
            self.use(value, 0, self.names)    if code in opcode.hasname  else
            self.use(value, 0, self.varnames) if code in opcode.haslocal else
            self.use(value, 0, self.consts)   if code in opcode.hasconst else
            self.use(value, value in self.cellnames, self.cellvars, self.freevars)
                if code in opcode.hasfree else
            # TODO hasjrel, hasjabs
            opcode.cmp_op.index(value) if code in opcode.hascompare else
            value
        ))

        self.cstacksize += delta
        self.stacksize = max(self.stacksize, self.cstacksize)

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
                const.CO_NESTED if self.freevars else
                0               if self.cellvars else
                const.CO_NOFREE
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


class Compiler:

    def __init__(self):

        super().__init__()

        # A mutable code object currently in use.
        self.code = None

        # An expression currently being processed by innermost `load`.
        self._loading = None

        # Predefined stuff that translates to bytecode.
        #
        # ..seealso:: `Interactive.GLOBALS`
        #
        self.builtins = {
            '':   self.call
          , '$':  self.call
          , ':':  self.call

          , ',':  self.tuple
          , '->': self.function
          , 'inherit': self.class_

          , '=':  self.store
          , '.':  lambda n, a: self.opcode('LOAD_ATTR', n, arg=a)

            # TODO various operators
          , '+':  functools.partial(self.opcode, 'BINARY_ADD')
          , '-':  functools.partial(self.opcode, 'BINARY_SUBTRACT')
          , '!!': functools.partial(self.opcode, 'BINARY_SUBSCR')
        }

    def opcode(self, opcode, *args, arg=0, delta=1):

        list(map(self.load, args))
        self.code.append(opcode, arg, -len(args) + delta)

    def tuple(self, lhs, *rhs):

        args = uncurry(lhs, const.ST_OP_TUPLE) + list(rhs)
        self.opcode('BUILD_TUPLE', *args, arg=len(args))

    def function(self, qargs, code, *_, _code_hook=lambda code: 0, _name='<lambda>'):

        # TODO generators

        args = ()  # Arguments, obv.
        defs = ()  # TODO Default values
        kwas = ()  # TODO kw-only arguments
        kwvs = {}  # TODO kw-only arguments default values
        vara = ()  # TODO varargs
        vark = ()  # TODO varkwargs
        annt = {}  # TODO annotations

        if not isinstance(qargs, dg.Closure) or qargs:

            args = tuple(uncurry(unwrap(qargs), const.ST_OP_TUPLE))

        len(args) < 256 or self.error(const.ERR_TOO_MANY_ARGS)

        # Put keyword-only default values onto the stack.
        #
        # STACK: + len(kwvs) * 2
        #
        for arg, value in kwvs.items():

            self.load(arg)
            self.load(value)

        # Put positional default values onto the stack.
        #
        # STACK: + len(defs)
        #
        for value in defs:

            self.load(value)

        # Put argument annotations onto the stack.
        #
        # STACK: + len(annt) + 1
        #
        annotated = tuple(annt)

        for annotation in map(annt.__getitem__, annotated):

            self.load(annotation)

        annotated and self.load(annotated)

        # Create a new `MutableCode` object for that function.
        #
        # Note that it can't use cell variables defined later.
        # This is not of concern in the global namespace as it will fall
        # back to LOAD_GLOBAL anyway.
        #
        mcode = MutableCode(
            code,
            len(args),
            len(kwas),
            args + kwas + vara + vark,
            set(self.code.varnames) | self.code.cellnames,
            const.CO_OPTIMIZED | const.CO_NEWLOCALS |
            (const.CO_VARARGS   if vara else 0) |
            (const.CO_VARKWARGS if vark else 0)
        )
        _code_hook(mcode)
        code = self.compile(code, mcode, _name)

        if code.co_freevars:

            # Build a tuple of cell variables used by the new function.
            #
            # STACK: + len(code.co_freevars)
            #
            for freevar in code.co_freevars:

                if freevar in self.code.varnames:

                    # Export local variable.
                    self.code.LOAD_FAST  (freevar, delta=1)
                    self.code.STORE_DEREF(freevar, delta=-1)

                self.code.LOAD_CLOSURE(freevar, delta=1)

            # STACK: - len(code.co_freevars)
            # STACK: + 1
            self.code.BUILD_TUPLE(len(code.co_freevars), -len(code.co_freevars) + 1)
            # STACK: + 1
            self.load(code)
            # Create a new function object.
            #
            # STACK: - len(kwvs) * 2
            # STACK: - len(defs)
            # STACK: - 2
            # STACK: + 1
            #
            self.code.MAKE_CLOSURE(
                256 * len(kwvs) + len(defs),  # + ?????
                -len(kwvs) * 2 - len(defs) - 1
            )

        else:

            # STACK: + 1
            self.load(code)
            # Create a new function object without any cell variables.
            #
            # STACK: - len(kwvs) * 2
            # STACK: - len(defs)
            # STACK: - 1
            # STACK: + 1
            #
            self.code.MAKE_FUNCTION(
                256 * len(kwvs) + len(defs),  # + ?????
                -len(kwvs) * 2 - len(defs)
            )

    def class_(self, *stuff):

        *args, block = stuff

        # FIXME methods should have '__class__' in their `freevars`.
        self.code.LOAD_BUILD_CLASS(delta=1)
        self.function(
            '__locals__',
            block,
            _code_hook=lambda code: (
                setattr(code, 'slowlocals', True),

                code.LOAD_FAST('__locals__', 1),
                code.STORE_LOCALS(delta=-1),

                code.LOAD_NAME ('__name__',    1),
                code.STORE_NAME('__module__', -1),
            )
        )

        self.load('<class>')
        self.load_call(args, ld=2)

    def call(self, f, *args):

        args = uncurry(f, const.ST_OP_FUNCALL) + list(args)
        self.load(args.pop(0))
        self.load_call(args)

    def load_call(self, args, ld=0):

        kwargs = {}
        vararg = {}

        for arg in args:

            arg = unwrap(arg)

            kw = match.matchA(arg, const.ST_ARG_KW)
            kw and kwargs.__setitem__(*kw)

            var = match.matchA(arg, const.ST_ARG_VAR)
            var and 0 in vararg and self.error(const.ERR_MULTIPLE_VARARGS)
            var and vararg.__setitem__(0, *var)

            varkw = match.matchA(arg, const.ST_ARG_VAR_KW)
            varkw and 1 in vararg and self.error(const.ERR_MULTIPLE_VARKWARGS)
            varkw and vararg.__setitem__(1, *varkw)

            var or kw or varkw or self.load(arg)

        for kw, value in kwargs.items():

            isinstance(kw, dg.Link) or self.error(const.ERR_NONCONST_KEYWORD)
            self.load(str(kw))
            self.load(value)

        0 in vararg and self.load(vararg[0])
        1 in vararg and self.load(vararg[1])

        (
            self.code.CALL_FUNCTION_VAR_KW if len(vararg) == 2 else
            self.code.CALL_FUNCTION_VAR    if 0 in vararg else
            self.code.CALL_FUNCTION_KW     if 1 in vararg else
            self.code.CALL_FUNCTION
        )(
            ld + len(args) + 255 * len(kwargs) - len(vararg),
            delta=-ld - len(args) - len(kwargs)
        )

    def store(self, var, expr):

        # Drop outermost pairs of parentheses.
        var = unwrap(var)

        if match.matchQ(expr, const.ST_IMPORT):

            args = uncurry(var, const.ST_OP_ATTRIBUTE)
            var = args[0]

            isinstance(var, dg.Link) or self.error(const.ERR_NONCONST_IMPORT)

            self.load(0)
            self.load(None)
            self.code.IMPORT_NAME('.'.join(args), -1)
            self.code.DUP_TOP(delta=1)

        else:

            self.load(expr)
            self.code.DUP_TOP(delta=1)

            attr = match.matchA(var, const.ST_OP_ATTRIBUTE)
            item = match.matchA(var, const.ST_OP_ITEM)

            if attr:

                isinstance(attr[1], dg.Link) or self.error(const.ERR_NONCONST_ATTR)

                self.load(attr[0])
                self.code.STORE_ATTR(attr[1], -2)
                return

            if item:

                self.load(item[0])
                self.load(item[1])
                self.code.STORE_SUBSCR(delta=-3)
                return

        isinstance(var, dg.Link) or self.error(const.ERR_NONCONST_VARNAME)
        var in self.code.cellnames and self.error(const.ERR_FREEVAR_ASSIGNMENT)

        self.code.STORE_DEREF (var, -1) if var in self.code.cellvars else \
        self.code.STORE_NAME  (var, -1) if self.code.slowlocals else \
        self.code.STORE_FAST  (var, -1)

    def load(self, e):

        stacksize = self.code.cstacksize
        _backup = self._loading

        if hasattr(e, 'reparse_location'):

            self.code.mark(e)
            self._loading = e

        if isinstance(e, dg.Closure):

            for not_at_end, q in enumerate(e, -len(e) + 1):

                self.load(q)
                # XXX should it insert PRINT_EXPR in `single` mode instead?
                not_at_end and self.code.POP_TOP(delta=-1)

            e or self.load(None)

        elif isinstance(e, dg.Expression):

            if isinstance(e[0], dg.Link) and e[0] in self.builtins:

                return self.builtins[e[0]](*e[1:])

            self.load(e[0])
            self.load_call(e[1:])

        elif isinstance(e, dg.Link):

            self.code.LOAD_DEREF  (e, 1) if e in self.code.cellvars  else \
            self.code.LOAD_FAST   (e, 1) if e in self.code.varnames  else \
            self.code.LOAD_DEREF  (e, 1) if e in self.code.cellnames else \
            self.code.LOAD_NAME   (e, 1) if self.code.slowlocals     else \
            self.code.LOAD_GLOBAL (e, 1)

        else:

            self.code.LOAD_CONST(e, 1)

        # NOTE `self._loading` may become garbage because of exceptions.
        self._loading = _backup
        # XXX this line is for compiler debugging purposes.
        #     If it triggers an exception, the required stack size
        #     might have been calculated improperly.
        assert self.code.cstacksize == stacksize + 1, 'stack leaked'

    def compile(self, e, into=None, name='<lambda>', single=False):

        backup, self.code = self.code, MutableCode(e) if into is None else into

        try:

            self.load(e)

            if single:

                self.code.DUP_TOP(delta=1)
                self.code.PRINT_EXPR(delta=-1)

            self.code.RETURN_VALUE(delta=-1)
            return self.code.compile(name)

        finally:

            self.code = backup

    def error(self, description):

        raise SyntaxError(
            description,
            (
                self._loading.reparse_location.filename,
                self._loading.reparse_location.start[1],
                1, str(self._loading)
            )
        )


class Interactive (interactive.Interactive):

    PARSER   = dg.Parser()
    COMPILER = Compiler()
    GLOBALS  = {
        # Runtime counterparts of some stuff in `Compiler.builtins`.

        '$': lambda f, x: f(x)
      , ':': lambda f, x: f(x)

        # TODO various operators
      , '+':  operator.add
      , '-':  operator.sub
      , '!!': operator.getitem
    }

    def compile(self, code):

        q = self.PARSER.compile_command(code)
        q = q if q is None else self.COMPILER.compile(q, name='<module>', single=True)
        return q

    def run(self, ns):

        q = self.PARSER.parse(sys.stdin, '<stdin>')
        q = self.COMPILER.compile(q, name='<module>')
        return self.eval(q, ns)


__name__ == '__main__' and Interactive().shell(__name__, Interactive.GLOBALS)
