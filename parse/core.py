import re
import collections

from . import tree

STATE_AT_LINE_START = 1  # `(?m)^`
STATE_AT_FILE_START = 2  # `^`
STATE_AT_FILE_END   = 4  # `$`
STATE_CUSTOM        = 8  # lowest unused state bit

Location = collections.namedtuple('Location', 'start, end, filename')


class Parser (collections.Iterator):

    OPERATOR_RIGHT_FIXITY = {'**', ':', '$', '->', '=', 'if', 'unless', 'else'}
    OPERATOR_PRECEDENCE = lambda self, i, q={
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
       '==':  -9,
       '!=':  -9,
       'is':  -9,
       'in':  -9,
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
      # Assignment
        '=': -19,
      # Conditionals
       'if': -20,
   'unless': -20,
     'else': -21,
      # Chaining
       '\n': -100500,
    }.get: q(i, -7)  # Default

    tokens = []

    @classmethod
    def token(cls, regex=r'.', state=0):

        def g(f):

            cls.tokens.append((re.compile(regex, re.DOTALL).match, state, f))
            return f

        return g

    # Whether an operator's priority is higher than the other one's.
    #
    # :param in_relation_to: operator to the left.
    #
    def has_priority(self, operator, in_relation_to):

        if operator == '->':

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
            # a $ b -> c $ d     a $ (b $ (c $ d))   everything's True
            # a b -> c.d         a (b -> (c.d))      also True
            #
            return True

        p1 = self.OPERATOR_PRECEDENCE(operator)
        p2 = self.OPERATOR_PRECEDENCE(in_relation_to)
        return p1 + (operator in self.OPERATOR_RIGHT_FIXITY) > p2

    # A compiler function for `interactive`, similar to `code.compile_command`.
    #
    # :param code: what to compile.
    #
    # :return: None if `code` is incomplete, `parse(code)` otherwise.
    #
    def compile_command(self, code):

        try:

            res = self.parse(code, '<stdin>')

        except SyntaxError as e:

            if e.args[0] in {'mismatched parentheses', 'mismatched quote'}:

                # The code is incomplete by definition if there are
                # unmatched parentheses or quotes in it.
                return None

            # Other errors are irrepairable.
            raise

        # Search for incomplete operator expressions.
        expr = res
        while not getattr(expr, 'closed', True) and len(expr) > 2: expr = expr[-1]

        return None if (
            not code.endswith('\n')
            and (
                not getattr(expr, 'closed', True)
                or code.rsplit('\n', 1)[-1].startswith(' ')
            )
        ) else res

    def parse(self, input, filename='<string>'):

        self.state  = STATE_AT_FILE_START | STATE_AT_LINE_START
        self.buffer = input
        self.stuff  = None
        self.offset = 0
        self.pstack = collections.deque()
        self.repeat = collections.deque()
        self.indent = collections.deque([-1])
        self.filename = filename
        return next(self)

    def position(self, offset):

        return (
            offset,
            1 + self.buffer[:offset].count('\n'),  # lineno
            offset - self.buffer.rfind('\n', 0, offset)  # charno
        )

    def error(self, description, after=False):

        offset, lineno, charno = self.next_token_at if after else self.last_token_at
        line = self.buffer[self.buffer.rfind('\n', 0, offset) + 1:self.buffer.find('\n', offset)]
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
                (func, self.state & state == state and regex(self.buffer, self.offset))
                for regex, state, func in self.tokens
            )

            f, match = next(m for m in matches if m[1])
            self.pstack.append(self.offset)
            self.state &= ~STATE_AT_FILE_START
            self.state &= ~STATE_AT_LINE_START
            self.state |= match.group().endswith('\n') and STATE_AT_LINE_START
            self.offset = match.end()
            self.repeat.extend(map(self.located, f(self, match)))
            self.pstack.pop()

        return self.repeat.popleft()

    next_token_at = property(lambda self: self.position(self.offset))
    last_token_at = property(lambda self: self.position(self.pstack[-1]))
