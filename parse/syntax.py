from . import r
from . import tree
from .. import const

ST_EXC_FINALLY = 'True'

ST_TUPLE_S = '_,'
ST_TUPLE   = ','
ST_ASSIGN  = '_ = _'

ST_EXPR_IF     = '_ `if` _'
ST_EXPR_UNLESS = '_ `unless` _'

ST_ARG_KW       = '_: _'
ST_ARG_VAR      = '*_'
ST_ARG_VAR_KW   = '**_'
ST_ARG_VAR_C    = '*'
ST_ARG_VAR_KW_C = '**'

ST_IMPORT     = 'import'
ST_IMPORT_REL = '_ _'
ST_IMPORT_SEP = '.'

ST_ASSIGN_ATTR = '_._'
ST_ASSIGN_ITEM = '_ !! _'

consts = [_ for _ in globals() if _.startswith('ST_')]
values = r().parse('\n'.join(map(globals().__getitem__, consts)))[1:]
list(map(globals().__setitem__, consts, values))

ST_BREAK = tree.Link('\n')

# Match `f` with a varary operator `p`, returning either the operands or `f`.
uncurry = lambda f, p: f[1:] if isinstance(f, tree.Expression) and tree.matchQ(f[0], p) else [f]


def assignment(var, expr):

    if tree.matchQ(expr, ST_IMPORT):

        var = tree.matchA(var, ST_IMPORT_REL) or [tree.Link(), var]
        isinstance(var[0], tree.Link) or const.ERR.NONCONST_IMPORT
        parent = var[0].count('.')
        parent == len(var[0]) or const.ERR.NONCONST_IMPORT
        args = uncurry(var[-1], ST_IMPORT_SEP)
        all(isinstance(a, tree.Link) for a in args) or const.ERR.NONCONST_IMPORT
        return '.'.join(args), const.AT.IMPORT, args[0], parent

    # Other assignment types do not depend on right-hand statement value.
    return (expr,) + assignment_target(var)


def assignment_target(var):

    # Attempt to do iterable unpacking first.
    pack = uncurry(var, ST_TUPLE)
    pack = pack if len(pack) > 1 else tree.matchA(var, ST_TUPLE_S)

    if pack:

        # Allow one starred argument that is similar to `varargs`.
        star = [i for i, q in enumerate(pack) if tree.matchQ(q, ST_ARG_VAR)] or [-1]
        len(star) > 1 and const.ERR.MULTIPLE_VARARGS
        star[0] > 255 and const.ERR.TOO_MANY_ITEMS_BEFORE_STAR

        if star[0] >= 0:

            # Remove the star. We know it's there, that's enough.
            pack[star[0]], = tree.matchA(pack[star[0]], ST_ARG_VAR)

        return const.AT.UNPACK, map(assignment_target, pack), len(pack), star[0]

    attr = tree.matchA(var, ST_ASSIGN_ATTR)
    item = tree.matchA(var, ST_ASSIGN_ITEM)

    if attr:

        isinstance(attr[1], tree.Link) or const.ERR.NONCONST_ATTR
        return const.AT.ATTR, tuple(attr)

    if item:

        return const.AT.ITEM, tuple(item)

    isinstance(var, tree.Link) or const.ERR.NONCONST_VARNAME
    return const.AT.NAME, var


def function(args, code):

    arguments   = []  # `c.co_varnames[:c.co_argc]`
    kwarguments = []  # `c.co_varnames[c.co_argc:c.co_argc + c.co_kwonlyargc]`

    defaults    = []  # `f.__defaults__`
    kwdefaults  = {}  # `f.__kwdefaults__`

    varargs     = []  # [] or [name of a varargs container]
    varkwargs   = []  # [] or [name of a varkwargs container]

    if args is not None:

        # Either a single argument, or multiple arguments separated by commas.
        for arg in uncurry(args, ST_TUPLE):

            arg, *default = tree.matchA(arg, ST_ARG_KW) or [arg]
            vararg = tree.matchA(arg, ST_ARG_VAR)
            varkw  = tree.matchA(arg, ST_ARG_VAR_KW)
            # Extract argument name from `vararg` or `varkw`.
            arg, = vararg or varkw or [arg]

            # Syntax checks.
            # 0. varkwargs should be the last argument
            varkwargs and const.ERR.ARG_AFTER_VARKWARGS
            # 1. varargs and varkwargs can't have default values.
            default and (vararg or varkw) and const.ERR.VARARG_DEFAULT
            # 2. all arguments between the first one with the default value
            #    and the varargs must have default values
            not varargs and defaults and not default and const.ERR.NO_DEFAULT
            # 3. only one vararg and one varkwarg is allowed
            varargs   and vararg and const.ERR.MULTIPLE_VARARGS
            varkwargs and varkw  and const.ERR.MULTIPLE_VARKWARGS
            # 4. guess what
            isinstance(arg, tree.Link) or const.ERR.NONCONST_ARGUMENT

            # Put the argument into the appropriate list.
            default and not varargs and defaults.extend(default)
            default and     varargs and kwdefaults.__setitem__(arg, *default)
            (
                varargs     if vararg  else
                varkwargs   if varkw   else
                kwarguments if varargs else
                arguments
            ).append(arg)

    len(arguments) > 255 and const.ERR.TOO_MANY_ARGS
    return arguments, kwarguments, defaults, kwdefaults, varargs, varkwargs, code


def call_pre(args1):

    args2 = tree.matchA(args1[0], ST_ARG_KW) or args1[:1]
    attr  = tree.matchA(args2[0], ST_ASSIGN_ATTR)
    attr and not isinstance(attr[1], tree.Link) and const.ERR.NONCONST_ATTR
    return [attr] + args2 + args1[1:]


def call_args(args):

    posargs  = []
    kwargs   = {}
    vararg   = []
    varkwarg = []

    for arg in args:

        kw = tree.matchA(arg, ST_ARG_KW)

        if not kw or arg.closed:

            # The only place where `(a: b)` != `a: b`.
            # `a: b` is a keyword argument while `(a: b)` is a function call.
            # Note that `kw` *implies* `hasattr(arg, 'closed')`, since
            # `ST_ARG_KW` can only match an expression.
            posargs.append(arg)

        elif tree.matchQ(kw[0], ST_ARG_VAR_C):

            vararg and const.ERR.MULTIPLE_VARARGS
            vararg.append(kw[1])

        elif tree.matchQ(kw[0], ST_ARG_VAR_KW_C):

            varkwarg and const.ERR.MULTIPLE_VARKWARGS
            varkwarg.append(kw[1])

        else:

            isinstance(kw[0], tree.Link) or const.ERR.NONCONST_KEYWORD
            kwargs.__setitem__(*kw)

    return posargs, kwargs, vararg, varkwarg
