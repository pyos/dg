from . import tree
from .. import const

MATCH_A = lambda p: lambda f: tree.matchA(f, p)
MATCH_Q = lambda p: lambda f: tree.matchQ(f, p)
UNCURRY = lambda p, n=...: lambda f, n=n: f[1:] if isinstance(f, tree.Expression) and tree.matchQ(f[0], p) else [f] if n is ... else n

def UNASSOC(p):

    def g(f):

        q = tree.matchA(f, p)
        return g(q.pop(0)) + q if q else [f]

    return g


ANY = tree.Link('_')

ST_CALL        = UNCURRY(tree.Link(''))
ST_PACK        = UNCURRY(tree.Link(','))
ST_PACK_STAR   = MATCH_A(tree.Expression((tree.Link(''),  tree.Link('*'),  ANY)))
ST_ARG_KW      = MATCH_A(tree.Expression((tree.Link(':'), ANY,             ANY)))
ST_ARG_VAR     = MATCH_Q(tree.Link('*'))
ST_ARG_VAR_KW  = MATCH_Q(tree.Link('**'))
ST_IMPORT      = MATCH_Q(tree.Expression((tree.Link(''), tree.Link('new'), tree.Link('import'))))
ST_IMPORT_SEP  = UNASSOC(tree.Expression((tree.Link('.'),  ANY, ANY)))
ST_IMPORT_REL  = MATCH_A(tree.Expression((tree.Link(''),   ANY, ANY)))
ST_ASSIGN      = MATCH_A(tree.Expression((tree.Link('='),  ANY, ANY)))
ST_ASSIGN_ATTR = MATCH_A(tree.Expression((tree.Link('.'),  ANY, ANY)))
ST_ASSIGN_ITEM = MATCH_A(tree.Expression((tree.Link('!!'), ANY, ANY)))


def error(description, at):

    (_, line, char), _, filename, text = at.location
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
        args = ST_IMPORT_SEP(name) or [name]

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
    pack = ST_PACK(var, ())

    if pack:

        # Allow one starred argument that is similar to `varargs`.
        star = [i for i, q in enumerate(pack) if ST_PACK_STAR(q)] or [-1]
        len(star) > 1 and error(const.ERR.MULTIPLE_VARARGS, pack[star[1]])
        star[0] > 255 and error(const.ERR.TOO_MANY_ITEMS_BEFORE_STAR, pack[star[0]])

        if star[0] >= 0:

            # Remove the star. We know it's there, that's enough.
            pack[star[0]], = ST_PACK_STAR(pack[star[0]])

        return const.AT.UNPACK, pack, [len(pack), star[0]]

    var_a = ST_ASSIGN_ATTR(var)
    var_i = ST_ASSIGN_ITEM(var)

    if var_a:

        rest, attr = var_a
        isinstance(attr, tree.Link) or error(const.ERR.NONCONST_ATTR, attr)
        return const.AT.ATTR, attr, rest

    if var_i:

        rest, item = var_i
        return const.AT.ITEM, item, rest

    isinstance(var, tree.Link) or error(const.ERR.NONCONST_VARNAME, var)
    return const.AT.NAME, var, []


def argspec(args, definition):

    arguments   = []  # `c.co_varnames[:c.co_argc]`
    kwarguments = []  # `c.co_varnames[c.co_argc:c.co_argc + c.co_kwonlyargc]`

    defaults    = []  # `f.__defaults__`
    kwdefaults  = {}  # `f.__kwdefaults__`

    varargs     = []  # `[]` or `[c.co_varnames[c.co_argc + c.co_kwonlyargc]]`
    varkwargs   = []  # `[]` or `[c.co_varnames[c.co_argc + c.co_kwonlyargc + 1]]`

    if not isinstance(args, tree.Constant) or args.value is not None:

        for arg in (ST_CALL(args) if definition else args):

            # 1. `**: _` should be the last argument.
            varkwargs and error(const.ERR.ARG_AFTER_VARARGS, arg)

            kw = ST_ARG_KW(arg)

            if not kw:

                if definition:

                    # 2.1. `_: _` should only be followed by `_: _`
                    #      unless `*: _` was already encountered.
                    defaults and not varargs and error(const.ERR.NO_DEFAULT, arg)
                    # 2.2. `_` is a positional argument name, and should be a link.
                    isinstance(arg, tree.Link) or error(const.ERR.NONCONST_ARGUMENT, arg)

                # If there was a `*: _`, this is a keyword-only argument.
                # Unless, of course, this is a function call, in which case
                # it doesn't really matter.
                (kwarguments if varargs and definition else arguments).append(arg)

            elif ST_ARG_VAR(kw[0]):

                # 3.1. `*: _` cannot be followed by another `*: _`.
                varargs and error(const.ERR.MULTIPLE_VARARGS, kw[0])
                varargs.append(kw[1])

            elif ST_ARG_VAR_KW(kw[0]):

                # 4.1. Just in case. Should not be triggered.
                varkwargs and error(const.ERR.MULTIPLE_VARKWARGS, kw[0])
                varkwargs.append(kw[1])

            else:

                name, default = kw

                # 5.1. `_: _` is a keyword argument, and its left side is a link.
                isinstance(name, tree.Link) or error(const.ERR.NONCONST_KEYWORD, name)

                # If there was a `*: _`, guess what.
                # Or if this is not a definition. It's easier to tell
                # whether the argument is a keyword that way.
                if varargs or not definition:

                    kwarguments.append(name)
                    kwdefaults[name] = default

                else:

                    arguments.append(name)
                    defaults.append(default)

    len(arguments) > 255 and error(const.ERR.TOO_MANY_ARGS, args)  # *sigh*
  # If this is a function call, not a definition:
  #        posargs,   _,           _,        kwargs,     varargs, varkwargs
    return arguments, kwarguments, defaults, kwdefaults, varargs, varkwargs
