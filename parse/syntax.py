from . import tree
from .. import const

MATCH_A = lambda p: lambda f: tree.matchA(f, p)
MATCH_Q = lambda p: lambda f: tree.matchQ(f, p)
UNCURRY = lambda p, n=...: lambda f, n=n: f[1:] if isinstance(f, tree.Expression) and tree.matchQ(f[0], p) else [f] if n is ... else n

ANY = tree.Link('_')

ST_BREAK        = UNCURRY(tree.Link('\n'))
ST_TUPLE        = UNCURRY(tree.Link(','))
ST_ARG_KW       = UNCURRY(tree.Link(':'))
ST_ARG_VAR      = MATCH_A(tree.Expression((tree.Link(''), tree.Link('*'),  ANY)))
ST_ARG_VAR_KW   = MATCH_A(tree.Expression((tree.Link(''), tree.Link('**'), ANY)))
ST_ARG_VAR_C    = MATCH_Q(tree.Link('*'))
ST_ARG_VAR_KW_C = MATCH_Q(tree.Link('**'))
ST_IMPORT       = MATCH_Q(tree.Expression((tree.Link(':'), tree.Link('import'))))
ST_IMPORT_SEP   = UNCURRY(tree.Link('.'))
ST_IMPORT_REL   = MATCH_A(tree.Expression((tree.Link(''), ANY, ANY)))
ST_ASSIGN       = MATCH_A(tree.Expression((tree.Link('='), ANY, ANY)))
ST_ASSIGN_ATTR  = UNCURRY(tree.Link('.'))
ST_ASSIGN_ITEM  = UNCURRY(tree.Link('!!'))


def error(description, at):

    (_, line, char), _, filename, text = at.reparse_location
    raise SyntaxError(description, (filename, line, char, text))


# assignment::
#
#   assignment_target = expression
#   dotname = link('import')
#
# where::
#
#   dotname = link(.*) | link('.' *) link(.*)
#
def assignment(var, expr):

    if ST_IMPORT(expr):

        parent, name = ST_IMPORT_REL(var) or [tree.Link(''), var]
        args = ST_IMPORT_SEP(name)

        if isinstance(parent, tree.Link) and len(parent) == parent.count('.') and all(isinstance(a, tree.Link) for a in args):

            return args[0], '.'.join(args), len(parent)

    # Other assignment types do not depend on right-hand statement value.
    return var, expr, False


# assignment_target::
#
#   link(.*)
#   expression.link(.*)
#   expression !! expression
#   expression(',', assignment_target *)
#
def assignment_target(var):

    # Attempt to do iterable unpacking first.
    pack = ST_TUPLE(var, ())

    if pack:

        # Allow one starred argument that is similar to `varargs`.
        star = [i for i, q in enumerate(pack) if ST_ARG_VAR(q)] or [-1]
        len(star) > 1 and error(const.ERR.MULTIPLE_VARARGS, pack[star[1]])
        star[0] > 255 and error(const.ERR.TOO_MANY_ITEMS_BEFORE_STAR, pack[star[0]])

        if star[0] >= 0:

            # Remove the star. We know it's there, that's enough.
            pack[star[0]], = ST_ARG_VAR(pack[star[0]])

        return const.AT.UNPACK, pack, [len(pack), star[0]]

    *var_a, attr = ST_ASSIGN_ATTR(var, [var])
    *var_i, item = ST_ASSIGN_ITEM(var, [var])

    if var_a:

        isinstance(attr, tree.Link) or error(const.ERR.NONCONST_ATTR, attr[1])
        return const.AT.ATTR, attr, var_a

    if var_i:

        return const.AT.ITEM, item, var_i

    isinstance(var, tree.Link) or error(const.ERR.NONCONST_VARNAME, var)
    return const.AT.NAME, var, []


# function::
#
#   positional *, default *, ( varargs, ( positional | default ) * ) ?, varkwargs ?
#
# where::
#
#   positional = link(.*)
#   default    = positional: expression
#   varargs    = *positional
#   varkwargs  = **positional
#
def function(args):

    arguments   = []  # `c.co_varnames[:c.co_argc]`
    kwarguments = []  # `c.co_varnames[c.co_argc:c.co_argc + c.co_kwonlyargc]`

    defaults    = []  # `f.__defaults__`
    kwdefaults  = {}  # `f.__kwdefaults__`

    varargs     = []  # `[]` or `[c.co_varnames[c.co_argc + c.co_kwonlyargc]]`
    varkwargs   = []  # `[]` or `[c.co_varnames[c.co_argc + c.co_kwonlyargc + 1]]`

    if not isinstance(args, tree.Constant) or args.value is not None:

        # Either a single argument, or multiple arguments separated by commas.
        for arg in ST_TUPLE(args):

            arg, *default = ST_ARG_KW(arg)
            vararg = ST_ARG_VAR(arg)
            varkw  = ST_ARG_VAR_KW(arg)
            # Extract argument name from `vararg` or `varkw`.
            arg, = vararg or varkw or [arg]

            # Syntax checks.
            # 0. varkwargs should be the last argument
            varkwargs and error(const.ERR.ARG_AFTER_VARKWARGS, arg)
            # 1. varargs and varkwargs can't have default values.
            default and (vararg or varkw) and error(const.ERR.VARARG_DEFAULT, arg)
            # 2. all arguments between the first one with the default value
            #    and the varargs must have default values
            not varargs and defaults and not default and error(const.ERR.NO_DEFAULT, arg)
            # 3. only one vararg and one varkwarg is allowed
            varargs   and vararg and error(const.ERR.MULTIPLE_VARARGS, arg)
            varkwargs and varkw  and error(const.ERR.MULTIPLE_VARKWARGS, arg)
            # 4. guess what
            isinstance(arg, tree.Link) or error(const.ERR.NONCONST_ARGUMENT, arg)

            # Put the argument into the appropriate list.
            default and not varargs and defaults.extend(default)
            default and     varargs and kwdefaults.__setitem__(arg, *default)
            (
                varargs     if vararg  else
                varkwargs   if varkw   else
                kwarguments if varargs else
                arguments
            ).append(arg)

    len(arguments) > 255 and error(const.ERR.TOO_MANY_ARGS, args)
    return arguments, kwarguments, defaults, kwdefaults, varargs, varkwargs


# call_pre::
#
#   expression: expression
#   expression('', expression, expression *)
#   expression('', expression: expression, expression *)
#
def call_pre(argv):

    # `a: b c`:: one function call
    # `(a: b) c`:: two function calls
    f, *args = argv
    argx = [f] if f is None or f.closed else ST_ARG_KW(f)
    return argx + args


# call_args::
#
#   any *
#   any *, varargs, any *
#   any *, varkwargs, any *
#   any *, varargs, any *, varkwargs, any *
#   any *, varkwargs, any *, varargs, any *
#
# where::
#
#   any = link(.*): expression | expression
#
def call_args(args):

    posargs  = []
    kwargs   = {}
    vararg   = []
    varkwarg = []

    for arg in args:

        kw = ST_ARG_KW(arg, ())

        if not kw or arg.closed:

            # `a: b`:: keyword argument
            # `(a: b)`:: function call
            posargs.append(arg)

        elif ST_ARG_VAR_C(kw[0]):

            # Shouldn't `a: (*): b (*): c` become `a: (*): (itertools.chain: b c)`?
            vararg and error(const.ERR.MULTIPLE_VARARGS, kw[0])
            vararg.append(kw[1])

        elif ST_ARG_VAR_KW_C(kw[0]):

            varkwarg and error(const.ERR.MULTIPLE_VARKWARGS, kw[0])
            varkwarg.append(kw[1])

        else:

            isinstance(kw[0], tree.Link) or error(const.ERR.NONCONST_KEYWORD, kw[0])
            kwargs.__setitem__(*kw)

    return posargs, kwargs, vararg, varkwarg
