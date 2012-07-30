from . import tree
from .. import const

MATCH_A = lambda p: lambda f: tree.matchA(f, p)
MATCH_Q = lambda p: lambda f: tree.matchQ(f, p)
UNCURRY = lambda p: lambda f, n=None: f[1:] if isinstance(f, tree.Expression) and tree.matchQ(f[0], p) else [f] if n is None else n

ST_BREAK        = UNCURRY(tree.Link('\n'))
ST_EXC_FINALLY  = MATCH_Q(tree.Link('True'))
ST_TUPLE        = UNCURRY(tree.Link(','))
ST_ASSIGN       = MATCH_A(tree.Expression((tree.Link('='),      tree.Link('_'),  tree.Link('_'))))
ST_EXPR_IF      = MATCH_A(tree.Expression((tree.Link('if'),     tree.Link('_'),  tree.Link('_'))))
ST_EXPR_UNLESS  = MATCH_A(tree.Expression((tree.Link('unless'), tree.Link('_'),  tree.Link('_'))))
ST_ARG_KW       = MATCH_A(tree.Expression((tree.Link(':'),      tree.Link('_'),  tree.Link('_'))))
ST_ARG_VAR      = MATCH_A(tree.Expression((tree.Link(''),       tree.Link('*'),  tree.Link('_'))))
ST_ARG_VAR_KW   = MATCH_A(tree.Expression((tree.Link(''),       tree.Link('**'), tree.Link('_'))))
ST_ARG_VAR_C    = MATCH_Q(tree.Link('*'))
ST_ARG_VAR_KW_C = MATCH_Q(tree.Link('**'))
ST_IMPORT       = MATCH_Q(tree.Link('import'))
ST_IMPORT_SEP   = UNCURRY(tree.Link('.'))
ST_IMPORT_REL   = MATCH_A(tree.Expression((tree.Link(''),   tree.Link('_'), tree.Link('_'))))
ST_ASSIGN_ATTR  = MATCH_A(tree.Expression((tree.Link('.'),  tree.Link('_'), tree.Link('_'))))
ST_ASSIGN_ITEM  = MATCH_A(tree.Expression((tree.Link('!!'), tree.Link('_'), tree.Link('_'))))


def assignment(var, expr):

    if ST_IMPORT(expr):

        var = ST_IMPORT_REL(var) or [tree.Link(), var]
        isinstance(var[0], tree.Link) or const.ERR.NONCONST_IMPORT
        parent = var[0].count('.')
        parent == len(var[0]) or const.ERR.NONCONST_IMPORT
        args = ST_IMPORT_SEP(var[-1])
        all(isinstance(a, tree.Link) for a in args) or const.ERR.NONCONST_IMPORT
        return '.'.join(args), const.AT.IMPORT, args[0], parent

    # Other assignment types do not depend on right-hand statement value.
    return (expr,) + assignment_target(var)


def assignment_target(var):

    # Attempt to do iterable unpacking first.
    pack = ST_TUPLE(var, ())

    if pack:

        # Allow one starred argument that is similar to `varargs`.
        star = [i for i, q in enumerate(pack) if ST_ARG_VAR(q)] or [-1]
        len(star) > 1 and const.ERR.MULTIPLE_VARARGS
        star[0] > 255 and const.ERR.TOO_MANY_ITEMS_BEFORE_STAR

        if star[0] >= 0:

            # Remove the star. We know it's there, that's enough.
            pack[star[0]], = ST_ARG_VAR(pack[star[0]])

        return const.AT.UNPACK, map(assignment_target, pack), len(pack), star[0]

    attr = ST_ASSIGN_ATTR(var)
    item = ST_ASSIGN_ITEM(var)

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
        for arg in ST_TUPLE(args):

            arg, *default = ST_ARG_KW(arg) or [arg]
            vararg = ST_ARG_VAR(arg)
            varkw  = ST_ARG_VAR_KW(arg)
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

    args2 = ST_ARG_KW(args1[0]) or args1[:1]
    attr  = ST_ASSIGN_ATTR(args2[0])
    attr and not isinstance(attr[1], tree.Link) and const.ERR.NONCONST_ATTR
    return [attr] + args2 + args1[1:]


def call_args(args):

    posargs  = []
    kwargs   = {}
    vararg   = []
    varkwarg = []

    for arg in args:

        kw = ST_ARG_KW(arg)

        if not kw or arg.closed:

            # The only place where `(a: b)` != `a: b`.
            # `a: b` is a keyword argument while `(a: b)` is a function call.
            # Note that `kw` *implies* `hasattr(arg, 'closed')`, since
            # `ST_ARG_KW` can only match an expression.
            posargs.append(arg)

        elif ST_ARG_VAR_C(kw[0]):

            vararg and const.ERR.MULTIPLE_VARARGS
            vararg.append(kw[1])

        elif ST_ARG_VAR_KW_C(kw[0]):

            varkwarg and const.ERR.MULTIPLE_VARKWARGS
            varkwarg.append(kw[1])

        else:

            isinstance(kw[0], tree.Link) or const.ERR.NONCONST_KEYWORD
            kwargs.__setitem__(*kw)

    return posargs, kwargs, vararg, varkwarg
