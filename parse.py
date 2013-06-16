from re          import compile
from ast         import literal_eval
from functools   import reduce
from collections import Iterator, deque, namedtuple

Location = namedtuple('Location', 'start, end, filename, first_line')


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

# In all comments below, `R` and `Q` are infix links, while lowercase letters
# are arbitrary expressions.
has_priority = (lambda f: lambda a, b: f(a)[0] > f(b)[1])(lambda m, g={
    # `a R b Q c` <=> `a R (b Q c)` if left binding strength of `Q`
    # is higher than right binding strength of `R`.
    '.':     ( 0,   0),   # getattr
    '!.':    ( 0,   0),   # call with no arguments, then getattr
    '!':     ( 0,  -1),   # call with no arguments
    ':':     ( 0,  -1),   # keyword argument
    '':      (-2,  -2),   # call with an argument
    '!!':    (-3,  -3),   # container subscription (i.e. `a[b]`)
    '**':    (-3,  -4),   # exponentiation
    '*':     (-5,  -5),   # multiplication
    '/':     (-5,  -5),   # fp division
    '//':    (-5,  -5),   # int division
    '%':     (-5,  -5),   # modulus
    '+':     (-6,  -6),   # addition
    '-':     (-6,  -6),   # subtraction
    # -7 is the default value for everything not on this list.
    '<':     (-8,  -8),   # less than
    '<=':    (-8,  -8),   # ^ or equal
    '>':     (-8,  -8),   # greater than
    '>=':    (-8,  -8),   # ^ or equal
    '==':    (-8,  -8),   # equal
    '!=':    (-8,  -8),   # not ^
    'is':    (-8,  -8),   # occupies the same memory location as
    'in':    (-8,  -8),   # is one of the elements of
    '<<':    (-10, -10),  # *  2 **
    '>>':    (-10, -10),  # // 2 **
    '&':     (-11, -11),  # bitwise and
    '^':     (-12, -12),  # bitwise xor
    '|':     (-13, -13),  # bitwise or
    'and':   (-14, -14),  # B if A else A
    'or':    (-15, -15),  # A if A else B
    '$':     (-15, -16),  # call with one argument and no f-ing parentheses
    '->':    ( 1,  -18),  # a function
    ',':     (-17, -17),  # a tuple
    '=':     (-17, -18),  # assignment
    '!!=':   (-17, -18),  # in-place versions of some of the other functions
    '+=':    (-17, -18),
    '-=':    (-17, -18),
    '*=':    (-17, -18),
    '**=':   (-17, -18),
    '/=':    (-17, -18),
    '//=':   (-17, -18),
    '%=':    (-17, -18),
    '&=':    (-17, -18),
    '^=':    (-17, -18),
    '|=':    (-17, -18),
    '<<=':   (-17, -18),
    '>>=':   (-17, -18),
    'where': (-17, -18),  # with some stuff that is not visible outside of that expression
    'if':    (-19, -20),  # binary conditional
    'else':  (-20, -21),  # ternary conditional (always follows an `a if b` expression)
    '\n':    (-23, -23),  # do A then B
}.get: g(m, (-7, -7)))  # Default


# If `unassoc(R)`: `a R b R c` <=> `Expression [ Link R, Link a, Link b, Link c]`
# Otherwise:       `a R b R c` <=> `Expression [ Link R, Expression [...], Link c]`
# (This doesn't apply to right-fixed links.)
unassoc = {',', '..', '::', '', '\n'}.__contains__

# These operators have no right-hand statement part in any case.
unary = {'!'}.__contains__


# infixl :: (State, StructMixIn, Link, StructMixIn) -> StructMixIn
#
# Handle an infix expression given its all three parts.
#
# If that particular expression has no right-hand statement part,
# `rhs` will be pushed to the object queue.
#
def infixl(stream, lhs, op, rhs):

    break_   = False
    postfixl = lambda: (lhs if op in '\n ' else infixl_insert_rhs(lhs, op, None))

    while rhs == '\n' and not unary(op):

        break_, rhs = rhs, next(stream)

    if isinstance(rhs, Internal) or unary(op):  # `(a R)`

        stream.appendleft(rhs)
        return postfixl()

    if break_ and op == '' and rhs.indented:

        # a
        #   b         <=>  a b (c d)
        #   c d
        return reduce(
            lambda lhs, rhs: infixl_insert_rhs(lhs, op, rhs),
            rhs[1:] if isinstance(rhs, Expression) and rhs[0] == '\n' else [rhs], lhs
        )

    if break_ and op != '\n' and not rhs.indented:  # `a R`

        return infixl(stream, postfixl(), break_, rhs)

    if not rhs.closed and rhs.infix and (op == '' or has_priority(op, rhs)):

        # `a R Q b` <=> `(a R) Q b` if R is prioritized over Q or R is empty.
        return infixl(stream, postfixl(), rhs, next(stream))

    return infixl_insert_rhs(lhs, op, rhs)


# infixl_insert_rhs :: (StructMixIn, Link, StructMixIn) -> StructMixIn
#
# Recursively descends into `root` if infix precedence rules allow it to,
# otherwise simply creates and returns a new infix expression AST node.
#
def infixl_insert_rhs(root, op, rhs):

    if isinstance(root, Expression) and not root.closed:

        if has_priority(op, root[0]):

            # `a R b Q c` <=> `a R (b Q c)` if Q is prioritized over R
            root.append(infixl_insert_rhs(root.pop(), op, rhs))
            return root

        elif op == root[0] and unassoc(op) and rhs is not None:

            root.append(rhs)  # `a R b R c` <=> `R a b c`
            return root

    # `R`         <=> `Link R`
    # `R rhs`     <=> `Expression [ Link '', Link R, Link rhs ]`
    # `lhs R`     <=> `Expression [ Link R, Link lhs ]`
    # `lhs R rhs` <=> `Expression [ Link R, Link lhs, Link rhs ]`
    e = Expression([op, root] if rhs is None else [op, root, rhs])
    e.closed = rhs is None
    e.location = Location(
        root.location.start,
        e[-(not e.closed)].location.end,
        root.location.filename,
        root.location.first_line
    )
    return e


def indent(stream, token):

    indent = len(token.group())

    if indent > stream.indent[-1]:

        stream.indent.append(indent)
        block = do(stream, token, {''}, preserve_close_state=True)
        block.indented = True
        return block

    while indent != stream.indent[-1]:

        stream.indent.pop() < 0 and stream.error('no matching indentation level', token.start())
        stream.appendleft(Link('\n', True).at(stream, token.end()))
        stream.appendleft(Internal('').at(stream, token.end()))


def whitespace(stream, token): pass


def number(stream, token):

    return Constant(literal_eval(token.group()))


def string(stream, token):

    g = token.group(2) * (4 - len(token.group(2)))
    q = ''.join(sorted(set(token.group(1))))
    return Constant(literal_eval(''.join([q, g, token.group(3), g])))


def link(stream, token, infixn={'if', 'else', 'or', 'and', 'in', 'is', 'where'}):

    infix = token.group(2) or token.group(3) or token.group(4)
    return Link(infix or token.group(), infix or (token.group() in infixn))


def do(stream, token, ends={')'}, preserve_close_state=False):

    object   = Constant(None).at(stream, token.end())
    can_join = False

    for item in stream:

        if isinstance(item, Internal):

            item.value in ends or stream.error(
              'unexpected block delimiter' if item.value else
              'unexpected EOF'             if stream.offset >= len(stream.buffer) else
              'unexpected dedent', item.location.start[0]
            )

            break

        elif can_join:

            # Two objects in a row should be joined with an empty infix link.
            object = infixl(stream, object, Link('', True).after(object), item)

        # Ignore line feeds directly following an opening parentheses.
        elif item != '\n':

            object, can_join = item, True

    object.closed |= not preserve_close_state
    return object


def end(stream, token):

    return Internal(token.group())


def string_err(stream, token):

    stream.error('unexpected EOF while reading a string literal', token.start())


def error(stream, token):

    stream.error('invalid input', token.start())


def R(func, expr):

    return func, compile(expr).match


class it (Iterator, deque):

    tokens = [R(indent, r' *')], [
        R(whitespace, r'[^\S\n]+|\s*#.*')
      , R(number,     r'(?i)[+-]?(?:0b[0-1]+|0o[0-7]+|0x[0-9a-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?j?)')
      , R(string,     r'(?s)([br]*)(\'\'\'|"""|"|\')((?:\\?.)*?)\2')
      , R(link,       r"(\w+'*|\*+(?=:)|([!$%&*+\--/:<-@\\^|~;]+|,+))|\s*(\n)|`(\w+'*)`")
      , R(do,         r'\(')
      , R(end,        r'\)|$')
      , R(string_err, r'''['"]''')
      , R(error,      r'.')
    ]

    def __new__(cls, data, filename='<string>'):

        self = super(it, cls).__new__(cls)
        self.filename = filename
        self.buffer   = data
        self.offset   = 0
        self.indent   = deque([-1])
        self.nextset  = self.tokens[0]
        return next(self)

    def __next__(self):

        while not self:

            f, match = next((f, match)
                for f, re in self.nextset
                for match in [re(self.buffer, self.offset)] if match
            )
            self.offset  = match.end()
            self.nextset = self.tokens[not match.group().endswith('\n')]
            q = f(self, match)

            if q is not None:

                return q.at(self, match.start())

        return self.popleft()

    # position :: int -> (int, int, int)
    #
    # Given a character offset, get an (offset, lineno, charno) triple.
    #
    def position(self, offset):

        return (offset,
            1      + self.buffer.count('\n', 0, offset),
            offset - self.buffer.rfind('\n', 0, offset))

    # error :: (str, int) -> _|_
    #
    # Raise a `SyntaxError` at a given offset.
    #
    def error(self, description, at):

        _, lineno, charno = self.position(at)
        raise SyntaxError(description, (self.filename, lineno, charno, self.line(at)))

    # line :: int -> str
    #
    # Get a line which contains the character at a given offset.
    #
    def line(self, offset):

        return self.buffer[
            self.buffer.rfind('\n', 0, offset) + 1 or None:
            self.buffer. find('\n',    offset) + 1 or None
        ]

fd = lambda fd, filename='<stream>': it(fd.read(), getattr(fd, 'name', filename))
