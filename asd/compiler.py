import functools

import dg

from . import match
from . import const
from . import codegen


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

        backup, self.code = self.code, codegen.MutableCode(e) if into is None else into

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

