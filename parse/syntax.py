from . import r
from . import tree
from .. import const

# CONST
# {
globals().update({
    n: r(v)[0] for n, v in
    dict(
        ST_GROUP = '(_)'

      , ST_TUPLE_S = '_,'
      , ST_TUPLE   = '_, _'
      , ST_CALL    = '_ _'

      , ST_ARG_KW       = '_: _'
      , ST_ARG_VAR      = '*_'
      , ST_ARG_VAR_KW   = '**_'
      , ST_ARG_VAR_C    = '(*)'
      , ST_ARG_VAR_KW_C = '(**)'

      , ST_IMPORT     = 'import'
      , ST_IMPORT_REL = '_ _'
      , ST_IMPORT_SEP = '_._'

      , ST_ASSIGN_ATTR = '_._'
      , ST_ASSIGN_ITEM = '_ !! _'
    ).items()
})
# }

# MISC
# {
# Drop outermost parentheses from a syntactic construct `f`.
unwrap  = lambda f:    tree.matchR(f, ST_GROUP, lambda f, q: q.pop(-1))[-1]

# Recursively match `f` with a binary operator `p`, returning all the operands.
uncurry = lambda f, p: tree.matchR(f, p,        lambda f, q: q.pop(-2))[::-1]

# Same as `assert not ...`, but without `AssertionError`.
def ERROR(pred, msg):

    if pred:

        raise Exception(msg)
# }


def assignment(var, expr):

    if tree.matchQ(expr, ST_IMPORT):

        var    = tree.matchA(var, ST_IMPORT_REL) or [var]
        parent = var[0].count('.') if len(var) > 1 else 0
      # ERROR(parent != (len(var[0]) if len(var) > 1 else 0), ...)

        var = var[len(var) > 1]
        var, *args = uncurry(unwrap(var), ST_IMPORT_SEP)

        ERROR(not isinstance(var, tree.Link), const.ERR.NONCONST_IMPORT)
        return '.'.join([var] + args), const.AT.IMPORT, var, parent

    # Other assignment types do not depend on right-hand statement value.
    return (expr,) + assignment_target(var)


def assignment_target(var):

    # Attempt to do iterable unpacking first.
    var  = unwrap(var)
    pack = uncurry(var, ST_TUPLE)
    pack = pack if len(pack) > 1 else tree.matchA(var, ST_TUPLE_S)

    if pack:

        # Allow one starred argument that is similar to `varargs`.
        star = [i for i, q in enumerate(pack) if tree.matchQ(q, ST_ARG_VAR)] or [-1]
        ERROR(len(star) < 2, const.ERR.MULTIPLE_VARARGS)
        ERROR(star[0] > 255, const.ERR.TOO_MANY_ITEMS_BEFORE_STAR)

        if star[0] >= 0:

            # Remove the star. We know it's there, that's enough.
            pack[star[0]], = tree.matchA(pack[star[0]], ST_ARG_VAR)

        return const.AT.UNPACK, map(assignment_target, var), len(pack), star[0]

    attr = tree.matchA(var, ST_ASSIGN_ATTR)
    item = tree.matchA(var, ST_ASSIGN_ITEM)

    if attr:

        ERROR(not isinstance(attr[1], tree.Link), const.ERR.NONCONST_ATTR)
        return const.AT.ATTR, tuple(attr)

    if item:

        return const.AT.ITEM, tuple(item)

    ERROR(not isinstance(var, tree.Link), const.ERR.NONCONST_VARNAME)
    return const.AT.NAME, var


def function(args, code):

    arguments   = []  # `c.co_varnames[:c.co_argc]`
    kwarguments = []  # `c.co_varnames[c.co_argc:c.co_argc + c.co_kwonlyargc]`

    defaults    = []  # `f.__defaults__`
    kwdefaults  = {}  # `f.__kwdefaults__`

    varargs     = []  # [] or [name of a varargs container]
    varkwargs   = []  # [] or [name of a varkwargs container]

    if not isinstance(args, tree.Closure) or args:

        # Either a single argument, or multiple arguments separated by commas.
        for arg in uncurry(unwrap(args), ST_TUPLE):

            arg, *default = tree.matchA(arg, ST_ARG_KW) or [arg]
            vararg = tree.matchA(arg, ST_ARG_VAR)
            varkw  = tree.matchA(arg, ST_ARG_VAR_KW)
            # Extract argument name from `vararg` or `varkw`.
            arg, = vararg or varkw or [arg]

            # Syntax checks.
            # 0. varkwargs should be the last argument
            ERROR(varkwargs, const.ERR.ARG_AFTER_VARKWARGS)
            # 1. varargs and varkwargs can't have default values.
            ERROR(default and (vararg or varkw), const.ERR.VARARG_DEFAULT)
            # 2. all arguments between the first one with the default value
            #    and the varargs must have default values
            ERROR(not varargs and defaults and not default, const.ERR.NO_DEFAULT)
            # 3. only one vararg and one varkwarg is allowed
            ERROR(varargs   and vararg, const.ERR.MULTIPLE_VARARGS)
            ERROR(varkwargs and varkw,  const.ERR.MULTIPLE_VARKWARGS)
            # 4. guess what
            ERROR(not isinstance(arg, tree.Link), const.ERR.NONCONST_ARGUMENT)

            # Put the argument into the appropriate list.
            default and not varargs and defaults.extend(default)
            default and     varargs and kwdefaults.__setitem__(arg, *default)
            (
                varargs     if vararg  else
                varkwargs   if varkw   else
                kwarguments if varargs else
                arguments
            ).append(arg)

    ERROR(len(arguments) > 255, const.ERR.TOO_MANY_ARGS)

    return arguments, kwarguments, defaults, kwdefaults, varargs, varkwargs, code


def tuple(init, *last):

    return uncurry(init, ST_TUPLE) + list(last)


def call_pre(f, *args):

    f, *args2 = uncurry(f, ST_CALL)
    f, *args3 = tree.matchA(f, ST_ARG_KW) or [f]
    return [f] + args3 + args2 + list(args)


def call(f, *args):

    posargs  = []
    kwargs   = {}
    vararg   = []
    varkwarg = []

    for arg in args:

        kw = tree.matchA(arg, ST_ARG_KW)

        if not kw:

            posargs.append(arg)

        elif tree.matchQ(kw[0], ST_ARG_VAR_C):

            ERROR(vararg, const.ERR.MULTIPLE_VARARGS)
            vararg.append(kw[1])

        elif tree.matchQ(kw[0], ST_ARG_VAR_KW_C):

            ERROR(varkwarg, const.ERR.MULTIPLE_VARKWARGS)
            varkwarg.append(kw[1])

        else:

            ERROR(not isinstance(kw[0], tree.Link), const.ERR.NONCONST_KEYWORD)
            kwargs.__setitem__(*kw)

    return f, posargs, kwargs, vararg, varkwarg

