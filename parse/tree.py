import itertools
import collections


class Expression (list):

    indented = False
    closed   = False
    """
    def __repr__(self):

        sub = list(map(repr, self))
        sub[0] = '`{}`'.format(*sub) if sub[0].operator else sub[0]

        return (
            ' '.join(sub[::-1])  if len(self) < 3          else
            ' '.join(sub[1:])    if not self[0]            else
            sub[0].join(sub[1:]) if self[0] in {'.', '\n'} else
            ' {} '.format(*sub).join(sub[1:])
        )
    """

class Link (str):

    @property
    def operator(self):

        return not self.isidentifier() \
            or self in {'if', 'else', 'unless', 'or', 'and'}
    """
    def __repr__(self):

        return self
    """

class Internal:

    def __repr__(self):

        return '#INTERNAL {}'.format(id(self))


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
