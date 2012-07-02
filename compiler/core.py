from . import codegen
from .. import const
from ..parser import tree
from ..parser import syntax

# Choose a function based on the number of arguments.
varary  = lambda *fs: lambda *xs: fs[len(xs) - 1](*xs)


class Compiler:

    def __init__(self):

        super().__init__()

        # A mutable code object currently in use.
        self.code = None

        # An expression currently being processed by innermost `load`.
        self._loading = None

        # Predefined stuff that translates to bytecode.
        self.builtins = {
            ',':  self.tuple
          , '':   self.call
          , '$':  self.call
          , ':':  self.call
          , '=':  self.store
          , '->': self.function

          , 'while': self.while_

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
          , '.~':  lambda a, b: (self.opcode('DELETE_ATTR',         a, arg=b, delta=0), self.load(None))
          , '!!~': lambda a, b: (self.opcode('DELETE_SUBSCR',       a, b,     delta=0), self.load(None))
        }

    def opcode(self, opcode, *args, arg=0, delta=1, inplace=False, ret=None):

        self.load(*args)
        self.code.append(opcode, arg, -len(args) + delta)
        inplace and self.store_top(*syntax.assignment_target(args[0]))

    def tuple(self, lhs, *rhs):

        args = syntax.tuple(lhs, *rhs)
        self.opcode('BUILD_TUPLE', *args, arg=len(args))

    def while_(self, cond, block):

        exit_ptr = self.code.SETUP_LOOP()
        cond_ptr = self.code.JUMP_ABSOLUTE(-1)
        self.load(cond)
        else_ptr = self.code.POP_JUMP_IF_FALSE(delta=-1)
        self.load(block)
        self.code.POP_TOP(delta=-1)
        cond_ptr()
        else_ptr()
        self.code.POP_BLOCK()
        # self.load(else_)
        # self.code.POP_TOP(delta=-1)
        exit_ptr()
        # FIXME popping a block resets the stack.
        #   We can't return values from `while` because of that.
        self.load(None)

    def function(self, args, code, hook=0):

        args, kwargs, defs, kwdefs, varargs, varkwargs, code = syntax.function(args, code)
        self.load_map(kwdefs)
        self.load(*defs)

        mcode = codegen.MutableCode(True, args, kwargs, varargs, varkwargs, self.code)
        hook and hook(mcode)
        code = self.compile(code, mcode, '<lambda>')

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
            len(defs) + 256 * len(kwdefs),
            -len(kwdefs) * 2 - len(defs) - bool(code.co_freevars)
        )

    def class_(self, *stuff):

        *args, block = stuff

        # FIXME methods should have '__class__' in their `freevars`.
        self.code.LOAD_BUILD_CLASS(delta=1)
        self.function(
            tree.Link('__locals__'), block,
            lambda code: (
                setattr(code, 'slowlocals', True),
                code.LOAD_FAST('__locals__', 1),
                code.STORE_LOCALS(delta=-1),
                code.LOAD_NAME ('__name__',    1),
                code.STORE_NAME('__module__', -1),
            )
        )
        self.load('<class>', *args)
        self.code.CALL_FUNCTION(len(args) + 2, delta=-len(args) - 2)

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

    def call(self, f, *args):

        f, *args = syntax.call_pre(f, *args)

        if isinstance(f, tree.Link) and f in self.builtins:

            return self.builtins[f](*args)

        f, posargs, kwargs, vararg, varkwarg = syntax.call(f, *args)
        self.load(f)
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
            len(posargs) + 256 * len(kwargs),
            delta=-len(posargs) - 2 * len(kwargs) - len(vararg) - len(varkwarg)
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
        self.code.filename = e.reparse_location.filename
        self.code.lineno   = e.reparse_location.start[1]

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

