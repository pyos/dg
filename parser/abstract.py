from . import core
from . import tree
from .. import const

ST_GROUP      = '(_)'

ST_ASSIGNMENT = '_ = _'
ST_FUNCTION   = '_ -> _'
ST_TUPLE_S    = '_,'
ST_TUPLE      = '_, _'
ST_CALL       = '_ _'
ST_NCALL      = ':_'
ST_DCALL      = '_ $ _'

ST_ARG_KW     = '_: _'
ST_ARG_VAR    = '*_'
ST_ARG_VAR_KW = '**_'

ST_IMPORT     = 'import'
ST_IMPORT_REL = '_ _'
ST_IMPORT_SEP = '_._'

ST_ASSIGN_ATTR = '_._'
ST_ASSIGN_ITEM = '_ !! _'

unwrap  = lambda f:    tree.matchR(f, ST_GROUP, lambda f, q: q.pop(-1))[-1]
uncurry = lambda f, p: tree.matchR(f, p,        lambda f, q: q.pop(-2))[::-1]


@ST_ASSIGNMENT
def assignment(self, var, expr):

    if tree.matchQ(expr, ST_IMPORT):

        var    = tree.matchA(var, ST_IMPORT_REL)
        parent = len(var[0]) if len(var) > 1 else 0
        var    = var[len(var) > 1]
        var, *args = uncurry(unwrap(var), ST_IMPORT_SEP)

        isinstance(var, tree.Link) or self.error(const.ERR_NONCONST_IMPORT)
        return '.'.join([var] + args), const.AT_IMPORT, var, parent

    return (expr,) + assignment_target(var)


def assignment_target(self, var):

    var  = unwrap(var)
    pack = uncurry(var, ST_TUPLE)
    pack = pack if len(pack) > 1 else tree.matchA(var, ST_TUPLE_S)

    if pack:

        star = [i for i, q in enumerate(pack) if tree.matchQ(q, ST_ARG_VAR)]

        if star:

            len(star) == 1 or self.error(const.ERR_MULTIPLE_VARARGS)

            star,  = star
            before = pack[:star]
            pack[star] = tree.matchA(pack[star], ST_ARG_VAR)[0]

            isinstance(pack[start], tree.Link) or self.error(const.ERR_NONCONST_STAR)
            return const.AT_UNPACK, map(assignment_target, var), len(pack), star

        return const.AT_UNPACK, map(assignment_target, var), len(pack), -1

    attr = tree.matchA(var, ST_ASSIGN_ATTR)
    item = tree.matchA(var, ST_ASSIGN_ITEM)

    if attr:

        isinstance(attr[1], tree.Link) or self.error(const.ERR_NONCONST_ATTR)
        return const.AT_ATTR, tuple(attr)

    if item:

        return const.AT_ITEM, tuple(item)

    isinstance(var, tree.Link) or self.error(const.ERR_NONCONST_VARNAME)
    return const.AT_NAME, var


@ST_FUNCTION
def function(self, args, code):

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
            varkwargs and self.error(const.ERR_ARG_AFTER_VARKWARGS)
            # 1. varargs and varkwargs can't have default values.
            default and (vararg or varkw) and self.error(const.ERR_VARARG_DEFAULT)
            # 2. all arguments between the first one with the default value
            #    and the varargs must have default values
            varargs or not defaults or default or self.error(const.ERR_NO_DEFAULT)
            # 3. only one vararg and one varkwarg is allowed
            varargs   and vararg and self.error(const.ERR_MULTIPLE_VARARGS)
            varkwargs and varkw  and self.error(const.ERR_MULTIPLE_VARKWARGS)
            # 4. guess what
            isinstance(arg, tree.Link) or self.error(const.ERR_NONCONST_VARNAME)

            # Put the argument into the appropriate list.
            default and not varargs and defaults.extend(default)
            default and     varargs and kwdefaults.__setitem__(arg, *default)
            (
                varargs     if vararg  else
                varkwargs   if varkw   else
                kwarguments if varargs else
                arguments
            ).append(arg)

    len(arguments) < 256 or self.error(const.ERR_TOO_MANY_ARGS)

    return arguments, kwarguments, defaults, kwdefaults, varargs, varkwargs, code


@ST_TUPLE
@ST_TUPLE_S
def tuple(self, init, *last):

    return uncurry(init, ST_TUPLE) + list(args))


@ST_CALL
@ST_NCALL
@ST_DCALL
def call(self, f, *args):

    f, *args = uncurry(f, ST_CALL) + list(args)

    posargs  = []
    kwargs   = {}
    vararg   = []
    varkwarg = []

    for arg in args:

        arg = unwrap(arg)

        kw = tree.matchA(arg, ST_ARG_KW)
        kw and kwargs.__setitem__(*kw)
        kw and not isinstance(kw, tree.Link) or self.error(const.ERR_NONCONST_KEYWORD)

        var = tree.matchA(arg, ST_ARG_VAR)
        var and vararg and self.error(const.ERR_MULTIPLE_VARARGS)
        var and vararg.extend(*var)

        varkw = tree.matchA(arg, ST_ARG_VAR_KW)
        varkw and varkwarg and self.error(const.ERR_MULTIPLE_VARKWARGS)
        varkw and varkwarg.extend(*varkw)

        var or kw or varkw or posargs.append(arg)

    return f, posargs, kwargs, vararg, varkwarg

