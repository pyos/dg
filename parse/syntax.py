from . import tree
from .. import const


def binary_op(id, expr, on_error):

    return expr[1:] if isinstance(expr, tree.Expression) and len(expr) > 2 and expr[0] == id else on_error(expr)


def error(description, at):

    (_, line, char), _, filename, text = at.location
    raise SyntaxError(description, (filename, line, char, text))


# assignment_target::
#
#   link(.*)
#   expression.link(.*)
#   expression !! expression
#   expression(',', assignment_target *)
#
def assignment_target(var):

    # Attempt to do iterable unpacking first.
    pack = binary_op(',', var, lambda _: None)

    if pack:

        # Allow one starred argument that is similar to `varargs`.
        star = -1

        for i, q in enumerate(pack):

            if isinstance(q, list) and len(q) == 3 and q[:2] == ['', '*']:

                star > -1 and error(const.ERR.MULTIPLE_VARARGS, q)
                i > 255   and error(const.ERR.TOO_MANY_ITEMS_BEFORE_STAR, q)

                star, pack[i] = i, q[2]

        return const.AT.UNPACK, pack, (len(pack), star)

    var, attr = binary_op('.',  var, lambda x: (x, None))
    var, item = binary_op('!!', var, lambda x: (x, None))

    if attr:

        isinstance(attr, tree.Link) or error(const.ERR.NONCONST_ATTR, attr)
        return const.AT.ATTR, attr, var

    if item:

        return const.AT.ITEM, item, var

    return (const.AT.NAME if isinstance(var, tree.Link) else const.AT.ASSERT), var, []


def argspec(args, definition):

    arguments   = []  # `c.co_varnames[:c.co_argc]`
    kwarguments = []  # `c.co_varnames[c.co_argc:c.co_argc + c.co_kwonlyargc]`

    defaults    = []  # `f.__defaults__`
    kwdefaults  = {}  # `f.__kwdefaults__`

    varargs     = []  # `[]` or `[c.co_varnames[c.co_argc + c.co_kwonlyargc]]`
    varkwargs   = []  # `[]` or `[c.co_varnames[c.co_argc + c.co_kwonlyargc + 1]]`

    if not isinstance(args, tree.Constant) or args.value is not None:

        for arg in (binary_op('', args, lambda x: [x]) if definition else args):

            # 1. `**: _` should be the last argument.
            varkwargs and error(const.ERR.ARG_AFTER_VARARGS, arg)

            kw, value = binary_op(':', arg, lambda x: (None, x))

            if kw is None:

                if definition:

                    # 2.1. `_: _` should only be followed by `_: _`
                    #      unless `*: _` was already encountered.
                    defaults and not varargs and error(const.ERR.NO_DEFAULT, value)

                # If there was a `*: _`, this is a keyword-only argument.
                # Unless, of course, this is a function call, in which case
                # it doesn't really matter.
                (kwarguments if varargs and definition else arguments).append(value)

            elif kw == '*':

                # 3.1. `*: _` cannot be followed by another `*: _`.
                varargs and error(const.ERR.MULTIPLE_VARARGS, kw)
                varargs.append(value)

            elif kw == '**':

                # 4.1. Just in case. Should not be triggered.
                varkwargs and error(const.ERR.MULTIPLE_VARKWARGS, kw)
                varkwargs.append(value)

            else:

                # If there was a `*: _`, guess what.
                # Or if this is not a definition. It's easier to tell
                # whether the argument is a keyword that way.
                if varargs or not definition:

                    # 5.1. `_: _` is a keyword argument, and its left side is a link.
                    isinstance(kw, tree.Link) or error(const.ERR.NONCONST_KEYWORD, kw)

                    kwarguments.append(kw)
                    kwdefaults[kw] = value

                else:

                    arguments.append(kw)
                    defaults.append(value)

    len(arguments) > 255 and error(const.ERR.TOO_MANY_ARGS, args)  # *sigh*
  # If this is a function call, not a definition:
  #        posargs,   _,           _,        kwargs,     varargs, varkwargs
    return arguments, kwarguments, defaults, kwdefaults, varargs, varkwargs
