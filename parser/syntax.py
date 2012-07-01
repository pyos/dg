from . import core
from . import tree
from .. import const

# CONST
# {
_PARSER = core.Parser()
_CONSTS = dict(
    ST_GROUP      = '(_)'

  , ST_TUPLE_S    = '_,'
  , ST_TUPLE      = '_, _'
  , ST_CALL       = '_ _'

  , ST_ARG_KW     = '_: _'
  , ST_ARG_VAR    = '*_'
  , ST_ARG_VAR_KW = '**_'

  , ST_IMPORT     = 'import'
  , ST_IMPORT_REL = '_ _'
  , ST_IMPORT_SEP = '_._'

  , ST_ASSIGN_ATTR = '_._'
  , ST_ASSIGN_ITEM = '_ !! _'
)


globals().update({
    c: _PARSER.parse(v)[0]
    for c, v in _CONSTS.items()
})

del _PARSER
del _CONSTS
# }

# MISC
# {
# Drop outermost parentheses from a syntactic construct `f`.
unwrap  = lambda f:    tree.matchR(f, ST_GROUP, lambda f, q: q.pop(-1))[-1]

# Recursively match `f` with a binary operator `p`, returning all the operands.
uncurry = lambda f, p: tree.matchR(f, p,        lambda f, q: q.pop(-2))[::-1]
# }


def assignment(self, var, expr):

    if tree.matchQ(expr, ST_IMPORT):

        var    = tree.matchA(var, ST_IMPORT_REL) or [var]
        parent = var[0].count('.') if len(var) > 1 else 0
      # parent == (len(var[0]) if len(var) > 1 else 0) or self.error(...)

        var = var[len(var) > 1]
        var, *args = uncurry(unwrap(var), ST_IMPORT_SEP)

        isinstance(var, tree.Link) or self.error(const.ERR.NONCONST_IMPORT)
        return '.'.join([var] + args), const.AT.IMPORT, var, parent

    # Other assignment types do not depend on right-hand statement value.
    return (expr,) + assignment_target(self, var)


def assignment_target(self, var):

    # Attempt to do iterable unpacking first.
    var  = unwrap(var)
    pack = uncurry(var, ST_TUPLE)
    pack = pack if len(pack) > 1 else tree.matchA(var, ST_TUPLE_S)

    if pack:

        # Allow one starred argument that is similar to `varargs`.
        star = [i for i, q in enumerate(pack) if tree.matchQ(q, ST_ARG_VAR)] or [-1]
        len(star) == 1 or self.error(const.ERR.MULTIPLE_VARARGS)
        star[0] < 256  or self.error(const.ERR.TOO_MANY_ITEMS_BEFORE_STAR)

        if star[0] >= 0:

            # Remove the star. We know it's there, that's enough.
            pack[star], = tree.matchA(pack[star], ST_ARG_VAR)

        return const.AT.UNPACK, map(assignment_target, var), len(pack), star[0]

    attr = tree.matchA(var, ST_ASSIGN_ATTR)
    item = tree.matchA(var, ST_ASSIGN_ITEM)

    if attr:

        isinstance(attr[1], tree.Link) or self.error(const.ERR.NONCONST_ATTR)
        return const.AT.ATTR, tuple(attr)

    if item:

        return const.AT.ITEM, tuple(item)

    isinstance(var, tree.Link) or self.error(const.ERR.NONCONST_VARNAME)
    return const.AT.NAME, var


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
            varkwargs and self.error(const.ERR.ARG_AFTER_VARKWARGS)
            # 1. varargs and varkwargs can't have default values.
            default and (vararg or varkw) and self.error(const.ERR.VARARG_DEFAULT)
            # 2. all arguments between the first one with the default value
            #    and the varargs must have default values
            varargs or not defaults or default or self.error(const.ERR.NO_DEFAULT)
            # 3. only one vararg and one varkwarg is allowed
            varargs   and vararg and self.error(const.ERR.MULTIPLE_VARARGS)
            varkwargs and varkw  and self.error(const.ERR.MULTIPLE_VARKWARGS)
            # 4. guess what
            isinstance(arg, tree.Link) or self.error(const.ERR.NONCONST_VARNAME)

            # Put the argument into the appropriate list.
            default and not varargs and defaults.extend(default)
            default and     varargs and kwdefaults.__setitem__(arg, *default)
            (
                varargs     if vararg  else
                varkwargs   if varkw   else
                kwarguments if varargs else
                arguments
            ).append(arg)

    len(arguments) < 256 or self.error(const.ERR.TOO_MANY_ARGS)

    return arguments, kwarguments, defaults, kwdefaults, varargs, varkwargs, code


def tuple(self, init, *last):

    return uncurry(init, ST_TUPLE) + list(last)


def call_pre(self, f, *args):

    return uncurry(f, ST_CALL) + list(args)


def call(self, f, *args):

    posargs  = []
    kwargs   = {}
    vararg   = []
    varkwarg = []

    for arg in args:

        arg = unwrap(arg)

        kw = tree.matchA(arg, ST_ARG_KW)
        kw and kwargs.__setitem__(*kw)
        kw and not isinstance(kw, tree.Link) and self.error(const.ERR.NONCONST_KEYWORD)

        var = tree.matchA(arg, ST_ARG_VAR)
        var and vararg and self.error(const.ERR.MULTIPLE_VARARGS)
        var and vararg.extend(*var)

        varkw = tree.matchA(arg, ST_ARG_VAR_KW)
        varkw and varkwarg and self.error(const.ERR.MULTIPLE_VARKWARGS)
        varkw and varkwarg.extend(*varkw)

        var or kw or varkw or posargs.append(arg)

    return f, posargs, kwargs, vararg, varkwarg

