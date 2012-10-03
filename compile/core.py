import sys

from . import codegen
from .. import const
from ..parse import tree
from ..parse import syntax


class Compiler:

    @classmethod
    # Compile a parser output tree into an immutable code object.
    #
    # :param into_codeobj: a temporary mutable code object to use.
    #
    def compile(cls, expr, into=None, name='<module>'):

        self = cls()
        self.code = codegen.MutableCode() if into is None else into
        self.code.filename = expr.location.filename
        self.code.lineno   = expr.location.start[1]
        self.opcode('RETURN_VALUE', expr, delta=0)
        return self.code.compile(name)

    # Push the results of some expressions onto the stack.
    #
    # NOTE `load(a=b)` loads string `'a'`, then the result of `b`.
    # NOTE `load`ing an expression multiple times evaluates it multiple times.
    #   Use `DUP_TOP` opcode when necessary.
    #
    def load(self, *es, **kws):

        for e in es:

            hasattr(e, 'location') and self.code.mark(e)

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

            self.opcode('STORE_ATTR', args, arg=var, delta=-2)

        elif type == const.AT.ITEM:

            self.opcode('STORE_SUBSCR', args, var, delta=-2)

        else:

            var in self.builtins   and syntax.error(const.ERR.BUILTIN_ASSIGNMENT, var)
          # var in self.fake_attrs and syntax.error(const.ERR.BUILTIN_ASSIGNMENT, var)

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

    # Load an attribute given its name.
    #
    # Default behavior is to use LOAD_ATTR(name).
    # Built-in functions may override that.
    #
    def ldattr(self, name):

        isinstance(name, tree.Link) or syntax.error(const.ERR.NONCONST_ATTR, name)
        self.fake_attrs[name](self) if name in self.fake_attrs else \
        self.opcode('LOAD_ATTR', arg=name, delta=0)

    def nativecall(self, args, preloaded, infix=False):

        defs  = args, None, None, {}, (), ()
        args, _, _, kwargs, vararg, varkwarg = defs if infix else syntax.argspec(args, definition=False)

        self.load(*args, **kwargs)
        self.opcode(
            'CALL_FUNCTION' + ('_VAR' if vararg else '') + ('_KW' if varkwarg else ''),
            *vararg + varkwarg,
            arg  = len(args) + 256 * len(kwargs) + preloaded,
            delta=-len(args) -   2 * len(kwargs) - preloaded
        )

    def infixbind(self, f, arg, right):

        if f not in self.bind_hooks or not self.bind_hooks[f](self, arg, right):

            self.load(tree.Link('bind'))
            self.opcode('CALL_FUNCTION', tree.Link('flip'), f, arg=1, delta=1) if right else self.load(f)
            self.opcode('CALL_FUNCTION', arg, arg=2, delta=-1)

  ### ESSENTIAL BUILT-INS

    #
    # function argument ... keyword: value *: varargs **: varkwargs
    #
    # Call a (possibly built-in) function.
    #
    def call(self, f, *args):

        lfe = False

        if f.infix and f == '':  # empty link can't be closed

            *op, (f, *args) = f, args
            lfe = True

        if f.infix and not f.closed and (lfe or len(args) == 1):

            self.infixbind(f, args[0] if len(args) == 1 else tree.Expression(op + args), right=lfe)

        elif isinstance(f, tree.Link) and f in self.builtins:

            self.builtins[f](self, *args)

        else:

            self.load(f)
            self.nativecall(args, 0, f.infix and not f.closed)

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

        args, kwargs, defs, kwdefs, varargs, varkwargs = syntax.argspec(args, definition=True)
        code = codegen.MutableCode(True, args, kwargs, varargs, varkwargs, self.code)
        code = self.compile(body, into=code, name='<lambda>')
        self.make_function(code, defs, kwdefs)

    #
    # object.attribute
    #
    # Retrieve an attribute of some object.
    #
    def getattr(self, a, b):

        self.load(a)
        self.ldattr(b)

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
      , '=':  store
      , '.':  getattr
      , '\n': chain
      , '->': function
    }

    fake_attrs = {}
    bind_hooks = {}
