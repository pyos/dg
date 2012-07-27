from . import codegen
from .. import const
from ..parse import tree
from ..parse import syntax


class Compiler:

    def __init__(self):

        super().__init__()

        # A mutable code object currently in use.
        self.code = None

        # An expression currently being processed by innermost `load`.
        self._loading = None

    def opcode(self, opcode, *args, delta, **kwargs):

        self.load(*args)
        arg = kwargs.get('arg', len(args))
        return self.code.append(opcode, arg, -len(args) + delta)

    def store(self, var, expr):

        expr, type, var, *args = syntax.assignment(var, expr)

        if type == const.AT.IMPORT:

            self.opcode('IMPORT_NAME', args[0], None, arg=expr, delta=1)

        else:

            self.load(expr)

        self.store_top(type, var, *args)

    def store_top(self, type, var, *args, dup=True):

        dup and self.opcode('DUP_TOP', delta=1)

        if type == const.AT.UNPACK:

            ln, star = args
            op  = 'UNPACK_SEQUENCE'            if star <  0 else 'UNPACK_EX'
            arg = star + 256 * (ln - star - 1) if star >= 0 else ln
            self.opcode(op, arg=arg, delta=ln - 1)

            for item in var:

                self.store_top(*item, dup=False)

        elif type == const.AT.ATTR:

            var[1] in self.fake_methods and const.ERR.FAKE_METHOD_ASSIGNMENT
            self.opcode('STORE_ATTR', var[0], arg=var[1], delta=-1)

        elif type == const.AT.ITEM:

            self.opcode('STORE_SUBSCR', *var, delta=-1)

        else:

            var in self.builtins       and const.ERR.BUILTIN_ASSIGNMENT
            var in self.fake_methods   and const.ERR.BUILTIN_ASSIGNMENT
            var in self.code.cellnames and const.ERR.FREEVAR_ASSIGNMENT

            self.opcode(
                'STORE_DEREF' if var in self.code.cellvars else
                'STORE_NAME'  if self.code.slowlocals else
                'STORE_FAST',
                arg=var, delta=-1
            )

    def function(self, args, code):

        args, kwargs, defs, kwdefs, varargs, varkwargs, code = syntax.function(args, code)
        self.load(**kwdefs)
        self.load(*defs)

        mcode = codegen.MutableCode(True, args, kwargs, varargs, varkwargs, self.code)

        hasattr(self.code, 'f_hook') and self.code.f_hook(mcode)
        code = self.compile(code, mcode, name='<lambda>')

        self.opcode(
            *self.preload_free(code),
            arg=len(defs) + 256 * len(kwdefs),
            delta=-len(kwdefs) * 2 - len(defs) - bool(code.co_freevars) + 1
        )


    def preload_free(self, code):

        if code.co_freevars:

            for freevar in code.co_freevars:

                if freevar in self.code.varnames:

                    # Make fast slot accessible from inner scopes.
                    self.opcode('LOAD_FAST',   arg=freevar, delta=1)
                    self.opcode('STORE_DEREF', arg=freevar, delta=-1)

                self.opcode('LOAD_CLOSURE', arg=freevar, delta=1)

            self.opcode('BUILD_TUPLE', arg=len(code.co_freevars), delta=-len(code.co_freevars) + 1)

        return ('MAKE_CLOSURE' if code.co_freevars else 'MAKE_FUNCTION'), code

    def call(self, *argv, preloaded=0):

        attr, f, *args = syntax.call_pre(list(argv))

        if isinstance(f, tree.Link) and f in self.builtins:

            return self.builtins[f](self, *args)

        if attr and attr[1] in self.fake_methods:

            return self.fake_methods[attr[1]](self, attr[0], *args)

        posargs, kwargs, vararg, varkwarg = syntax.call_args(args)
        preloaded or self.load(f)
        self.load(*posargs, **kwargs)

        self.opcode(
            'CALL_FUNCTION_VAR_KW' if vararg and varkwarg else
            'CALL_FUNCTION_VAR'    if vararg else
            'CALL_FUNCTION_KW'     if varkwarg else
            'CALL_FUNCTION',
            *vararg + varkwarg,
            arg=len(posargs) + 256 * len(kwargs) + preloaded,
            delta=-len(posargs) - 2 * len(kwargs) - preloaded
        )

    def load(self, *es, **kws):

        for e in es:

            depth = self.code.depth
            _backup = self._loading

            if hasattr(e, 'reparse_location'):

                self.code.mark(e)
                self._loading = e

            if isinstance(e, tree.Closure):

                for not_at_end, q in enumerate(e, -len(e) + 1):

                    self.load(q)
                    not_at_end and self.opcode('POP_TOP', delta=-1)

                e or self.load(None)

            elif isinstance(e, tree.Expression):

                self.call(*e)

            elif isinstance(e, tree.Link):

                self.opcode(
                    'LOAD_DEREF' if e in self.code.cellvars  else
                    'LOAD_FAST'  if e in self.code.varnames  else
                    'LOAD_DEREF' if e in self.code.cellnames else
                    'LOAD_NAME'  if self.code.slowlocals     else
                    'LOAD_GLOBAL',
                    arg=e, delta=1
                )

            else:

                self.opcode('LOAD_CONST', arg=e, delta=1)

            # NOTE `self._loading` may become garbage because of exceptions.
            self._loading = _backup
            # XXX this line is for compiler debugging purposes.
            #     If it triggers an exception, the required stack size
            #     might have been calculated improperly.
            assert self.code.depth == depth + 1, 'stack leaked'

        for k, v in kws.items():

            self.load(str(k), v)

    def compile(self, expr, into=None, name='<module>'):

        backup = self.code
        self.code = codegen.MutableCode() if into is None else into

        if hasattr(expr, 'reparse_location'):

            self.code.filename = expr.reparse_location.filename
            self.code.lineno   = expr.reparse_location.start[1]

        else:

            self.code.filename = backup.filename
            self.code.lineno   = backup.lnotab[max(backup.lnotab)]

        try:

            self.opcode('RETURN_VALUE', expr, delta=0)
            return self.code.compile(name)

        except Exception as err:

            if __debug__ or isinstance(err, (SyntaxError, AssertionError)):

                raise

            fn = self._loading.reparse_location.filename
            ln = self._loading.reparse_location.start[1]
            tx = str(self._loading)
            raise SyntaxError(str(err), (fn, ln, 1, tx))

        finally:

            self.code = backup

    def getattr(self, a, *bs):

        self.load(a)

        for b in bs:

            self.opcode('LOAD_ATTR', arg=b, delta=0)

    builtins = {
        '':   call
      , ':':  call
      , '=':  store
      , '->': function
      , '.':  getattr
      , '\n': lambda self, *xs: [self.opcode('POP_TOP', x, delta=0) for x in xs[:-1]] + [self.load(xs[-1])]
    }

    fake_methods = {}
