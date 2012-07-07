from . import core
from .. import const
from ..parse import tree
from ..parse import syntax

# Choose a function based on the number of arguments.
varary  = lambda *fs: lambda *xs: fs[len(xs) - 2](*xs)

r = core.Compiler.make()

# Stuff not worth named functions.
r.builtins = {
    'return':  lambda self, a: (self.opcode('DUP_TOP', a), self.code.RETURN_VALUE())
  , 'yield':   lambda self, a: self.opcode('YIELD_VALUE',  a)

  , 'not': lambda self, a: self.opcode('UNARY_NOT',    a)
  , '~':   lambda self, a: self.opcode('UNARY_INVERT', a)

  , '+': varary(
        lambda self, a:    self.opcode('UNARY_POSITIVE', a)
      , lambda self, a, b: self.opcode('BINARY_ADD',     a, b)
    )

  , '-': varary(
        lambda self, a:    self.opcode('UNARY_NEGATIVE',  a)
      , lambda self, a, b: self.opcode('BINARY_SUBTRACT', a, b)
    )

  , '<':   lambda self, a, b: self.opcode('COMPARE_OP', a, b, arg='<')
  , '<=':  lambda self, a, b: self.opcode('COMPARE_OP', a, b, arg='<=')
  , '==':  lambda self, a, b: self.opcode('COMPARE_OP', a, b, arg='==')
  , '!=':  lambda self, a, b: self.opcode('COMPARE_OP', a, b, arg='!=')
  , '>':   lambda self, a, b: self.opcode('COMPARE_OP', a, b, arg='>')
  , '>=':  lambda self, a, b: self.opcode('COMPARE_OP', a, b, arg='>=')
  , 'is':  lambda self, a, b: self.opcode('COMPARE_OP', a, b, arg='is')
  , 'in':  lambda self, a, b: self.opcode('COMPARE_OP', a, b, arg='in')

  , 'or':  lambda self, a, b: (self.load(a), self.code.JUMP_IF_TRUE_OR_POP (delta=-1), self.load(b))[1]()
  , 'and': lambda self, a, b: (self.load(a), self.code.JUMP_IF_FALSE_OR_POP(delta=-1), self.load(b))[1]()

  , '.':   lambda self, a, b: self.opcode('LOAD_ATTR',            a, arg=b)
  , '!!':  lambda self, a, b: self.opcode('BINARY_SUBSCR',        a, b)
  , '*':   lambda self, a, b: self.opcode('BINARY_MULTIPLY',      a, b)
  , '**':  lambda self, a, b: self.opcode('BINARY_POWER',         a, b)
  , '/':   lambda self, a, b: self.opcode('BINARY_TRUE_DIVIDE',   a, b)
  , '//':  lambda self, a, b: self.opcode('BINARY_FLOOR_DIVIDE',  a, b)
  , '%':   lambda self, a, b: self.opcode('BINARY_MODULO',        a, b)
  , '&':   lambda self, a, b: self.opcode('BINARY_AND',           a, b)
  , '^':   lambda self, a, b: self.opcode('BINARY_XOR',           a, b)
  , '|':   lambda self, a, b: self.opcode('BINARY_OR',            a, b)
  , '<<':  lambda self, a, b: self.opcode('BINARY_LSHIFT',        a, b)
  , '>>':  lambda self, a, b: self.opcode('BINARY_RSHIFT',        a, b)

  , '!!=': lambda self, a, b: self.opcode('BINARY_SUBSCR',        a, b, inplace=True)
  , '+=':  lambda self, a, b: self.opcode('INPLACE_ADD',          a, b, inplace=True)
  , '-=':  lambda self, a, b: self.opcode('INPLACE_SUBTRACT',     a, b, inplace=True)
  , '*=':  lambda self, a, b: self.opcode('INPLACE_MULTIPLY',     a, b, inplace=True)
  , '**=': lambda self, a, b: self.opcode('INPLACE_POWER',        a, b, inplace=True)
  , '/=':  lambda self, a, b: self.opcode('INPLACE_TRUE_DIVIDE',  a, b, inplace=True)
  , '//=': lambda self, a, b: self.opcode('INPLACE_FLOOR_DIVIDE', a, b, inplace=True)
  , '%=':  lambda self, a, b: self.opcode('INPLACE_MODULO',       a, b, inplace=True)
  , '&=':  lambda self, a, b: self.opcode('INPLACE_AND',          a, b, inplace=True)
  , '^=':  lambda self, a, b: self.opcode('INPLACE_XOR',          a, b, inplace=True)
  , '|=':  lambda self, a, b: self.opcode('INPLACE_OR',           a, b, inplace=True)
  , '<<=': lambda self, a, b: self.opcode('INPLACE_LSHIFT',       a, b, inplace=True)
  , '>>=': lambda self, a, b: self.opcode('INPLACE_RSHIFT',       a, b, inplace=True)

  , '.~':  lambda self, a, b: (self.opcode('DELETE_ATTR',         a, arg=b, delta=0), self.load(None))
  , '!!~': lambda self, a, b: (self.opcode('DELETE_SUBSCR',       a, b,     delta=0), self.load(None))
}


@r.builtin(',')
#
# `init, last`
#
# Append last to `init` if `init` is a syntactic tuple,
# yield `(init, last)` otherwise.
#
# `init,`
#
# Return `init` if it's a syntactic tuple, and the tuple containing `init` otherwise.
#
def tuple(self, init, *last):

    args = syntax.tuple_(init, *last)
    self.opcode('BUILD_TUPLE', *args, arg=len(args))


@r.builtin('')
@r.builtin(':')
#
# `f arg`
# `f: arg`
#
# Call `f` with `arg`, which may be a keyword argument (`kw: value`).
#
def call(self, *args):

    return self.call(*args)


@r.builtin('$')
#
# `f $ arg`  Call `f` with `(arg)`.
# `f $`      Call `f` with `()`.
#
def pipe(self, f, *args):

    args = [tree.Closure([arg]) for arg in args] if args else [tree.Closure()]
    return self.call(f, *args)


@r.builtin('=')
#
# `var = expr`
#
# Assign `var` the value of `expr`.
#
def store(self, var, expr):

    expr, type, var, *args = syntax.assignment(var, expr)

    if type == const.AT.IMPORT:

        self.opcode('IMPORT_NAME', args[0], None, arg=expr)

    else:

        self.load(expr)

    self.store_top(type, var, *args)


@r.builtin('->')
#
# `argspec -> body`
#
# Allow to evaluate `body` passing it stuff that matches `argspec`.
#
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


@r.builtin('while')
#
# `while: cond block`
#
# Evaluate `block` in the current namespace until `cond` becomes False. 
#
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


@r.builtin('inherit')
#
# `inherit: superclass... class_body`
#
# Create a new class deriving from all of the superclasses.
#
def inherit(self, *stuff):

    *args, block = stuff

    # FIXME methods should have '__class__' in their `freevars`.
    self.code.LOAD_BUILD_CLASS(delta=1)
    function(
        self, tree.Link('__locals__'), block,
        lambda code: (
            code.LOAD_FAST('__locals__', 1),
            code.STORE_LOCALS(delta=-1),
            code.LOAD_NAME ('__name__',    1),
            code.STORE_NAME('__module__', -1),
        )
    )
    self.load('<class>')
    self.call(None, *args, preloaded=2)


@r.builtin('if')
#
# `if: cond then [else]`
#
# Evaluate `then` if `cond`, `else` (or None) otherwise.
#
def if_(self, cond, then, else_=None):

    self.load(cond)
    end_ptr = self.code.POP_JUMP_IF_FALSE(delta=-1)
    self.load(then)
    jmp_ptr = self.code.JUMP_FORWARD(delta=-1)
    end_ptr()
    self.load(else_)
    jmp_ptr()

