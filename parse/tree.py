import collections

Location = collections.namedtuple('Location', 'start, end, filename, first_line')


class StructMixIn:

    infix       = False
    closed      = False
    indented    = False

    def after(self, other):

        self.location = Location(
            other.location.end,
            other.location.end,
            other.location.filename,
            other.location.first_line
        )
        return self

    def at(self, stream, start):

        self.location = Location(
            stream.position(start),
            stream.position(stream.offset),
            stream.filename,
            stream.line(start)
        )
        return self


class Expression (list, StructMixIn):

    def __repr__(self):

        return ('({})' if self.closed else '{}').format(
            ' '.join(map(repr, self[1:])) if self[0] == '' else
            '{1}{0}{2}'  .format(*self) if len(self) == 3 and self[0] == '.' else
            '{1} {0} {2}'.format(*self) if len(self) == 3 else
            '{1} {0}'    .format(*self) if len(self) == 2 else
            '({}) {}'.format(self[0], ' '.join(map(repr, self[1:])))
        )


class Link (str, StructMixIn):

    def __new__(cls, data, infix=False):

        obj = str.__new__(cls, data)
        obj.infix = bool(infix)
        return obj

    def __repr__(self):

        return self


class Constant (StructMixIn):

    def __init__(self, value):

        super().__init__()
        self.value = value

    def __repr__(self):

        return repr(self.value)


class Internal (Constant):

    pass
