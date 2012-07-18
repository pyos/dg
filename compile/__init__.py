from . import core
from .. import const
from ..parse import tree
from ..parse import syntax


def varary(multiple, arg=0, inplace=False, single=None):

    def f(self, a, *bs):

        self.load(a)
        ps = [self.opcode(multiple, b, arg=arg, delta=0) for b in bs]
        ps or self.opcode(single,      arg=arg, delta=0)
        inplace and store_top(self, *syntax.assignment_target(a))

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
      , ',':  lambda self, a, *bs: self.opcode('BUILD_TUPLE', *syntax.tuple_(a, *bs), delta=1)
      , '$':  lambda self, a, *bs, c=tree.Closure: self.call(a, *[c([b]) for b in bs] or [c()])
      , ':.': lambda self, a, *bs: (self.call(a), [self.opcode('LOAD_ATTR', arg=b, delta=0) for b in bs])

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

    fake_methods = {}


@r.builtin('while', fake_method=True)
#
# `var.while: expr`
#
# Evaluate `expr` while `var` is true.
#
def while_(self, cond, block):

    self.load(None)
    exit_ptr = self.opcode('SETUP_LOOP', delta=0)
    cond_ptr = self.opcode('JUMP_ABSOLUTE', arg=-1, delta=0)
    else_ptr = self.opcode('POP_JUMP_IF_FALSE', cond, delta=0)
    self.opcode('ROT_TWO', block, delta=1)
    self.opcode('POP_TOP', delta=-1)
    cond_ptr()
    else_ptr()
    self.opcode('POP_BLOCK', delta=0)
    exit_ptr()


@r.builtin('for', fake_method=True)
@r.callable
#
# `var.each: variable stuff`
#
# Equivalent to `for variable in var: stuff`.
#
def each(self, iterable, each, do):

    self.opcode('GET_ITER', None, iterable, delta=2)

    loop_ptr = self.opcode('JUMP_ABSOLUTE', arg=-1, delta=0)
    end_ptr  = self.opcode('FOR_ITER', delta=1)

    store_top(self, *syntax.assignment_target(each), dup=False)
    self.load(do)
    self.opcode('ROT_THREE', delta=0)
    self.opcode('ROT_TWO',   delta=0)
    self.opcode('POP_TOP',   delta=-1)

    loop_ptr()
    end_ptr()

    # FOR_ITER popped `iterable` off the stack.
    self.code.cstacksize -= 1


@r.builtin('=')
#
# `var = expr`
#
# Assign `var` the value of `expr`.
#
def store(self, var, expr):

    expr, type, var, *args = syntax.assignment(var, expr)

    if type == const.AT.IMPORT:

        self.opcode('IMPORT_NAME', args[0], None, arg=expr, delta=1)

    else:

        self.load(expr)

    store_top(self, type, var, *args)


def store_top(self, type, var, *args, dup=True):

    dup and self.opcode('DUP_TOP', delta=1)

    if type == const.AT.UNPACK:

        ln, star = args
        op  = 'UNPACK_SEQUENCE'            if star < 0 else 'UNPACK_EX'
        arg = star + 256 * (ln - star - 1) if star > 0 else ln
        self.opcode(op, arg=arg, delta=ln - 1)

        for item in var:

            store_top(self, *item, dup=False)

    elif type == const.AT.ATTR:

        syntax.ERROR(var[1] in self.fake_methods, const.ERR.FAKE_METHOD_ASSIGNMENT)
        self.opcode('STORE_ATTR', var[0], arg=var[1], delta=-1)

    elif type == const.AT.ITEM:

        self.opcode('STORE_SUBSCR', *var, delta=-1)

    else:

        syntax.ERROR(var in self.builtins, const.ERR.BUILTIN_ASSIGNMENT)
        syntax.ERROR(var in self.fake_methods, const.ERR.BUILTIN_ASSIGNMENT)
        syntax.ERROR(var in self.code.cellnames, const.ERR.FREEVAR_ASSIGNMENT)

        self.opcode(
            'STORE_DEREF' if var in self.code.cellvars else
            'STORE_NAME'  if self.code.slowlocals else
            'STORE_FAST',
            arg=var, delta=-1
        )


@r.builtin('->')
#
# `argspec -> body`
#
# Allow to evaluate `body` passing it stuff that matches `argspec`.
#
def function(self, args, code):

    args, kwargs, defs, kwdefs, varargs, varkwargs, code = syntax.function(args, code)
    self.load(**kwdefs)
    self.load(*defs)

    mcode = codegen.MutableCode(True, args, kwargs, varargs, varkwargs, self.code)

    hasattr(self.code, 'f_hook') and self.code.f_hook(mcode)
    code = self.compile(code, mcode, name='<lambda>')

    self.opcode(
        'MAKE_CLOSURE' if preload_free(self, code) else 'MAKE_FUNCTION',
        code,
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

    return code.co_freevars


@r.builtin('inherit')
#
# `inherit: superclass... class_body`
#
# Create a new class deriving from all of the superclasses.
#
def inherit(self, *stuff):

    *args, block = stuff

    mcode = codegen.MutableCode(True, ['__locals__'], cell=self.code)
    mcode.cellnames.add('__class__')
    mcode.append('LOAD_FAST', '__locals__', 1)
    mcode.append('STORE_LOCALS', delta=-1)
    mcode.append('LOAD_NAME', '__name__', 1)
    mcode.append('STORE_NAME', '__module__', -1)
    mcode.f_hook = lambda code: code.freevars.append('__class__')

    self.compile(block, mcode, name='<lambda>')

    # Return the empty __class__ cell.
    mcode.bytecode.pop()
    mcode.append('POP_TOP')
    mcode.append('LOAD_CLOSURE', '__class__', 1)
    mcode.append('RETURN_VALUE', delta=-1)
    code = mcode.compile()

    self.opcode('LOAD_BUILD_CLASS', delta=1)
    self.opcode(
        'MAKE_CLOSURE' if preload_free(self, code) else 'MAKE_FUNCTION',
        code, arg=0, delta=1 - bool(code.co_freevars)
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

    is_if, (then, cond) = syntax.else_(cond)

    code = 'POP_JUMP_IF_FALSE' if is_if else 'POP_JUMP_IF_TRUE'
    ptr  = self.opcode(code,           cond, delta=0)
    jmp  = self.opcode('JUMP_FORWARD', then, delta=0)
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
    store_top(self, *syntax.assignment_target(name))
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
@r.callable
#
# `raise: exception_object`
#
# Raise an exception, which is either a type or an instance of Exception.
#
def raise_(self, exception, caused_by=...):

    args = (exception,) if caused_by is ... else (exception, caused_by)
    self.opcode('RAISE_VARARGS', *args, delta=0)
    self.load(None)  # we've got to return something
