import functools

import dg
import dg.util

from . import const
from . import codegen


varary  = lambda *fs: lambda *xs: fs[len(xs) - 1](*xs)
unwrap  = lambda f: dg.util.matchR(f, const.ST_CLOSURE, lambda f, q: q.pop(-1))[-1]
uncurry = lambda f, p: dg.util.matchR(f, p, lambda f, q: q.pop(-2))[::-1]


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
          , '=':  self.store

          , 'inherit': self.class_
          , 'return':  lambda a: (self.opcode('DUP_TOP', a), self.code.RETURN_VALUE())
          , 'yield':   lambda a: self.opcode('YIELD_VALUE',  a)

          , 'not': lambda a: self.opcode('UNARY_NOT',    a)
          , '~':   lambda a: self.opcode('UNARY_INVERT', a)

          , '+': varary(
                lambda a:    self.opcode('UNARY_POSITIVE', a)
              , lambda a, b: self.opcode('BINARY_ADD',     a, b)
            )

          , '-': varary(
                lambda a:    self.opcode('UNARY_NEGATIVE',  a)
              , lambda a, b: self.opcode('BINARY_SUBTRACT', a, b)
            )

          , '<':   lambda a, b: self.opcode('COMPARE_OP', a, b, arg='<')
          , '<=':  lambda a, b: self.opcode('COMPARE_OP', a, b, arg='<=')
          , '==':  lambda a, b: self.opcode('COMPARE_OP', a, b, arg='==')
          , '!=':  lambda a, b: self.opcode('COMPARE_OP', a, b, arg='!=')
          , '>':   lambda a, b: self.opcode('COMPARE_OP', a, b, arg='>')
          , '>=':  lambda a, b: self.opcode('COMPARE_OP', a, b, arg='>=')
          , 'is':  lambda a, b: self.opcode('COMPARE_OP', a, b, arg='is')
          , 'in':  lambda a, b: self.opcode('COMPARE_OP', a, b, arg='in')

          , 'or':  lambda a, b: (self.load(a), self.code.JUMP_IF_TRUE_OR_POP (delta=-1), self.load(b))[1]()
          , 'and': lambda a, b: (self.load(a), self.code.JUMP_IF_FALSE_OR_POP(delta=-1), self.load(b))[1]()

          , '.':   lambda a, b: self.opcode('LOAD_ATTR',            a, arg=b)
          , '!!':  lambda a, b: self.opcode('BINARY_SUBSCR',        a, b)
          , '*':   lambda a, b: self.opcode('BINARY_MULTIPLY',      a, b)
          , '**':  lambda a, b: self.opcode('BINARY_POWER',         a, b)
          , '/':   lambda a, b: self.opcode('BINARY_TRUE_DIVIDE',   a, b)
          , '//':  lambda a, b: self.opcode('BINARY_FLOOR_DIVIDE',  a, b)
          , '%':   lambda a, b: self.opcode('BINARY_MODULO',        a, b)
          , '&':   lambda a, b: self.opcode('BINARY_AND',           a, b)
          , '^':   lambda a, b: self.opcode('BINARY_XOR',           a, b)
          , '|':   lambda a, b: self.opcode('BINARY_OR',            a, b)
          , '<<':  lambda a, b: self.opcode('BINARY_LSHIFT',        a, b)
          , '>>':  lambda a, b: self.opcode('BINARY_RSHIFT',        a, b)
          , '!!=': lambda a, b: self.opcode('BINARY_SUBSCR',        a, b, inplace=True)
          , '+=':  lambda a, b: self.opcode('INPLACE_ADD',          a, b, inplace=True)
          , '-=':  lambda a, b: self.opcode('INPLACE_SUBTRACT',     a, b, inplace=True)
          , '*=':  lambda a, b: self.opcode('INPLACE_MULTIPLY',     a, b, inplace=True)
          , '**=': lambda a, b: self.opcode('INPLACE_POWER',        a, b, inplace=True)
          , '/=':  lambda a, b: self.opcode('INPLACE_TRUE_DIVIDE',  a, b, inplace=True)
          , '//=': lambda a, b: self.opcode('INPLACE_FLOOR_DIVIDE', a, b, inplace=True)
          , '%=':  lambda a, b: self.opcode('INPLACE_MODULO',       a, b, inplace=True)
          , '&=':  lambda a, b: self.opcode('INPLACE_AND',          a, b, inplace=True)
          , '^=':  lambda a, b: self.opcode('INPLACE_XOR',          a, b, inplace=True)
          , '|=':  lambda a, b: self.opcode('INPLACE_OR',           a, b, inplace=True)
          , '<<=': lambda a, b: self.opcode('INPLACE_LSHIFT',       a, b, inplace=True)
          , '>>=': lambda a, b: self.opcode('INPLACE_RSHIFT',       a, b, inplace=True)
          , '.~':  lambda a, b: self.opcode('DELETE_ATTR',          a, arg=b, delta=0, ret=None)
          , '!!~': lambda a, b: self.opcode('DELETE_SUBSCR',        a, b,     delta=0, ret=None)
        }

    def opcode(self, opcode, *args, arg=0, delta=1, inplace=False, **k):

        self.load(*args)
        self.code.append(opcode, arg, -len(args) + delta)
        inplace and self.store_top(args[0])
        'ret' in k and self.load(k['ret'])

    def tuple(self, lhs, *rhs):

        args = uncurry(lhs, const.ST_OP_TUPLE) + list(rhs)
        self.opcode('BUILD_TUPLE', *args, arg=len(args))

    def function(self, args, code, *_, _code_hook=lambda code: 0, _name='<lambda>'):

        arguments   = []  # `c.co_varnames[:c.co_argc]`
        kwarguments = []  # `c.co_varnames[c.co_argc:c.co_argc + c.co_kwonlyargc]`

        defaults    = []  # `f.__defaults__`
        kwdefaults  = {}  # `f.__kwdefaults__`

        varargs     = []  # [] or [name of a varargs container]
        varkwargs   = []  # [] or [name of a varkwargs container]

        if not isinstance(args, dg.Closure) or args:

            # Either a single argument, or multiple arguments separated by commas.
            for arg in uncurry(unwrap(args), const.ST_OP_TUPLE):

                arg, *default = dg.util.matchA(arg, const.ST_ARG_KW) or [arg]
                vararg = dg.util.matchA(arg, const.ST_ARG_VAR)
                varkw  = dg.util.matchA(arg, const.ST_ARG_VAR_KW)
                # Extract argument name from `vararg` or `varkw`.
                arg, = vararg or varkw or [arg]

                # Syntax checks.
                # 0. varkwargs should be the last argument
                varkwargs and self.error(const.ERR_ARG_AFTER_VARKWARGS)
                # 1. varargs and varkwargs can't have default values.
                default and (vararg or varkw) and self.error(const.ERR_VARARG_DEFAULT)
                # 2. all arguments between the first one with the default value
                #    and the varargs must have default values
                varargs or not defaults or default or self.error(const.ERR_NO_DEFAULT)
                # 3. only one vararg and one varkwarg is allowed
                varargs   and vararg and self.error(const.ERR_MULTIPLE_VARARGS)
                varkwargs and varkw  and self.error(const.ERR_MULTIPLE_VARKWARGS)

                # Put the argument into the appropriate list.
                default and not varargs and defaults.extend(default)
                default and     varargs and kwdefaults.__setitem__(arg, *default)
                (
                    varargs     if vararg  else
                    varkwargs   if varkw   else
                    kwarguments if varargs else
                    arguments
                ).append(arg)

        len(arguments) < 256 or self.error(const.ERR_TOO_MANY_ARGS)

        [self.load(str(k), v) for k, v in kwdefaults.items()]
        self.load(*defaults)

        mcode = codegen.MutableCode(
            code,
            len(arguments),
            len(kwarguments),
            arguments + kwarguments + varargs + varkwargs,
            set(self.code.varnames) | self.code.cellnames,
            const.CO_OPTIMIZED | const.CO_NEWLOCALS |
            bool(varargs)   * const.CO_VARARGS |
            bool(varkwargs) * const.CO_VARKWARGS
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
            len(defaults) + 256 * len(kwdefaults),
            -len(kwdefaults) * 2 - len(defaults) - bool(code.co_freevars)
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

            kw = dg.util.matchA(arg, const.ST_ARG_KW)
            kw and kwargs.__setitem__(*kw)

            var = dg.util.matchA(arg, const.ST_ARG_VAR)
            var and 0 in vararg and self.error(const.ERR_MULTIPLE_VARARGS)
            var and vararg.__setitem__(0, *var)

            varkw = dg.util.matchA(arg, const.ST_ARG_VAR_KW)
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

        if dg.util.matchQ(expr, const.ST_IMPORT):

            parent = 0

            if isinstance(var, dg.Expression) and len(var) == 3:

                if var[0] == '' and set(var[1]) == {'.'}:

                    parent = len(var[1])
                    var = var[2]

            args = uncurry(unwrap(var), const.ST_OP_ATTRIBUTE)
            var = args[0]

            isinstance(var, dg.Link) or self.error(const.ERR_NONCONST_IMPORT)
            self.opcode('IMPORT_NAME', parent, None, arg='.'.join(args))

        else:

            self.load(expr)

        self.store_top(var)

    def store_top(self, var, dup=True):

        dup and self.code.DUP_TOP(delta=1)

        var  = unwrap(var)
        pack = uncurry(var, const.ST_OP_TUPLE)
        pack = pack if len(pack) > 1 else dg.util.matchA(var, const.ST_OP_TUPLE_S)

        if pack:

            star = [i for i, q in enumerate(pack) if dg.util.matchQ(q, const.ST_ARG_VAR)]

            if star:

                len(star) == 1 or self.error(const.ERR_MULTIPLE_VARARGS)

                star,  = star
                before = pack[:star]
                pack[star] = dg.util.matchA(pack[star], const.ST_ARG_VAR)[0]

                self.code.UNPACK_EX(
                    # items before a star + 256 * items after a star
                    star + 256 * (len(pack) - star - 1),
                    len(pack) - 1
                )

            else:

                self.code.UNPACK_SEQUENCE(len(pack), len(pack) - 1)

            for item in pack:

                self.store_top(item, dup=False)

            return

        attr = dg.util.matchA(var, const.ST_OP_ATTRIBUTE)
        item = dg.util.matchA(var, const.ST_OP_ITEM)

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

