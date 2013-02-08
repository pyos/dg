import re
import ast
import functools
import collections

from . import tree, syntax

### Public API

it = lambda data, filename='<string>': next(_State(data, filename))
fd = lambda fd, name='<stream>': it(fd.read(), getattr(fd, 'name', name))

### Helpers

class _State (collections.Iterator, collections.deque):

    tokens  = []

    def __init__(self, data, filename):

        super().__init__()
        self.linestart = True
        self.filename  = filename
        self.buffer = data
        self.offset = 0
        self.indent = collections.deque([-1])

    def __next__(self):

        while not self:

            f, match = next((func, match)
                for regex, func, st in self.tokens              if st is self.linestart
                for match in [regex(self.buffer, self.offset)]  if match
            )

            self.offset    = match.end()
            self.linestart = match.group().endswith('\n')

            q = f(self, match)
            q is None or self.appendleft(q.at(self, match.start()))

        return self.popleft()

    def position(self, offset):

        part = self.buffer[:offset]
        return (offset, 1 + part.count('\n'), offset - part.rfind('\n'))

    def error(self, description, at):

        offset, lineno, charno = self.position(at)
        raise SyntaxError(description, (self.filename, lineno, charno, self.line(at)))

    line = lambda self, offset: self.buffer[
        self.buffer.rfind('\n', 0, offset) + 1:
        self.buffer. find('\n',    offset) + 1 or None  # 0 won't do here
    ]


def token(regex, linestart=False):

    return lambda f: _State.tokens.append((re.compile(regex, re.DOTALL).match, f, linestart)) or f


# Whether an infix link's priority is higher than the other one's.
#
# :param link: link to the right.
#
# :param in_relation_to: link to the left.
#
has_priority = functools.partial(
    lambda infixr, precedence, link, in_relation_to: (
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
        link == '->' or
          infixr(precedence(link)) < abs(precedence(in_relation_to))
    ),
    # Right-fixed links have positive precedence, left-fixed ones have negative.
    lambda x: abs(x) - (x > 0),
    lambda i, q={
      # Scope resolution
        '.':   0,
        '!.':  0,
        '!':   1,
      # Keyword arguments
        ':':   1,
      # Function application
        '':   -2,
      # Container subscription
        '!!': -3,
      # Math
        '**':  4,
        '*':  -5,
        '/':  -5,
        '//': -5,
        '%':  -5,
        '+':  -6,
        '-':  -6,
      # Comparison
        '<':  -8,
        '<=': -8,
        '>=': -8,
        '>':  -8,
        '==': -8,
        '!=': -8,
        'is': -8,
        'in': -8,
      # Binary operations
        '<<': -10,
        '>>': -10,
        '&':  -11,
        '^':  -12,
        '|':  -13,
      # Logic
        'and': -14,
        'or':  -15,
      # Low-priority binding
        '$':   16,
      # Function definition
        '->':  17,
      # Sequential evaluation
        ',':  -18,
      # Local binding
        'where': 19,
      # Assignment
        '=':   19,
        '!!=': 19,
        '+=':  19,
        '-=':  19,
        '*=':  19,
        '**=': 19,
        '/=':  19,
        '//=': 19,
        '%=':  19,
        '&=':  19,
        '^=':  19,
        '|=':  19,
        '<<=': 19,
        '>>=': 19,
      # Conditionals
        'if':   20,
        'else': 21,
      # Immediate return
        ';':  -100499,
      # Chaining
        '\n': -100500,
    }.get: q(i, -7)  # Default
)


# Whether an operator is non-associative with itself (i.e. should be joined.)
# Note that this is only necessary if you're not doing some kind of fold.
# Unless, of course, you don't want the compiler to consume the whole stack.
unassoc = {',', '..', '::', '', '\n'}.__contains__
unary   = {'!', ';'}.__contains__


# Handle an infix link.
#
# :param lhs, op, rhs: respective parts of an infix expression.
#
def infixl(stream, lhs, op, rhs):

    br       = False
    rhsbound = None

    # Note that constant strings aren't equal to anything but themselves.
    # This will only return True for a link.
    while rhs == '\n' and not unary(op):

        br  = br or rhs
        rhs = next(stream)

    if isinstance(rhs, tree.Internal) or unary(op):

        # `(a R)`
        stream.appendleft(rhs)
        rhs = None

    elif br == '\n' and op == '' and rhs.indented:

        # `a \n b ...` <=> `a b ...` iff `b ...` is indented.
        # i.e. an indented block with no infix link before it means
        # line continuation.
        qs = rhs[1:] if isinstance(rhs, tree.Expression) and rhs[0] == '\n' else [rhs]

        for q in qs:

            lhs = infixl_insert_rhs(lhs, op, q)

        return lhs

    elif br == '\n' != op and not rhs.indented:

        # `a R \n b` <=> `a R b` iff `b` is indented.
        stream.appendleft(rhs)
        rhs = br

    if isinstance(rhs, tree.Link) and not rhs.closed and rhs.infix:

        # `a R Q b` <=> `(a R) Q b` if R is prioritized over Q or R is empty.
        rhsbound = rhs if op == '' or has_priority(op, rhs) else None
        rhs      = None if rhsbound else rhs

    # Chaining a single expression doesn't make sense.
    if rhs is not None or op not in ('\n', ''):

        lhs = infixl_insert_rhs(lhs, op, rhs)

    return infixl(stream, lhs, rhsbound, next(stream)) if rhsbound else lhs


# Recursive implementation of bracketless shunting-yard algorithm.
#
# Tests show that it's NOT much slower than iterative version, but this one looks
# neater. Note that if this hits the stack limit, the compiler would do that, too.
#
def infixl_insert_rhs(root, op, rhs):

    if root.traversable:

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
    e = tree.Expression([op, root] if rhs is None else [op, root, rhs])
    e.closed = rhs is None
    return e.in_between(root, op if rhs is None else rhs)

### Tokens


@token(r' *', linestart=True)
#
# indent = ^ ' ' *
#
def indent(stream, token):

    indent = len(token.group())

    if indent > stream.indent[-1]:

        stream.indent.append(indent)
        return do(stream, token, preserve_close_state=True)

    while indent != stream.indent.pop():

        stream.appendleft(tree.Internal('').at(stream, token.end()))
        stream.indent or stream.error('no matching indentation level', token.start())

    stream.indent.append(indent)


@token(r'[^\S\n]+|\s*#[^\n]*')
#
# whitespace = < whitespace > | '#', < anything but line feed >
#
def whitespace(stream, token): pass


@token(r'(?i)[+-]?0(b[0-1]+|o[0-7]+|x[0-9a-f]+)')
#
# intb = int2 | int8 | int16
# int2 = '0b', ( '0' .. '1' ) +
# int8 = '0o', ( '0' .. '7' ) +
# int16 = '0x', ( '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' ) +
#
def intb(stream, token):

    return tree.Constant(ast.literal_eval(token.group()))


@token(r'([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?(j|J)?')
#
# number = int10s, ( '.', int10 ) ?, ( [eE], int10s ) ?, [jJ] ?
#
# int10s = ( '+' | '-' ) ?, int10
# int10  = < any digit > +
#
def number(stream, token):

    sign, integral, fraction, exponent, imag = token.groups()
    sign     = -1 if sign == '-' else 1
    imag     = 1j if imag        else 1
    exponent = int(exponent or 0)
    fraction = int(fraction) / 10 ** (len(fraction) - exponent) if fraction else 0
    return tree.Constant((int(integral) * 10 ** exponent + fraction) * sign * imag)


@token(r'([br]*)(\'\'\'|"""|"|\')((?:\\?.)*?)\2')
#
# string = ( 'b' | 'r' ) *, ( sq_string | dq_string | sq_string_m | dq_string_m )
#
# sq_string = "'", ( '\\' ?, < any character > ) * ?, "'"
# dq_string = '"', ( '\\' ?,  < any character > ) * ?, '"'
# sq_string_m = "'''", ( '\\' ?, < any character > ) * ?, "'''"
# dq_string_m = '"""', ( '\\' ?,  < any character > ) * ?, '"""'
#
def string(stream, token):

    g = token.group(2) * (4 - len(token.group(2)))
    q = ''.join(sorted(set(token.group(1))))
    return tree.Constant(ast.literal_eval(''.join([q, g, token.group(3), g])))


@token(r"(\w+'*|\*+(?=:)|([!$%&*+\--/:<-@\\^|~;]+|,+))|\s*(\n)|`(\w+'*)`")
#
# link = word | < ascii punctuation > + | ',' + | ( '`', word, '`' ) | '\n'
#
# word = ( < alphanumeric > | '_' ) +, "'" *
#
def link(stream, token, infixn={'if', 'else', 'or', 'and', 'in', 'is', 'where'}):

    infix = token.group(2) or token.group(3) or token.group(4)
    return tree.Link(infix or token.group(), infix or (token.group() in infixn))


@token('\(')
#
# do = '('
#
def do(stream, token, preserve_close_state=False):

    par = token.group().strip() if token else ''
    object   = tree.Constant(None).at(stream, token.end())
    can_join = False

    for item in stream:

        if isinstance(item, tree.Internal):

            (par + item.value) in ('', '()') or stream.error(
              'unexpected EOF'         if par and stream.offset >= len(stream.buffer) else
              'unexpected dedent'      if par and not item.value else
              'unexpected close-paren' if not par and item.value else
              'invalid close-paren', item.location.start[0]
            )

            break

        elif can_join:

            # Two objects in a row should be joined with an empty infix link.
            object = infixl(stream, object, tree.Link('', True).before(item), item)

        # Ignore line feeds directly following an opening parentheses.
        elif item != '\n':

            object, can_join = item, True

    # Further expressions should not touch this block.
    par or stream.appendleft(tree.Link('\n', True).after(object))

    object.indented = not par
    object.closed  |= not preserve_close_state
    return object


@token(r'\)|$')
#
# end = ')' | $
#
def end(stream, token):

    return tree.Internal(token.group())


@token(r'"|\'')
#
# string_err = "'" | '"'
#
def string_err(stream, token):

    stream.error('unexpected EOF while reading a string literal', token.start())


@token(r'.')
#
# error = < unmatched symbol >
#
def error(stream, token):

    stream.error('invalid input', token.start())
