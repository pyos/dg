from re          import compile
from ast         import literal_eval
from collections import Iterator, deque, namedtuple

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
            ('{!r:>1}' if self[0] in '.\n' else ' {!r} ').format(self[0]).join(map(repr, self[1:]))
        )


class ExpressionL (Expression):

    closed = True

    def __repr__(self):

        return '({1!r} {0!r})'.format(*self)


class ExpressionR (Expression):

    def __repr__(self):

        return ('({0!r} {1!r})' if self.closed else '{0!r} {1!r}').format(*self)


class Link (str, Node):

    def __repr__(self):

        return ('({})' if self.closed else '{}').format(self)


class LinkI (Link):

    infix = True


class Constant (Node):

    def __init__(self, value):

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
has_priority = lambda a, b, get={
    # `a R b Q c` <=> `a R (b Q c)` if left binding strength of `Q`
    # is higher than right binding strength of `R`.
    '@':     ( 5,    5),    # attribute of `self`
    '.':     ( 0,    0),    # getattr
    '!.':    ( 0,    0),    # call with no arguments, then getattr
    '!':     ( 0,   -10),   # call with no arguments
    ':':     ( 0,   -10),   # keyword argument
    '':      (-20,  -20),   # call with an argument
    '!!':    (-30,  -30),   # container subscription (i.e. `a[b]`)
    '**':    (-30,  -40),   # exponentiation
    '*':     (-50,  -50),   # multiplication
    '/':     (-50,  -50),   # fp division
    '//':    (-50,  -50),   # int division
    '%':     (-50,  -50),   # modulus
    '+':     (-60,  -60),   # addition
    '-':     (-60,  -60),   # subtraction
    # -70 is the default value for everything not on this list.
    '<':     (-80,  -80),   # less than
    '<=':    (-80,  -80),   # ^ or equal
    '>':     (-80,  -80),   # greater than
    '>=':    (-80,  -80),   # ^ or equal
    '==':    (-80,  -80),   # equal
    '!=':    (-80,  -80),   # not ^
    'is':    (-80,  -80),   # occupies the same memory location as
    'in':    (-80,  -80),   # is one of the elements of
    '<<':    (-100, -100),  # *  2 **
    '>>':    (-100, -100),  # // 2 **
    '&':     (-110, -110),  # bitwise and
    '^':     (-120, -120),  # bitwise xor
    '|':     (-130, -130),  # bitwise or
    'and':   (-140, -140),  # B if A else A
    'or':    (-150, -150),  # A if A else B
    '$':     (-150, -160),  # call with one argument and no f-ing parentheses
    '->':    (-25,  -180),  # a function
    '~>':    (-25,  -180),  # a method (i.e. a function with `self` as an argument)
    ',':     (-170, -170),  # a tuple
    '=':     (-170, -180),  # assignment
    '!!=':   (-170, -180),  # in-place versions of some of the other functions
    '+=':    (-170, -180),
    '-=':    (-170, -180),
    '*=':    (-170, -180),
    '**=':   (-170, -180),
    '/=':    (-170, -180),
    '//=':   (-170, -180),
    '%=':    (-170, -180),
    '&=':    (-170, -180),
    '^=':    (-170, -180),
    '|=':    (-170, -180),
    '<<=':   (-170, -180),
    '>>=':   (-170, -180),
    'where': (-170, -180),  # with some stuff that is not visible outside of that expression
    'for':   (-180, -190),  # evaluate stuff for each item in an iterable
    'while': (-180, -190),  # evaluate stuff until condition becomes false
    '=>':    (-180, -190),  # if-then
    '\n':    (-230, -230),  # do A then B
}.get, default=(-70, -70): get(a, default)[0] > get(b, default)[1]


# If `R` is in `unassoc`, `a R b R c` is returned as `Expression [R, a, b, c]`.
unassoc = {',', '..', '::', '', '\n'}

# If `R` is in `nolhs`, `a R b` is always parsed as `a (R b)`.
# If `R` is in `norhs`, `a R b` is always parsed as `(a R) b`.
nolhs = {'@'}
norhs = {'!'}

# If `a` is in `specl`, `a b => c` will be parsed into `Expression [a, b, c]`.
# If `a` is in `specm`, everything after `a` until the end of the line
# will be parsed as a single expression.
specl = {'for', 'while', 'with'}
specm = {'if', 'except'}


def spech(self, it):

    if isinstance(it, Link) and not it.indented and not it.closed:

        if it in specl:

            return infix(self, do(self, None, it.location, lambda x: x == '=>'), it, next(self))

        if it in specm:

            block = do(self, None, it.location, lambda x: ((x == '\n' or isinstance(x, Internal)) and (self.appendleft(x) or True)))

            if not isinstance(block, Constant) or block.value is not None:

                return infix(self, it, LinkI('').after(it), block)

    return it


def infix(self, lhs, op, rhs):
    br = False

    while rhs == '\n' and not op in norhs:
        # There are some special cases for indented RHS,
        # so we'll have to ignore the line breaks for now.
        br, rhs = rhs, next(self)

    if op == '':
        if isinstance(rhs, Internal):
            # `(a\n)`.
            self.appendleft(rhs)
            return lhs

        if br and not rhs.indented:
            # `a\n`.
            return infix(self, lhs, br, rhs)

        if rhs.infix and not rhs.closed and rhs in nolhs:
            # `a (R b)`.
            rhs = infix(self, rhs, op, next(self))

        if rhs.infix and not rhs.closed:
            # `a R b`. There's no empty operator at all.
            return infix(self, lhs, rhs, next(self))

    else:
        if isinstance(rhs, Internal) or op in norhs:
            # `(a R)`
            return infixin(op, lhs, self.appendleft(rhs))

        if br and not rhs.indented:
            # `a R\n`.
            return infix(self, infixin(op, lhs), br, rhs)

        if rhs.infix and not rhs.closed:
            if not has_priority(rhs, op) and rhs not in nolhs:
                # `a R Q b` <=> `(a R) Q b` if Q does not have priority over R.
                return infix(self, infixin(op, lhs), rhs, next(self))
            # `a R (Q b)` otherwise.
            rhs = infix(self, rhs, LinkI('').after(rhs), next(self))

    return infixin(op, lhs, spech(self, rhs) if has_priority('', lhs if op == '' and lhs.infix and not lhs.closed else op) else rhs)


def infixin(op, lhs, rhs=None):

    if isinstance(lhs, Expression) and not lhs.closed:

        if has_priority(op, lhs[0]):
            # `a R b Q c` <=> `a R (b Q c)` if Q has priority over R
            lhs.append(infixin(op, lhs.pop(), rhs))
            return lhs

        elif len(lhs) > 2 and op == lhs[0] and op in unassoc and rhs is not None:
            # `a R b R c` <=> `R a b c`
            lhs.extend(rhs[1:] if op == '' and not rhs.closed and isinstance(rhs, Expression) and rhs[0] == '\n' else [rhs])
            return lhs

    e = (
        # `R rhs` => `ExpressionR [ Link R, Link rhs ]`
        ExpressionR([lhs, rhs]) if op == '' and lhs.infix and not lhs.closed else
        # `lhs R` => `ExpressionL [ Link R, Link lhs ]`
        ExpressionL([op, lhs]) if rhs is None else
        # `lhs
        #    a  => Expression [ Link '', lhs, a, b ]
        #    b`
        Expression([op, lhs] + rhs[1:]) if op == '' and not rhs.closed and isinstance(rhs, Expression) and rhs[0] == '\n' else
        # `lhs R rhs` => `Expression [ Link R, Link lhs, Link rhs ]`
        Expression([op, lhs, rhs])
    )
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
        stream.appendleft(LinkI('\n').at(pos, stream))
        stream.appendleft(Internal('').at(pos, stream))


def string(stream, token, pos):
    g = token.group(2) * (4 - len(token.group(2)))
    q = ''.join(sorted(set(token.group(1))))
    return Constant(literal_eval(''.join([q, g, token.group(3), g])))


def link(stream, token, pos, infixn={'or', 'and', 'in', 'is', 'where'}):
    inf = token.group(2) or token.group(3) or token.group(4)
    return (LinkI if token.group() in infixn or inf else Link)(inf or token.group()).at(pos, stream)


def do(stream, token, pos, end=lambda x: isinstance(x, Internal) and x.value == ')', preserve_close_state=False):
    object   = Constant(None).at(pos, stream)
    can_join = False

    for item in stream:

        if end(item): break

        if isinstance(item, Internal):

            if token and not token.group().strip():
                # An indented block can also be ended by a close-paren.
                stream.indent.pop() < 0 and error('too many close-parens', item)
                stream.appendleft(item)
                break

            error('this block was not closed properly' if item.value
             else 'unexpected EOF in a block', pos)

        elif can_join:

            # Two objects in a row should be joined with an empty infix link.
            object = infix(stream, object, LinkI('').after(object), item)

        # Ignore line feeds directly following an opening parentheses.
        elif item != '\n':

            object, can_join = spech(stream, item), True

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
