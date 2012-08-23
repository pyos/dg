import sys

from . import codegen
from .. import const
from ..parse import tree
from ..parse import syntax


#
# NOTE this class depends heavily on side effects.
#   As such, none of the methods are thread-safe.
#
class Compiler:

    def __init__(self):

        super().__init__()

        self.code = None

    # Create an immutable code object that evaluates a given expression.
    #
    # :param into: either None or a preconstructed mutable code object.
    #
    # :param name: name of the namespace (e.g. '<module>' for the top-level code).
    #
    def compile(self, expr, into=None, name='<module>'):

        self.code = codegen.MutableCode(cell=self.code) if into is None else into
        self.code.filename = expr.reparse_location.filename
        self.code.lineno   = expr.reparse_location.start[1]

        try:

            self.opcode('RETURN_VALUE', expr, delta=0)
            return self.code.compile(name)

        finally:

            self.code = self.code.cell

    # Push the results of some expressions onto the stack.
    #
    # NOTE `load(a=b)` loads string `'a'`, then the result of `b`.
    # NOTE `load`ing an expression multiple times evaluates it multiple times.
    #   Use `DUP_TOP` opcode when necessary.
    #
    def load(self, *es, **kws):

        for e in es:

            hasattr(e, 'reparse_location') and self.code.mark(e)

            if isinstance(e, tree.Expression):

                self.call(*e)

            elif isinstance(e, tree.Link):

                self.opcode(
                    'LOAD_DEREF' if e in self.code.cellvars  else
                    'LOAD_FAST'  if e in self.code.varnames  else
                    'LOAD_DEREF' if e in self.code.cellnames else
                    'LOAD_NAME'  if self.code.slowlocals     else
                    'LOAD_GLOBAL', arg=e, delta=1
                )

            elif isinstance(e, tree.Constant):

                self.opcode('LOAD_CONST', arg=e.value, delta=1)

            else:

                self.opcode('LOAD_CONST', arg=e, delta=1)

        for k, v in kws.items():

            self.load(str(k), v)

    # Append a single opcode with some non-integer arguments.
    #
    # :param args: objects to pass to :meth:`load`.
    #
    # :param delta: how much items the opcode will pop **excluding :obj:`args`**
    #
    # :param arg: the argument to that opcode, defaults to `len(args)`.
    #
    def opcode(self, opcode, *args, delta, **kwargs):

        self.load(*args)
        return self.code.append(opcode, kwargs.get('arg', len(args)), -len(args) + delta)

    # Store whatever is on top of the stack in a variable.
    #
    # :param dup: whether to leave the stored object on the stack afterwards.
    #
    # Supported name schemes::
    #
    #   name = ...              | variable assignment
    #   object.name = ...       | object.__setattr__('name', ...)
    #   object !! object = ...  | object.__setitem__(object, ...)
    #   scheme, ... = ...       | recursive iterable unpacking
    #
    def store_top(self, var, dup=True):

        dup and self.opcode('DUP_TOP', delta=1)

        type, var, args = syntax.assignment_target(var)

        if type == const.AT.UNPACK:

            ln, star = args
            op  = 'UNPACK_SEQUENCE' if star < 0 else 'UNPACK_EX'
            arg = ln                if star < 0 else star + 256 * (ln - star - 1)
            self.opcode(op, arg=arg, delta=ln - 1)

            for item in var:

                self.store_top(item, dup=False)

        elif type == const.AT.ATTR:

            self.builtins['.'](self, *args)
            self.opcode('STORE_ATTR', arg=var, delta=-2)

        elif type == const.AT.ITEM:

            # `!!` is not defined, yet required by bootstrapped code.
            self.builtins['!!'](self, *args) if len(args) > 1 else self.load(*args)
            self.opcode('STORE_SUBSCR', var, delta=-2)

        else:

            var in self.builtins   and syntax.error(const.ERR.BUILTIN_ASSIGNMENT, var)
            var in self.fake_attrs and syntax.error(const.ERR.BUILTIN_ASSIGNMENT, var)

            self.opcode(
                'STORE_DEREF' if var in self.code.cellnames else
                'STORE_DEREF' if var in self.code.cellvars else
                'STORE_NAME'  if self.code.slowlocals else
                'STORE_FAST', arg=var, delta=-1
            )

    # Create a function from a given immutable code object and default arguments.
    #
    # In Python 3.3, the qualified name of the function is assumed to be
    # the same as the unqualified one. FIXME.
    #
    def make_function(self, code, defaults, kwdefaults):

        self.load(**kwdefaults)
        self.load(*defaults)

        if code.co_freevars:

            for freevar in code.co_freevars:

                self.opcode('LOAD_CLOSURE', arg=self.code.cellify(freevar), delta=1)

            self.opcode('BUILD_TUPLE', arg=len(code.co_freevars), delta=-len(code.co_freevars) + 1)

        self.opcode(
            'MAKE_CLOSURE' if code.co_freevars else 'MAKE_FUNCTION', code,
            # Python <  3.3: MAKE_FUNCTION(code)
            # Python >= 3.3: MAKE_FUNCTION(code, qualname)
            *[code.co_name] if sys.hexversion >= 0x03030000 else [],
            arg  =    len(defaults) + 256 * len(kwdefaults),
            delta=1 - len(defaults) -   2 * len(kwdefaults) - bool(code.co_freevars)
        )

  ### ESSENTIAL BUILT-INS

    #
    # function argument ...
    # function: argument ... keyword: value (*): varargs (**): varkwargs
    #
    # Call a (possibly built-in) function.
    #
    # :param preloaded: how many arguments are already on the stack:
    #   if None, then nothing is taken from the stack;
    #   if 0, the function object is taken from the stack and
    #     the first argument is discarded;
    #   if n, do the same thing as for 0, but also increase the argument by n.
    #
    # Note that this method borrows from Smalltalk in that it can also
    # call fake (i.e. not existing at runtime) methods to fake some behavior
    # Python developers decided to implement as syntactic constructs.
    # These methods, however, are not first-class.
    #
    def call(self, *argv, preloaded=None):

        f, *args = syntax.call_pre(argv)

        if isinstance(f, tree.Link) and f in self.builtins:

            return self.builtins[f](self, *args)

        posargs, kwargs, vararg, varkwarg = syntax.call_args(args)
        preloaded is None and self.load(f)
        self.load(*posargs, **kwargs)

        self.opcode(
            'CALL_FUNCTION' + '_VAR' * len(vararg) + '_KW' * len(varkwarg),
            *vararg + varkwarg,
            arg  = len(posargs) + 256 * len(kwargs) + (preloaded or 0),
            delta=-len(posargs) -   2 * len(kwargs) - (preloaded or 0)
        )

    #
    # name = expression
    #
    # Store the result of `expression` in `name`.
    # If `expression` is `import`, attempt to derive the module name
    # from `name`.
    #
    def store(self, var, expr):

        var, expr, isimport = syntax.assignment(var, expr)

        if isimport is False:

            self.load(expr)

        else:

            self.opcode('IMPORT_NAME', isimport, None, arg=expr, delta=1)

        self.store_top(var)

    #
    # argspec -> body
    #
    # Create a function with a given argument specification
    # that evaluates its body on call.
    #
    # `argspec` may be empty (i.e. `Constant(None)`.)
    #
    def function(self, args, body):

        args, kwargs, defs, kwdefs, varargs, varkwargs = syntax.function(args)
        code = codegen.MutableCode(True, args, kwargs, varargs, varkwargs, self.code)
        code = self.compile(body, into=code, name='<lambda>')
        self.make_function(code, defs, kwdefs)

    #
    # object.attribute
    #
    # Retrieve an attribute of some object.
    #
    def getattr(self, a, *bs):

        self.load(a)

        for b in bs:

            isinstance(b, tree.Link) or syntax.error(const.ERR.NONCONST_ATTR, b)
            self.fake_attrs[b](self) if b in self.fake_attrs else \
            self.opcode('LOAD_ATTR', arg=b, delta=0)

    #
    # expression_1 (insert line break here) expression_2
    #
    # Evaluate some expressions in a strict order, return the value of the last one.
    #
    def chain(self, a, *bs):

        self.load(a)

        for b in bs:

            self.opcode('POP_TOP', delta=-1)
            self.load(b)

    builtins = {
        '':   call
      , ':':  call
      , '=':  store
      , '.':  getattr
      , '\n': chain
      , '->': function
    }

    fake_attrs = {}
