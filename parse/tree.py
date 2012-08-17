import itertools


class StructMixIn:

    indented = False
    closed   = False


class Expression (list, StructMixIn):

    pass


class Link (str, StructMixIn):

    @property
    def infix(self):

        return not self.isidentifier() or self in {'if', 'else', 'unless', 'or', 'and'}


class Constant (StructMixIn):

    def __init__(self, value):

        super().__init__()
        self.value = value


class Internal (StructMixIn):

    pass


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
