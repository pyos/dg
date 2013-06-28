from re          import compile
from ast         import literal_eval
from functools   import reduce, partial
from collections import Iterator, deque, namedtuple

__all__ = ['Node', 'Expression', 'Link', 'Constant', 'Location', 'error', 'it', 'fd']

Location = namedtuple('Location', 'start, end, filename, first_line')


class Node:

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

    def at(self, start, stream):

        self.location = Location(
            start.start,
            (stream.offset, stream.lineno, stream.charno),
            start.filename,
            start.first_line
        )
        return self


class Expression (list, Node):

    def __repr__(self):

        return ('({})' if self.closed else '{}').format(
            ' '.join(map(repr, self[1:])) if self[0] == '' else
            '{1}{0}{2}'  .format(*self) if len(self) == 3 and self[0] == '.' else
            '{1} {0} {2}'.format(*self) if len(self) == 3 else
            '{1} {0}'    .format(*self) if len(self) == 2 else
            '({}) {}'.format(self[0], ' '.join(map(repr, self[1:])))
        )


class Link (str, Node):

    def __new__(cls, data, infix=False):

        obj = str.__new__(cls, data)
        obj.infix = bool(infix)
        return obj

    def __repr__(self):

        return self


class Constant (Node):

    def __init__(self, value):

        super().__init__()
        self.value = value

    def __repr__(self):

        return repr(self.value)


class Internal (Constant):

    pass


def error(description, at):
    (_, lineno, charno), _, filename, line = at.location if isinstance(at, Node) else at
    raise SyntaxError(description, (filename, lineno, charno, line))


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
    'for':   (-18, -19),  # evaluate stuff for each item in an iterable
    'while': (-18, -19),  # evaluate stuff until condition becomes false
    '=>':    (-22, -22),  # ???????
    '\n':    (-23, -23),  # do A then B
}.get: g(m, (-7, -7)))  # Default


# If `unassoc(R)` is true, `Expression`s starting with `R` are allowed
# to contain any number of arguments rather than only two.
unassoc = {',', '..', '::', '', '\n'}.__contains__

# These operators have no right-hand statement part in any case.
unary = {'!'}.__contains__


def infix(self, lhs, op, rhs):
    br = False

    while rhs == '\n' and not unary(op):
        # There are some special cases for indented RHS,
        # so we'll have to ignore the line breaks for now.
        br, rhs = rhs, next(self)

    if op == '':
        if isinstance(rhs, Internal):
            # `(a\n)`.
            self.appendleft(rhs)
            return lhs

        if br and rhs.indented:
            # a b
            #   c         <=>  a b c (d e)
            #   d e
            args = rhs[1:] if isinstance(rhs, Expression) and rhs[0] == '\n' else [rhs]
            return reduce(partial(infixin, op), args, lhs)

        if br:
            # `a\n`.
            return infixin(br, lhs, rhs)

        if rhs.infix and not rhs.closed:
            # `a R b`. There's no empty operator at all.
            return infix(self, lhs, rhs, next(self))

    else:
        if isinstance(rhs, Internal) or unary(op):
            # `(a R)`
            return infixin(op, lhs, self.appendleft(rhs))

        if rhs.infix and not rhs.closed and has_priority(op, rhs):
            # `a R Q b` <=> `(a R) Q b` if R has priority over Q.
            return infix(self, infixin(op, lhs), rhs, next(self))

        if br and not rhs.indented:
            # `a R\n`.
            return infixin(br, infixin(op, lhs), rhs)

    return infixin(op, lhs, rhs)


def infixin(op, lhs, rhs=None):

    if isinstance(lhs, Expression) and not lhs.closed:

        if has_priority(op, lhs[0]):
            # `a R b Q c` <=> `a R (b Q c)` if Q has priority over R
            lhs.append(infixin(op, lhs.pop(), rhs))
            return lhs

        elif op == lhs[0] and unassoc(op) and rhs is not None:
            # `a R b R c` <=> `R a b c`
            lhs.append(rhs)
            return lhs

    # `R`         <=> `Link R`
    # `R rhs`     <=> `Expression [ Link '', Link R, Link rhs ]`
    # `lhs R`     <=> `Expression [ Link R, Link lhs ]`
    # `lhs R rhs` <=> `Expression [ Link R, Link lhs, Link rhs ]`
    e = Expression([op, lhs] if rhs is None else [op, lhs, rhs])
    e.closed = rhs is None
    e.location = Location(
        lhs.location.start,
        e[-(not e.closed)].location.end,
        lhs.location.filename,
        lhs.location.first_line
    )
    return e


def indent(stream, token, pos):

    indent = len(token.group())

    if indent > stream.indent[-1]:

        stream.indent.append(indent)
        block = do(stream, token, pos, lambda x: isinstance(x, Internal) and not x.value, preserve_close_state=True)
        block.indented = True
        return stream.appendleft(block)  # it already has a location.

    while indent != stream.indent[-1]:

        stream.indent.pop() < 0 and error('no matching indentation level', pos)
        stream.appendleft(Link('\n', True).at(pos, stream))
        stream.appendleft(Internal('').at(pos, stream))


def string(stream, token, pos):
    g = token.group(2) * (4 - len(token.group(2)))
    q = ''.join(sorted(set(token.group(1))))
    return Constant(literal_eval(''.join([q, g, token.group(3), g])))


def link(stream, token, pos, infixn={'or', 'and', 'in', 'is', 'where'}):
    inf  = token.group(2) or token.group(3) or token.group(4)
    name = Link(inf or token.group(), inf or (token.group() in infixn)).at(pos, stream)

    if name in {'for', 'while'}:

        return infix(stream, do(stream, token, pos, end=lambda x: x == '=>'), name, next(stream))

    if name in {'if'}:

        block = do(stream, token, pos, end=lambda x: ((x == '\n' or isinstance(x, Internal)) and (stream.appendleft(x) or True)))

        if not isinstance(block, Constant) or block.value is not None:

            return infix(stream, name, Link('', True).after(name), block)

    return name


def do(stream, token, pos, end=lambda x: isinstance(x, Internal) and x.value == ')', preserve_close_state=False):
    object   = Constant(None).at(pos, stream)
    can_join = False

    for item in stream:

        if end(item): break

        if isinstance(item, Internal):

            error('unexpected block end', item) if not token.group().strip() else \
            error('unexpected EOF in a block', pos) if not item.value else \
            error('unmatched block start', pos)

        elif can_join:

            # Two objects in a row should be joined with an empty infix link.
            object = infix(stream, object, Link('', True).after(object), item)

        # Ignore line feeds directly following an opening parentheses.
        elif item != '\n':

            object, can_join = item, True

    object.closed |= not preserve_close_state
    return object


def space (stream, token, pos): pass
def number(stream, token, pos): return Constant(literal_eval(token.group()))
def end   (stream, token, pos): return Internal(token.group())
def errors(stream, token, pos): error('unexpected EOF while reading a string literal', pos)
def errorh(stream, token, pos): error('invalid input', pos)


def R(func, expr): return func, compile(expr).match


class it (Iterator, deque):

    tokens = [R(indent, r' *')], [
        R(space,  r'[^\S\n]+|\s*#.*')
      , R(number, r'(?i)[+-]?(?:0b[0-1]+|0o[0-7]+|0x[0-9a-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?j?)')
      , R(string, r'(?s)([br]*)(\'\'\'|"""|"|\')((?:\\?.)*?)\2')
      , R(link,   r"(\w+'*|\*+(?=:)|([!$%&*+\--/:<-@\\^|~;]+|,+))|\s*(\n)|`(\w+'*)`")
      , R(do,     r'\(')
      , R(end,    r'\)|$')
      , R(errors, r'''['"]''')
      , R(errorh, r'.')
    ]

    def __new__(cls, data, filename='<string>'):

        self = super(it, cls).__new__(cls)
        self.filename = filename
        self.buffer   = data
        self.lines    = deque(data.split('\n'))
        self.indent   = deque([-1])
        self.offset   = 0
        self.lineno   = 1
        self.charno   = 1
        self.nextset  = self.tokens[0]
        return next(self)

    def __next__(self):

        while not self:

            pos = Location((self.offset, self.lineno, self.charno), None, self.filename, self.lines[0])
            f, match = next((f, match)
                for f, re in self.nextset
                for match in [re(self.buffer, self.offset)] if match
            )

            if '\n' in match.group():
                for _ in range(match.group().count('\n')): self.lines.popleft()
                self.lineno +=  match.group().count('\n')
                self.charno  = -match.group().rfind('\n')

            self.offset  = match.end()
            self.charno += self.offset - match.start()
            self.nextset = self.tokens[not match.group().endswith('\n')]
            q = f(self, match, pos)

            if q is not None:

                return q.at(pos, self)

        return self.popleft()

fd = lambda fd, filename='<stream>': it(fd.read(), getattr(fd, 'name', filename))
