import itertools
import collections


class Expression (list):

    indented = False
    closed   = False


class Link (str):

    @property
    def infix(self):

        return not self.isidentifier() or self in {'if', 'else', 'unless', 'or', 'and'}


class Internal: pass
class Constant:

    # That works because built-in constant types override __new__.
    __new__ = lambda cls, x: next(c for c in cls.__subclasses__() if issubclass(c, type(x)))(x)

class String  (str,     Constant): pass
class Bytes   (bytes,   Constant): pass
class Integer (int,     Constant): pass
class Float   (float,   Constant): pass
class Complex (complex, Constant): pass
    


def format(code):

    if isinstance(code, Expression):

        return type(code).__name__ + '\n  ' + '\n'.join(map(format, code)).replace('\n', '\n  ')

    if isinstance(code, Link):

        return 'Link ' + str.__repr__(code)

    return repr(code)


def match(code, pattern, into):

    if isinstance(pattern, Link) and pattern == '_':

        # `_` matches anything.
        into.append(code)
        return True

    if isinstance(code, Expression):

        return (
            isinstance(pattern, type(code)) and
            len(code) == len(pattern)       and
            all(map(match, code, pattern, itertools.repeat(into)))
        )

    return type(code) == type(pattern) and code == pattern


def matchA(code, pattern):

    into = []
    return into if match(code, pattern, into) else []


def matchQ(code, pattern):

    return match(code, pattern, [])


def matchR(code, pattern, f):

    into = []

    while match(code, pattern, into):

        code = f(code, into)

    return into + [code]
