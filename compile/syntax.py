import itertools

from .. import parse

error = parse.error


# binary_op :: (Link, object, object -> [object]) -> [object]
#
# Return the arguments of a call `expr` to the varary operator `id`.
#
def binary_op(id, expr, on_error):

    return expr[1:] if isinstance(expr, parse.Expression) and len(expr) > 2 and expr[0] == id else on_error(expr)


def argspec(args, definition):

    arguments   = []  # `c.co_varnames[:c.co_argc]`
    kwarguments = []  # `c.co_varnames[c.co_argc:c.co_argc + c.co_kwonlyargc]`

    defaults    = []  # `f.__defaults__`
    kwdefaults  = {}  # `f.__kwdefaults__`

    varargs     = []  # `[]` or `[c.co_varnames[c.co_argc + c.co_kwonlyargc]]`
    varkwargs   = []  # `[]` or `[c.co_varnames[c.co_argc + c.co_kwonlyargc + 1]]`

    # Python only supports local variables as arguments. We'll have to improvise.
    patterns = {}
    varnames = set()
    patternc = itertools.count()

    if definition:

        def patternize(item):

            if isinstance(item, parse.Link) and item not in varnames:

                varnames.add(item)
                return item

            name = 'pattern-' + str(next(patternc))
            patterns[name] = item
            return name

    else: patternize = lambda x: x

    # `Constant(None)` <=> `()` <=> "no arguments".
    if not isinstance(args, parse.Constant) or args.value is not None:

        for arg in (binary_op('', args, lambda x: [x]) if definition else args):

            # 1. `**: _` should be the last argument in a function definition.
            definition and varkwargs and error('**double-starred argument is always the last one', arg)

            kw, value = binary_op(':', arg, lambda x: (None, x))

            if kw is None:

                if definition:

                    # 2.1. `_: _` should only be followed by `_: _`
                    #      unless `*: _` was already encountered.
                    defaults and not varargs and error('this argument should have a default value', value)

                # If there was a `*: _`, this is a keyword-only argument.
                # Unless, of course, this is a function call, in which case
                # it doesn't really matter.
                (kwarguments if varargs and definition else arguments).append(patternize(value))

            elif kw == '*':

                # 3.1. `*: _` cannot be followed by another `*: _`.
                varargs and error('can only have one *starred argument', kw)
                varargs.append(patternize(value))

            elif kw == '**':

                # 4.1. Just in case. Should not be triggered.
                varkwargs and error('can only have one **double-starred argument', kw)
                varkwargs.append(patternize(value))

            else:

                # If there was a `*: _`, guess what.
                # Or if this is not a definition. It's easier to tell
                # whether the argument is a keyword that way.
                if varargs or not definition:

                    # 5.1. `_: _` is a keyword argument, and its left side is a link.
                    isinstance(kw, parse.Link) or error('keywords cannot be pattern-matched', kw)

                    kw = patternize(kw)
                    kwarguments.append(kw)
                    kwdefaults[kw] = value

                else:

                    arguments.append(patternize(kw))
                    defaults.append(value)

    len(arguments) > 255 and error('CPython cannot handle that many arguments', args)  # *sigh*
  # If this is a function call, not a definition:
  #        posargs,   _,           _,        kwargs,     varargs, varkwargs, _
    return arguments, kwarguments, defaults, kwdefaults, varargs, varkwargs, patterns
