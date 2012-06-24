import itertools

import dg


def format(code):

    if isinstance(code, (dg.Closure, dg.Expression)):

        return type(code).__name__ + '\n  ' + '\n'.join(map(format, code)).replace('\n', '\n  ')

    if isinstance(code, dg.Link):

        return 'Link ' + str.__repr__(code)

    return repr(code)


def match(code, pattern, into):

    if isinstance(pattern, dg.Link) and pattern == '_':

        # `_` matches anything.
        into.append(code)
        return True

    if isinstance(code, (dg.Closure, dg.Expression)):

        return (
            isinstance(pattern, type(code)) and
            len(code) == len(pattern)       and
            all(map(match, code, pattern, itertools.repeat(into)))
        )

    return type(code) == type(pattern) and code == pattern


def matchA(code, pattern):

    into = []
    ok   = match(code, pattern, into)
    return into if ok else []


def matchQ(code, pattern):

    return match(code, pattern, [])


def matchR(code, pattern, f):

    into = []

    while match(code, pattern, into):

        code = f(code, into)

    return into + [code]

