from . import core
from .. import const
from ..parse import tree
from ..parse import syntax


def varary(multiple, arg=0, inplace=False, single=None):

    def f(self, a, *bs):

        self.load(a)
        ps = [self.opcode(multiple, b, arg=arg, delta=0) for b in bs]
        ps or self.opcode(single,      arg=arg, delta=0)
        inplace and self.store_top(*syntax.assignment_target(a))

    return f


def varary_cond(jmp, p=lambda xs: xs):

    def f(self, *xs, n=lambda: 0):

        *bs, a = p(xs)
        ps = [self.opcode(jmp, b, delta=0) for b in bs]
        self.load(a)
        [p() for p in ps]

    return f


class r (core.Compiler):

    # Stuff not worth named functions.
    builtins = {
        '':   core.Compiler.call
      , ':':  core.Compiler.call
      , '$':  lambda self, a, *bs, c=tree.Closure: self.call(a, *[c([b]) for b in bs] or [c()])

      , 'or':     varary_cond('JUMP_IF_TRUE_OR_POP')
      , 'and':    varary_cond('JUMP_IF_FALSE_OR_POP')
      , 'unless': varary_cond('JUMP_IF_TRUE_OR_POP',  reversed)
      , 'if':     varary_cond('JUMP_IF_FALSE_OR_POP', reversed)
      , 'return': lambda self, a: self.opcode('RETURN_VALUE', None, a, delta=1)
      , 'yield':  lambda self, a: self.opcode('YIELD_VALUE',        a, delta=1)

      , 'not': lambda self, a: self.opcode('UNARY_NOT',    a, delta=1)
      , '~':   lambda self, a: self.opcode('UNARY_INVERT', a, delta=1)

        # FIXME `a < b < c` <=> `a < b and b < c`, not `(a < b) < c`.
      , '<':   varary('COMPARE_OP', '<')
      , '<=':  varary('COMPARE_OP', '<=')
      , '==':  varary('COMPARE_OP', '==')
      , '!=':  varary('COMPARE_OP', '!=')
      , '>':   varary('COMPARE_OP', '>')
      , '>=':  varary('COMPARE_OP', '>=')
      , 'is':  varary('COMPARE_OP', 'is')
      , 'in':  varary('COMPARE_OP', 'in')

      , '!!':  varary('BINARY_SUBSCR')
      , '+':   varary('BINARY_ADD',      single='UNARY_POSITIVE')
      , '-':   varary('BINARY_SUBTRACT', single='UNARY_NEGATIVE')
      , '*':   varary('BINARY_MULTIPLY')
      , '**':  varary('BINARY_POWER')
      , '/':   varary('BINARY_TRUE_DIVIDE')
      , '//':  varary('BINARY_FLOOR_DIVIDE')
      , '%':   varary('BINARY_MODULO')
      , '&':   varary('BINARY_AND')
      , '^':   varary('BINARY_XOR')
      , '|':   varary('BINARY_OR')
      , '<<':  varary('BINARY_LSHIFT')
      , '>>':  varary('BINARY_RSHIFT')

      , '!!=': varary('BINARY_SUBSCR',        inplace=True)
      , '+=':  varary('INPLACE_ADD',          inplace=True)
      , '-=':  varary('INPLACE_SUBTRACT',     inplace=True)
      , '*=':  varary('INPLACE_MULTIPLY',     inplace=True)
      , '**=': varary('INPLACE_POWER',        inplace=True)
      , '/=':  varary('INPLACE_TRUE_DIVIDE',  inplace=True)
      , '//=': varary('INPLACE_FLOOR_DIVIDE', inplace=True)
      , '%=':  varary('INPLACE_MODULO',       inplace=True)
      , '&=':  varary('INPLACE_AND',          inplace=True)
      , '^=':  varary('INPLACE_XOR',          inplace=True)
      , '|=':  varary('INPLACE_OR',           inplace=True)
      , '<<=': varary('INPLACE_LSHIFT',       inplace=True)
      , '>>=': varary('INPLACE_RSHIFT',       inplace=True)

      , '.':   lambda self, a, b: self.opcode('LOAD_ATTR',           a, arg=b, delta=1)
      , '.~':  lambda self, a, b: self.opcode('DELETE_ATTR',   None, a, arg=b, delta=1)
      , '!!~': lambda self, a, b: self.opcode('DELETE_SUBSCR', None, a,     b, delta=1)
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
# :param hook_pre: `MutableCode -> *` function called *before* `Compiler.compile`
#
# :param hook_post: same as `hook_pre`, but called *after* `Compiler.compile`
#
# :param subf_hook_pre: same as `hook_pre`, but not for this function.
#   If a function defined inside this function has its own `hook_pre`,
#   this parameter does not affect it. Otherwise, it is used as a fallback hook.
#
def function(self, args, code, hook_pre=0, hook_post=0, subf_hook_pre=0):

    args, kwargs, defs, kwdefs, varargs, varkwargs, code = syntax.function(args, code)
    self.load(**kwdefs)
    self.load(*defs)

    mcode = codegen.MutableCode(True, args, kwargs, varargs, varkwargs, self.code)

    f_hook_pre = getattr(self, '_function_hook_pre', 0)
    hook_pre = hook_pre or f_hook_pre
    hook_pre and hook_pre(mcode)

    self._function_hook_pre = subf_hook_pre
    self.compile(code, mcode, name='<lambda>')  # Ignore that for now.
    self._function_hook_pre = f_hook_pre

    hook_post and hook_post(mcode)
    code = mcode.compile('<lambda>')

    if code.co_freevars:

        for freevar in code.co_freevars:

            if freevar in self.code.varnames:

                # Make fast slot accessible from inner scopes.
                self.opcode('LOAD_FAST',   arg=freevar, delta=1)
                self.opcode('STORE_DEREF', arg=freevar, delta=-1)

            self.opcode('LOAD_CLOSURE', arg=freevar, delta=1)

        self.opcode('BUILD_TUPLE', arg=len(code.co_freevars), delta=-len(code.co_freevars) + 1)

    self.opcode(
        'MAKE_CLOSURE' if code.co_freevars else 'MAKE_FUNCTION',
        code,
        arg=len(defs) + 256 * len(kwdefs),
        delta=-len(kwdefs) * 2 - len(defs) - bool(code.co_freevars) + 1
    )


@r.builtin('inherit')
#
# `inherit: superclass... class_body`
#
# Create a new class deriving from all of the superclasses.
#
def inherit(self, *stuff):

    *args, block = stuff

    self.opcode('LOAD_BUILD_CLASS', delta=1)
    function(
        self, tree.Link('__locals__'), block,
        lambda code: (
            code.append('LOAD_FAST', '__locals__', 1),
            code.append('STORE_LOCALS', delta=-1),
            code.append('LOAD_NAME', '__name__', 1),
            code.append('STORE_NAME', '__module__', -1),
        ),
        lambda code: (
            code.bytecode.pop(),
            code.append('POP_TOP'),
            # LOAD_CLOSURE puts a *cell* onto the stack, not its contents.
            # The __class__ cell is empty by now.
            # CPython seems to perform some black magic to fill it.
            code.append('LOAD_CLOSURE', '__class__', 1),
            code.append('RETURN_VALUE'),
        ),
        lambda code: code.freevars.append('__class__')
    )
    self.call(None, '<class>', *args, preloaded=1)


@r.builtin('else')
#
# ``then `if` cond `else` otherwise``
# ``otherwise `unless` cond `else` then``
#
# Return `then` if `cond`, `otherwise` otherwise.
#
def else_(self, cond, otherwise):

    (then, cond), code = syntax.else_(cond)

    code = {
        const.COND.IF:     'POP_JUMP_IF_FALSE',
        const.COND.UNLESS: 'POP_JUMP_IF_TRUE',
    }[code]

    ptr = self.opcode(code,           cond, delta=0)
    jmp = self.opcode('JUMP_FORWARD', then, delta=0)
    ptr()
    self.load(otherwise)
    jmp()


@r.builtin('switch')
#
# ```
# switch:
#   case1 = action1
#   case2 = action2
#   ...
#   True  = default
# ```
#
# Evaluate the first action to be assigned to a True value.
#
def switch(self, cases):

    jumps = []

    for cond, action in syntax.switch(cases):

        jumps and jumps.pop(-2)()
        jumps.append(self.opcode('POP_JUMP_IF_FALSE', cond, delta=0))
        jumps.append(self.opcode('JUMP_FORWARD',    action, delta=0))

    jumps and jumps.pop(-2)()
    self.load(None)  # In case nothing matched.
    [jump() for jump in jumps]


@r.builtin('unsafe')
#
# ```
# unsafe:
#   exc_name = unsafe_code
#   exc_name :: Exception = caught_Exception
#   exc_name `is` None = caught_nothing
#   True = finally
# ```
#
# Catch an exception, store it as `exc_name`, evaluate the first matching
# clause, then evaluate `finally` unconditionally and re-raise the exception
# if it was not handled.
#
def unsafe(self, cases):

    # http://i2.kym-cdn.com/photos/images/original/000/234/765/b7e.jpg
    # That seems to work, though.
    (name, try_), *cases, (has_finally, finally_) = syntax.unsafe(cases)

    # This will be our return value.
    self.load(None)

    to_finally = has_finally and self.opcode('SETUP_FINALLY', delta=0)
    to_except  = self.opcode('SETUP_EXCEPT', delta=0)
    # Replace that None with the value returned by `try_`
    # to fool the POP_BLOCK instruction.
    self.opcode('ROT_TWO', try_, delta=1)
    self.opcode('POP_BLOCK', delta=-1)
    # Er, so there was no exception, let's store None instead.
    # Since we've already POPped_BLOCK, exceptions occured
    # during this assignment will be ignored.
    store(self, name, None)
    # XXX I don't know why is that needed.
    self.code.cstacksize -= 1

    # Jump over that block if there was no exception.
    # Finishing SETUP_EXCEPT with an exception pushes
    # 3 items onto the stack.
    #
    # Stack:: [try_, None] or [None, traceback, value, type]
    #
    to_else = self.opcode('JUMP_FORWARD', delta=3)
    to_except()
    self.opcode('ROT_TWO', delta=0)
    self.store_top(*syntax.assignment_target(name))
    self.opcode('ROT_TWO', delta=0)
    to_else()

    # The same `switch` statement as above...
    jumps = []

    for cond, case in cases:

        jumps and jumps.pop(-2)()
        jumps.append(self.opcode('POP_JUMP_IF_FALSE', cond, delta=0))
        # FIXME we can't return anything from handlers.
        self.opcode('POP_TOP', case, delta=0)
        jumps.append(self.opcode('JUMP_FORWARD', delta=0))

    jumps and jumps.pop(-2)()
    # This will re-raise the exception if nothing matched
    # (and there was an exception. And there is no `finally` clause.)
    self.opcode('END_FINALLY', delta=-3)

    # The problem is, now we need to POP_EXCEPT, but only
    # if there was a handled exception.

    # First, jump over this whole part if the exception was not handled.
    unhandled_exception = self.opcode('JUMP_FORWARD', delta=0)

    for jmp in jumps: jmp()

    # Second, check if the exception type is None, in which case
    # there was no exception at all.
    self.opcode('DUP_TOP', delta=1)
    self.opcode('COMPARE_OP', None, arg='is', delta=0)
    # Then skip POP_EXCEPT if that is the case.
    no_exception = self.opcode('POP_JUMP_IF_TRUE', delta=-1)

    self.opcode('POP_EXCEPT', delta=0)
    unhandled_exception()
    no_exception()

    if has_finally:

        # If the interpreter made it here, one of the `except` clauses matched.
        self.opcode('POP_BLOCK', delta=-1)
        self.load(None)

        to_finally()
        self.opcode('POP_TOP', finally_, delta=0)
        self.opcode('END_FINALLY', delta=0)

    # We should be left with a return value by now.


@r.builtin('raise')
#
# `raise: exception_object`
#
# Raise an exception, which is either a type or an instance of Exception.
#
def raise_(self, exc):

    self.opcode('DUP_TOP', exc, delta=2)
    self.opcode('RAISE_VARARGS', arg=1, delta=-1)

