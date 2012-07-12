from . import codegen
from .. import const
from ..parse import tree
from ..parse import syntax


class Compiler:

    builtins     = {}
    fake_methods = {}

    def __init__(self):

        super().__init__()

        # A mutable code object currently in use.
        self.code = None

        # An expression currently being processed by innermost `load`.
        self._loading = None

    @classmethod
    def builtin(cls, name, fake_method=False):

        return lambda f: (
            cls.fake_methods if fake_method else
            cls.builtins
        ).__setitem__(name, f) or f

    def opcode(self, opcode, *args, delta, **kwargs):

        self.load(*args)
        arg = kwargs.get('arg', len(args))
        return self.code.append(opcode, arg, -len(args) + delta)

    def store_top(self, type, var, *args, dup=True):

        dup and self.opcode('DUP_TOP', delta=1)

        if type == const.AT.UNPACK:

            ln, star = args
            op  = 'UNPACK_SEQUENCE'            if star < 0 else 'UNPACK_EX'
            arg = star + 256 * (ln - star - 1) if star > 0 else ln
            self.opcode(op, arg=arg, delta=ln - 1)

            for item in var:

                self.store_top(*item, dup=False)

        elif type == const.AT.ATTR:

            self.opcode('STORE_ATTR', var[0], arg=var[1], delta=-1)

        elif type == const.AT.ITEM:

            self.opcode('STORE_SUBSCR', *var, delta=-1)

        else:

            syntax.ERROR(var in self.code.cellnames, const.ERR.FREEVAR_ASSIGNMENT)

            self.opcode(
                'STORE_DEREF' if var in self.code.cellvars else
                'STORE_NAME'  if self.code.slowlocals else
                'STORE_FAST',
                arg=var, delta=-1
            )

    def call(self, f, *args, preloaded=0):

        f, *args = syntax.call_pre(f, *args)

        if isinstance(f, tree.Link) and f in self.builtins:

            return self.builtins[f](self, *args)

        attr = syntax.call_attr(f)

        if attr and attr[1] in self.fake_methods:

            return self.fake_methods[attr[1]](self, attr[0], *args)

        f, posargs, kwargs, vararg, varkwarg = syntax.call(f, *args)
        preloaded or self.load(f)
        self.load(*posargs)
        self.load(**kwargs)

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

            stacksize = self.code.cstacksize
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
            assert self.code.cstacksize == stacksize + 1, 'stack leaked'

        for k, v in kws.items():

            self.load(str(k), v)

    def compile(self, expr, into=None, name='<lambda>'):

        backup = self.code
        self.code = codegen.MutableCode(isfunc=False) if into is None else into

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

            if __debug__ or isinstance(err, (SyntaxError, AsserionError)):

                raise

            fn = self._loading.reparse_location.filename
            ln = self._loading.reparse_location.start[1]
            tx = str(self._loading)
            raise SyntaxError(str(err), (fn, ln, 1, tx))

        finally:

            self.code = backup

