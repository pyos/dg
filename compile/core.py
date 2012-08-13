import sys

from . import codegen
from .. import const
from ..parse import tree
from ..parse import syntax


class Compiler:

    def __init__(self):

        super().__init__()

        # A mutable code object currently in use.
        self.code = None

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

            self.getattr(*var[:-1])
            self.opcode('STORE_ATTR', arg=var[-1], delta=-2)

        elif type == const.AT.ITEM:

            # `!!` is not defined, yet required by bootstrapped code.
            self.builtins['!!'](self, *var[:-1]) if len(var) > 2 else self.load(var[0])
            self.opcode('STORE_SUBSCR', var[-1], delta=-2)

        else:

            var in self.builtins       and syntax.error(const.ERR.BUILTIN_ASSIGNMENT, var)
            var in self.fake_methods   and syntax.error(const.ERR.BUILTIN_ASSIGNMENT, var)
            var in self.code.cellnames and syntax.error(const.ERR.FREEVAR_ASSIGNMENT, var)

            self.opcode(
                'STORE_DEREF' if var in self.code.cellvars else
                'STORE_NAME'  if self.code.slowlocals else
                'STORE_FAST',
                arg=var, delta=-1
            )

    def function(self, args, code):

        args, kwargs, defs, kwdefs, varargs, varkwargs = syntax.function(args)
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

        if sys.hexversion >= 0x03030000:

            # Python <  3.3: MAKE_FUNCTION(code)
            # Python >= 3.3: MAKE_FUNCTION(code, qualname)
            return ('MAKE_CLOSURE' if code.co_freevars else 'MAKE_FUNCTION'), code, code.co_name

        return ('MAKE_CLOSURE' if code.co_freevars else 'MAKE_FUNCTION'), code

    def call(self, *argv, preloaded=None):

        attr, f, *args = syntax.call_pre(list(argv))

        if isinstance(f, tree.Link) and f in self.builtins:

            return self.builtins[f](self, *args)

        if attr and attr[1] in self.fake_methods:

            return self.fake_methods[attr[1]](self, attr[0], *args)

        posargs, kwargs, vararg, varkwarg = syntax.call_args(args)
        preloaded is None and self.load(f)
        self.load(*posargs, **kwargs)

        self.opcode(
            'CALL_FUNCTION_VAR_KW' if vararg and varkwarg else
            'CALL_FUNCTION_VAR'    if vararg else
            'CALL_FUNCTION_KW'     if varkwarg else
            'CALL_FUNCTION',
            *vararg + varkwarg,
            arg=len(posargs) + 256 * len(kwargs) + (preloaded or 0),
            delta=-len(posargs) - 2 * len(kwargs) - (preloaded or 0)
        )

    def load(self, *es, **kws):

        for e in es:

            depth = self.code.depth
            hasattr(e, 'reparse_location') and self.code.mark(e)

            if isinstance(e, tree.Expression):

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

            elif isinstance(e, tree.Constant):

                self.opcode('LOAD_CONST', arg=e.value, delta=1)

            else:

                self.opcode('LOAD_CONST', arg=e, delta=1)

            # XXX this line is for compiler debugging purposes.
            #     If it triggers an exception, the required stack size
            #     might have been calculated improperly.
            assert self.code.depth == depth + 1, 'stack leaked at ' + str(getattr(e, 'reparse_location', '?'))

        for k, v in kws.items():

            self.load(str(k), v)

    def compile(self, expr, into=None, name='<module>'):

        backup = self.code
        self.code = codegen.MutableCode() if into is None else into
        self.code.filename = expr.reparse_location.filename
        self.code.lineno   = expr.reparse_location.start[1]

        try:

            self.opcode('RETURN_VALUE', expr, delta=0)
            return self.code.compile(name)

        finally:

            self.code = backup

    def getattr(self, a, *bs):

        self.load(a)

        for b in bs:

            isinstance(b, tree.Link) or syntax.error(const.ERR.NONCONST_ATTR, b)
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
