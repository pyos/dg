import functools

import dg

from . import match
from . import const
from . import codegen


varary  = lambda *fs: lambda *xs: fs[len(xs) - 1](*xs)
unwrap  = lambda f: match.matchR(f, const.ST_CLOSURE, lambda f, q: q.pop(-1))[-1]
uncurry = lambda f, p: match.matchR(f, p, lambda f, q: q.pop(-2))[::-1]


class Compiler:

    def __init__(self):

        super().__init__()

        # A mutable code object currently in use.
        self.code = None

        # An expression currently being processed by innermost `load`.
        self._loading = None

        # Predefined stuff that translates to bytecode.
        self.builtins = {
            '':   self.call
          , '$':  self.call
          , ':':  self.call

          , ',':  self.tuple
          , '->': self.function
          , 'inherit': self.class_

          , '=':  self.store
          , '.':  lambda n, a: self.opcode('LOAD_ATTR', n, arg=a)

          , 'yield': lambda a: self.opcode('YIELD_VALUE',  a)
          , 'not':   lambda a: self.opcode('UNARY_NOT',    a)
          , '~':     lambda a: self.opcode('UNARY_INVERT', a)

          , '+': varary(
                lambda a:    self.opcode('UNARY_POSITIVE', a)
              , lambda a, b: self.opcode('BINARY_ADD',     a, b)
            )

          , '-': varary(
                lambda a:    self.opcode('UNARY_NEGATIVE',  a)
              , lambda a, b: self.opcode('BINARY_SUBTRACT', a, b)
            )

          , '*':  lambda a, b: self.opcode('BINARY_MULTIPLY',     a, b)
          , '**': lambda a, b: self.opcode('BINARY_POWER',        a, b)
          , '/':  lambda a, b: self.opcode('BINARY_TRUE_DIVIDE',  a, b)
          , '//': lambda a, b: self.opcode('BINARY_FLOOR_DIVIDE', a, b)
          , '%':  lambda a, b: self.opcode('BINARY_MODULO',       a, b)
          , '!!': lambda a, b: self.opcode('BINARY_SUBSCR',       a, b)
          , '&':  lambda a, b: self.opcode('BINARY_AND',          a, b)
          , '^':  lambda a, b: self.opcode('BINARY_XOR',          a, b)
          , '|':  lambda a, b: self.opcode('BINARY_OR',           a, b)
          , '<<': lambda a, b: self.opcode('BINARY_LSHIFT',       a, b)
          , '>>': lambda a, b: self.opcode('BINARY_RSHIFT',       a, b)

          , '+=':  lambda a, b: self.opcode('INPLACE_ADD',          a, b, inplace=True)
          , '-=':  lambda a, b: self.opcode('INPLACE_SUBTRACT',     a, b, inplace=True)
          , '*=':  lambda a, b: self.opcode('INPLACE_MULTIPLY',     a, b, inplace=True)
          , '**=': lambda a, b: self.opcode('INPLACE_POWER',        a, b, inplace=True)
          , '/=':  lambda a, b: self.opcode('INPLACE_TRUE_DIVIDE',  a, b, inplace=True)
          , '//=': lambda a, b: self.opcode('INPLACE_FLOOR_DIVIDE', a, b, inplace=True)
          , '%=':  lambda a, b: self.opcode('INPLACE_MODULO',       a, b, inplace=True)
          , '!!=': lambda a, b: self.opcode('BINARY_SUBSCR',        a, b, inplace=True)
          , '&=':  lambda a, b: self.opcode('INPLACE_AND',          a, b, inplace=True)
          , '^=':  lambda a, b: self.opcode('INPLACE_XOR',          a, b, inplace=True)
          , '|=':  lambda a, b: self.opcode('INPLACE_OR',           a, b, inplace=True)
          , '<<=': lambda a, b: self.opcode('INPLACE_LSHIFT',       a, b, inplace=True)
          , '>>=': lambda a, b: self.opcode('INPLACE_RSHIFT',       a, b, inplace=True)
        }

    def opcode(self, opcode, *args, arg=0, delta=1, inplace=False):

        self.load(*args)
        self.code.append(opcode, arg, -len(args) + delta)
        inplace and self.store_top(args[0])

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

        list(map(self.load, kwvs.items()))
        self.load(*defs)
        self.load(*annt.values())
        annt and self.load(tuple(annt))

        mcode = codegen.MutableCode(
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

            for freevar in code.co_freevars:

                if freevar in self.code.varnames:

                    # Make fast slot accessible from inner scopes.
                    self.code.LOAD_FAST  (freevar, delta=1)
                    self.code.STORE_DEREF(freevar, delta=-1)

                self.code.LOAD_CLOSURE(freevar, delta=1)

            self.code.BUILD_TUPLE(len(code.co_freevars), -len(code.co_freevars) + 1)

        self.load(code)
        self.code.append(
            'MAKE_CLOSURE' if code.co_freevars else 'MAKE_FUNCTION',
            256 * len(kwvs) + len(defs),  # + ?????
            -len(kwvs) * 2 - len(defs) - bool(code.co_freevars)
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
        self.load(dg.Expression(args))

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

        if match.matchQ(expr, const.ST_IMPORT):

            args = uncurry(unwrap(var), const.ST_OP_ATTRIBUTE)
            var = args[0]

            isinstance(var, dg.Link) or self.error(const.ERR_NONCONST_IMPORT)
            self.opcode('IMPORT_NAME', 0, None, arg='.'.join(args))

        else:

            self.load(expr)

        self.store_top(var)

    def store_top(self, var):

        self.code.DUP_TOP(delta=1)

        var  = unwrap(var)
        attr = match.matchA(var, const.ST_OP_ATTRIBUTE)
        item = match.matchA(var, const.ST_OP_ITEM)

        if attr:

            isinstance(attr[1], dg.Link) or self.error(const.ERR_NONCONST_ATTR)

            self.load(attr[0])
            self.code.STORE_ATTR(attr[1], -2)
            return

        if item:

            self.load(*item)
            self.code.STORE_SUBSCR(delta=-3)
            return

        isinstance(var, dg.Link) or self.error(const.ERR_NONCONST_VARNAME)
        var in self.code.cellnames and self.error(const.ERR_FREEVAR_ASSIGNMENT)

        self.code.STORE_DEREF (var, -1) if var in self.code.cellvars else \
        self.code.STORE_NAME  (var, -1) if self.code.slowlocals else \
        self.code.STORE_FAST  (var, -1)

    def load(self, *es):

        for e in es:

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

                f, *args = e

                if isinstance(f, dg.Link) and f in self.builtins:

                    self.builtins[f](*args)

                else:

                    self.load(f)
                    self.load_call(args)

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

        backup, self.code = self.code, codegen.MutableCode(e) if into is None else into

        try:

            self.load(e)

            if single:

                self.code.DUP_TOP(delta=1)
                self.code.PRINT_EXPR(delta=-1)

            self.code.RETURN_VALUE(delta=-1)
            return self.code.compile(name)

        except (SyntaxError, AssertionError, KeyboardInterrupt) as e:

            raise

        except Exception as e:

            self.error(str(e))

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

