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

    def __new__(cls, *args, **kwargs):

        obj = super(type, cls).__new__(cls)
        obj.__init__()
        return obj.compile(*args, **kwargs)

    @classmethod
    def make(cls):

        class _(cls): builtins = {}
        return _

    @classmethod
    def builtin(cls, name):

        def deco(f):

            cls.builtins[name] = f
            return f

        return deco

    def opcode(self, opcode, *args, arg=0, delta=1, inplace=False, ret=None):

        self.load(*args)
        self.code.append(opcode, arg, -len(args) + delta)
        inplace and self.store_top(*syntax.assignment_target(args[0]))

    def store(self, var, expr):

        expr, type, var, *args = syntax.assignment(var, expr)

        if type == const.AT.IMPORT:

            self.opcode('IMPORT_NAME', args[0], None, arg=expr)

        else:

            self.load(expr)

        self.store_top(type, var, *args)

    def store_top(self, type, var, *args, dup=True):

        dup and self.code.DUP_TOP(delta=1)

        if type == const.AT.UNPACK:

            ln, star = args

            star < 0 and self.code.UNPACK_SEQUENCE(ln, ln - 1)
            star < 0 or  self.code.UNPACK_EX(star + 256 * (ln - star - 1), ln - 1)

            for item in var:

                self.store_top(*item, dup=False)

        elif type == const.AT.ATTR:

            self.load(var[0])
            self.code.STORE_ATTR(var[1], -2)

        elif type == const.AT.ITEM:

            self.load(*var)
            self.code.STORE_SUBSCR(delta=-3)

        else:

            if var in self.code.cellnames:

                raise Exception(const.ERR.FREEVAR_ASSIGNMENT)

            self.code.STORE_DEREF (var, -1) if var in self.code.cellvars else \
            self.code.STORE_NAME  (var, -1) if self.code.slowlocals else \
            self.code.STORE_FAST  (var, -1)

    def call(self, f, *args, preloaded=0):

        f, *args = syntax.call_pre(f, *args)

        if isinstance(f, tree.Link) and f in self.builtins:

            return self.builtins[f](self, *args)

        f, posargs, kwargs, vararg, varkwarg = syntax.call(f, *args)
        preloaded or self.load(f)
        self.load(*posargs)
        self.load_map(kwargs)
        self.load(*vararg)
        self.load(*varkwarg)

        (
            self.code.CALL_FUNCTION_VAR_KW if vararg and varkwarg else
            self.code.CALL_FUNCTION_VAR    if vararg else
            self.code.CALL_FUNCTION_KW     if varkwarg else
            self.code.CALL_FUNCTION
        )(
            len(posargs) + 256 * len(kwargs) + preloaded,
            delta=(
                -len(posargs) - 2 * len(kwargs)
                -len(vararg)  - len(varkwarg) - preloaded
            )
        )

    def load(self, *es):

        for e in es:

            stacksize = self.code.cstacksize
            _backup = self._loading

            if hasattr(e, 'reparse_location'):

                self.code.mark(e)
                self._loading = e

            if isinstance(e, tree.Closure):

                for not_at_end, q in enumerate(e, -len(e) + 1):

                    self.load(q)
                    not_at_end and self.code.POP_TOP(delta=-1)

                e or self.load(None)

            elif isinstance(e, tree.Expression):

                self.call(*e)

            elif isinstance(e, tree.Link):

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

    def load_map(self, d):

        for k, v in d.items():

            self.load(str(k), v)

    def compile(self, e, into=None, name='<lambda>', single=False):

        backup = self.code
        self.code = codegen.MutableCode(isfunc=False) if into is None else into

        if hasattr(e, 'reparse_location'):

            self.code.filename = e.reparse_location.filename
            self.code.lineno   = e.reparse_location.start[1]

        else:

            self.code.filename = backup.filename
            self.code.lineno   = backup.lnotab[max(backup.lnotab)]

        try:

            self.load(e)

            if single:

                self.code.DUP_TOP(delta=1)
                self.code.PRINT_EXPR(delta=-1)

            self.code.RETURN_VALUE(delta=-1)
            return self.code.compile(name)

        except (SyntaxError, AssertionError) as e:

            raise

        except Exception as e:

            if __debug__:

                raise

            raise SyntaxError(
                str(e),
                (
                    self._loading.reparse_location.filename,
                    self._loading.reparse_location.start[1],
                    1, str(self._loading)
                )
            )

        finally:

            self.code = backup

