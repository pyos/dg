import re
import collections

from . import tree

STATE_AT_LINE_START = 1  # `(?m)^`
STATE_AT_FILE_START = 2  # `^`
STATE_AT_FILE_END   = 4  # `$`


class Parser (collections.Iterator):

    INFIX_RIGHT_FIXITY = {
        '**', ':', '$', '->',
        '=', '!!=', '+=', '-=', '*=', '**=', '/=', '//=', '%=', '&=', '^=', '|=', '<<=', '>>=',
        'if', 'unless', 'else', 'where'
    }

    INFIX_PRECEDENCE = lambda self, i, q={
      # Scope resolution
        '.':   0,
       ':.':   0,
      # Keyword arguments
        ':':  -1,
      # Function application
         '':  -2,
      # Container subscription
       '!!':  -3,
      # Math
       '**':  -4,
        '*':  -5,
        '/':  -5,
       '//':  -5,
        '%':  -5,
        '+':  -6,
        '-':  -6,
      # Comparison
        '<':  -8,
       '<=':  -8,
       '>=':  -8,
        '>':  -8,
       '==':  -8,
       '!=':  -8,
       'is':  -8,
       'in':  -8,
      # Binary operations
       '<<': -10,
       '>>': -10,
        '&': -11,
        '^': -12,
        '|': -13,
      # Logic
       '&&': -14,
      'and': -14,
       '||': -15,
       'or': -15,
      # Low-priority binding
        '$': -16,
      # Function definition
       '->': -17,
      # Sequential evaluation
        ',': -18,
      # Local binding
    'where': -19,
      # Assignment
        '=': -19,
      '!!=': -19,
       '+=': -19,
       '-=': -19,
       '*=': -19,
      '**=': -19,
       '/=': -19,
      '//=': -19,
       '%=': -19,
       '&=': -19,
       '^=': -19,
       '|=': -19,
      '<<=': -19,
      '>>=': -19,
      # Conditionals
       'if': -20,
   'unless': -20,
     'else': -21,
      # Chaining
       '\n': -100500,
    }.get: q(i, -7)  # Default

    tokens = []

    # Whether an infix link's priority is higher than the other one's.
    #
    # :param in_relation_to: link to the left.
    #
    def has_priority(self, link, in_relation_to):

        if link == '->':

            # `a R b -> c` should always parse as `a R (b -> c)`.
            #
            # Note that this means that for `a R b -> c Q d` to parse
            # as `a R (b -> (c Q d))` this method should return True for both
            # (Q, R) and (Q, ->). Otherwise, the output is `a R (b -> c) Q d`.
            # That's not of concern when doing stuff like `f = x -> print 1`
            # 'cause `=` has the lowest possible priority.
            #
            # What               How                 Why
            # -----------------------------------------------------------
            # a b -> c d         a (b -> c) d        (, ) is False
            # a = b -> c = d     a = (b -> c) = d    (=, ->) is False
            # a $ b -> c $ d     a $ (b -> (c $ d))  everything's True
            # a b -> c.d         a (b -> (c.d))      also True
            #
            return True

        p1 = self.INFIX_PRECEDENCE(link)
        p2 = self.INFIX_PRECEDENCE(in_relation_to)
        return p1 + (link in self.INFIX_RIGHT_FIXITY) > p2

    @classmethod
    def token(cls, regex, state=0):

        def g(f):

            cls.tokens.append((re.compile(regex, re.DOTALL).match, state, f))
            return f

        return g

    @classmethod
    def parse(cls, input, filename='<string>'):

        self = cls()
        self.state  = STATE_AT_FILE_START | STATE_AT_LINE_START
        self.buffer = input
        self.stuff  = None
        self.offset = 0
        self.pstack = collections.deque()
        self.repeat = collections.deque()
        self.indent = collections.deque([-1])
        self.filename = filename
        q = next(self)
        self.state & STATE_AT_FILE_END or self.error('junk after the end of input', after=True)
        return q

    def position(self, offset):

        return (
            offset,
            1 + self.buffer[:offset].count('\n'),  # lineno
            offset - self.buffer.rfind('\n', 0, offset)  # charno
        )

    def error(self, description, after=False):

        offset, lineno, charno = self.next_token_at if after else self.last_token_at
        raise SyntaxError(description, (self.filename, lineno, charno, self.line(offset)))

    def __next__(self):

        while not self.repeat:

            self.state |= self.offset >= len(self.buffer) and STATE_AT_FILE_END

            matches = (
                (func, self.state & state == state and regex(self.buffer, self.offset))
                for regex, state, func in self.tokens
            )

            f, match = next(m for m in matches if m[1])
            self.pstack.append(self.offset)
            self.state &= ~STATE_AT_FILE_START
            self.state &= ~STATE_AT_LINE_START
            self.state |= match.group().endswith('\n') and STATE_AT_LINE_START
            self.offset = match.end()
            self.repeat.extend(q.at(self) for q in f(self, match))
            self.pstack.pop()

        return self.repeat.popleft()

    line = lambda self, offset: self.buffer[self.buffer.rfind('\n', 0, offset) + 1:self.buffer.find('\n', offset) + 1 or None]
    next_token_at = property(lambda self: self.position(self.offset))
    last_token_at = property(lambda self: self.position(self.pstack[-1]))
