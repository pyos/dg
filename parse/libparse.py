import re
import collections

STATE_AT_LINE_START = 1  # `(?m)^`
STATE_AT_FILE_START = 2  # `^`
STATE_AT_FILE_END   = 4  # `$`
STATE_CUSTOM        = 8  # lowest unused state bit

Token    = collections.namedtuple('Token',    'regex, state, func')
Location = collections.namedtuple('Location', 'start, end, filename')


class Parser (collections.Iterator):

    def __init__(self, input, filename='<string>'):

        super().__init__()

        self.state  = STATE_AT_FILE_START | STATE_AT_LINE_START
        self.buffer = input
        self.offset = 0
        self.pstack = collections.deque()
        self.repeat = collections.deque()
        self.filename = filename

    def __new__(cls, input, filename='<string>'):

        obj = super(type, cls).__new__(cls, input, filename)
        obj.__init__(input, filename)
        return next(obj)

    @classmethod
    def make(cls):

        class _(cls): tokens = []
        return _

    @classmethod
    def token(cls, func):

        state = func.__annotations__.get(func.__code__.co_varnames[0], 0)
        regex = func.__annotations__.get(func.__code__.co_varnames[1], r'.')
        cls.tokens.append(Token(re.compile(regex, re.DOTALL).match, state, func))
        return func

    def position(self, offset):

        return (
            offset,
            1 + self.buffer[:offset].count('\n'),  # lineno
            offset - self.buffer.rfind('\n', 0, offset)  # charno
        )

    def error(self, description, after=False):

        offset, lineno, charno = self.next_token_at if after else self.last_token_at
        line = self.buffer[self.buffer.rfind('\n', 0, offset) + 1:]
        raise SyntaxError(description, (self.filename, lineno, charno, line))

    def located(self, q):

        if hasattr(q, '__dict__'):

            q.reparse_location = Location(
                self.last_token_at,
                self.next_token_at,
                self.filename
            )

        return q

    def __next__(self):

        while not self.repeat:

            self.state |= self.offset >= len(self.buffer) and STATE_AT_FILE_END

            matches = (
                (
                    m.func,
                    m.state & self.state == m.state and m.regex(self.buffer, self.offset)
                ) for m in self.tokens
            )

            f, match = next(m for m in matches if m[1])
            self.pstack.append(self.offset)
            self.state  &= ~STATE_AT_FILE_START
            self.state  &= ~STATE_AT_LINE_START
            self.state  |= match.group().endswith('\n') and STATE_AT_LINE_START
            self.offset  = match.end()
            self.repeat.extend(map(self.located, f(self, match)))
            self.pstack.pop()

        return self.repeat.popleft()

    next_token_at = property(lambda self: self.position(self.offset))
    last_token_at = property(lambda self: self.position(self.pstack[-1]))

