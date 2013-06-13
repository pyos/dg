import re
import ast
import functools
import collections

from . import tree, syntax


it = lambda it, filename='<string>': next(State(it, filename, tokens))
fd = lambda fd, filename='<stream>': it(fd.read(), getattr(fd, 'name', filename))


class State (collections.Iterator, collections.deque):

    def __init__(self, data, filename, tokens):

        super().__init__()
        self.linestart = True
        self.filename  = filename
        self.buffer = data
        self.offset = 0
        self.indent = collections.deque([-1])
        self.tokens = tokens

    def __next__(self):

        while not self:

            f, match = self.tokens.match(self.buffer, self.offset, self.linestart)
            self.offset    = match.end()
            self.linestart = match.group().endswith('\n')
            q = f(self, match)

            if q is not None:

                return q.at(self, match.start())

        return self.popleft()

    # position :: int -> (int, int, int)
    #
    # Transform a character offset into an (offset, lineno, charno) triple.
    #
    def position(self, offset):

        part = self.buffer[:offset]
        return (offset, 1 + part.count('\n'), offset - part.rfind('\n'))

    # error :: (str, int) -> _|_
    #
    # Raise a `SyntaxError` at a given offset.
    #
    def error(self, description, at):

        offset, lineno, charno = self.position(at)
        raise SyntaxError(description, (self.filename, lineno, charno, self.line(at)))

    # line :: int -> str
    #
    # Get a line which contains the character at a given offset.
    #
    def line(self, offset):

        return self.buffer[
            self.buffer.rfind('\n', 0, offset) + 1:
            self.buffer. find('\n',    offset) + 1 or None  # 0 won't do here
        ]


class TokenSet (list):

    # type TokenHandler = (Stream, MatchObject) -> Maybe StructMixIn
    # type TokenSet = [((str, int) -> Maybe MatchObject, TokenHandler, bool)]
    #
    # () :: (str, Optional bool) -> TokenHandler -> TokenHandler
    #
    # A decorator-generating version of :meth:`add`.
    #
    def __call__(self, regex, at_line_start=False):

        return functools.partial(self.add, regex, at_line_start=at_line_start)

    # add :: (str, TokenHandler, Optional bool) -> TokenHandler
    #
    # Add a handler for some token.
    #
    # NOTE unlike `(?m)^`, using `at_line_start` guarantees that
    #   a handler won't be called the second time if
    #   the match is empty.
    #
    def add(self, regex, f, at_line_start=False):

        self.append((re.compile(regex, re.DOTALL).match, f, at_line_start))
        return f

    # match :: (str, int, bool) -> (TokenHandler, MatchObject)
    #
    # Attempt to find a handler suitable for parsing a part of a string.
    #
    def match(self, text, offset, at_line_start):

        return next((func, match)
            for regex, func, als_flag in self   if als_flag is at_line_start
            for match in [regex(text, offset)]  if match
        )


# In all comments below, `R` and `Q` are infix links, while lowercase letters
# are arbitrary expressions.
tokens = TokenSet()

# has_priority :: (Link, Link) -> bool
#
# Whether the first infix link has priority over the second one.
#
# NOTE in `a R b Q c`, `Q` should be the first link.
#
has_priority = functools.partial(
    lambda link, in_relation_to, infixr, precedence: (
        # `a R b -> c` <=> `a R (b -> c)` for all `R`.
        # `a R b -> c Q d` <=> `a R (b -> c Q d)` iff
        #   `has_priority(Q, R) and has_priority(Q, '->')`
        #  `a R (b -> c) Q d` otherwise.
        link == '->' or (
          # `a -> b where c` <=> `a -> (b where c)` for obvious reasons.
          # `a -> b, c` <=> `(a -> b), c` for probably not so obvious ones.
          not (link == ',' and in_relation_to == '->') and
          # No other operator is that complex.
          infixr(precedence(link)) < abs(precedence(in_relation_to))
        )
    ),
    # Right-fixed links have positive precedence, left-fixed ones have negative.
    # Right-fixed ones gain +1 to their priority, but since `<` is used above
    # rather than `<=`, that only affects expressions like `a R b R c`.
    infixr     = lambda x: abs(x) - (x > 0),
    precedence = lambda i, q={
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
      # Sequential evaluation
        ',':  -17,
      # Local binding
        'where': 18,
      # Assignment
        '=':   18,
        '!!=': 18,
        '+=':  18,
        '-=':  18,
        '*=':  18,
        '**=': 18,
        '/=':  18,
        '//=': 18,
        '%=':  18,
        '&=':  18,
        '^=':  18,
        '|=':  18,
        '<<=': 18,
        '>>=': 18,
      # Function definition
        '->':  19,
      # Conditionals
        'if':   20,
        'else': 21,
      # Immediate return
        ';':  -100499,
      # Chaining
        '\n': -100500,
    }.get: q(i, -7)  # Default
)


# If `unassoc(R)`: `a R b R c` <=> `Expression [ Link R, Link a, Link b, Link c]`
# Otherwise:       `a R b R c` <=> `Expression [ Link R, Expression [...], Link c]`
# (This doesn't apply to right-fixed links.)
unassoc = {',', '..', '::', '', '\n'}.__contains__

# These operators have no right-hand statement part in any case.
unary = {'!', ';'}.__contains__


# infixl :: (State, StructMixIn, Link, StructMixIn) -> StructMixIn
#
# Handle an infix expression given its all three parts.
#
# If that particular expression has no right-hand statement part,
# `rhs` will be pushed to the object queue.
#
def infixl(stream, lhs, op, rhs):

    break_   = False
    rhsbound = None

    while rhs == '\n' and not unary(op):

        break_, rhs = rhs, next(stream)

    if isinstance(rhs, tree.Internal) or unary(op):

        # `(a R)`, and `rhs` is a close-paren.
        stream.appendleft(rhs)
        rhs = None

    elif break_ and op == '' and rhs.indented:

        # `a \n b ...` <=> `a b ...` iff `b ...` is indented.
        #
        # That is, if an indented block follows a line with an empty infix
        # link at the end, each line of that block is an additional
        # argument to that empty link.
        for rhs in syntax.binary_op('\n', rhs, lambda e: [e]):

            lhs = infixl_insert_rhs(lhs, op, rhs)

        return lhs

    elif break_ and op != '\n' and not rhs.indented:

        # `a R`. There was no `rhs` before a line break,
        # and no indented block immediately after it either.
        stream.appendleft(rhs)
        rhs = break_

    if isinstance(rhs, tree.Link) and not rhs.closed and rhs.infix:

        # `a R Q b` <=> `(a R) Q b` if R is prioritized over Q or R is empty.
        rhsbound = rhs if op == '' or has_priority(op, rhs) else None
        rhs      = None if rhsbound else rhs

    # Chaining a single expression doesn't make sense.
    if rhs is not None or op not in ('\n', ''):

        lhs = infixl_insert_rhs(lhs, op, rhs)

    return infixl(stream, lhs, rhsbound, next(stream)) if rhsbound else lhs


# infixl_insert_rhs :: (StructMixIn, Link, StructMixIn) -> StructMixIn
#
# Recursively descends into `root` if infix precedence rules allow it to,
# otherwise simply creates and returns a new infix expression AST node.
#
# That is, it's a recursive bracketless shunting-yard algorithm implementation.
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


@tokens(r' *', at_line_start=True)
#
# indent = ^ ' ' *
#
def indent(stream, token):

    indent = len(token.group())

    if indent > stream.indent[-1]:

        stream.indent.append(indent)
        return do(stream, token, {''}, preserve_close_state=True)

    while indent != stream.indent.pop():

        stream.appendleft(tree.Internal('').at(stream, token.end()))
        stream.indent or stream.error('no matching indentation level', token.start())

    stream.indent.append(indent)


@tokens(r'[^\S\n]+|\s*#[^\n]*')
#
# whitespace = < whitespace > | '#', < anything but line feed >
#
def whitespace(stream, token): pass


@tokens(r'(?i)[+-]?(?:0b[0-1]+|0o[0-7]+|0x[0-9a-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?j?)')
#
# number = [+-] ?, (int2 | int8 | int16 | (int10, ( '.', int10 ) ?, ( e, [+-] ?, int10 ) ?, j ?))
#
# int2 = '0b', ( '0' .. '1' ) +
# int8 = '0o', ( '0' .. '7' ) +
# int10 = ( '0' .. '9' ) +
# int16 = '0x', ( '0' .. '9' | 'a' .. 'f' ) +
#
def number(stream, token):

    return tree.Constant(ast.literal_eval(token.group()))


@tokens(r'([br]*)(\'\'\'|"""|"|\')((?:\\?.)*?)\2')
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


@tokens(r"(\w+'*|\*+(?=:)|([!$%&*+\--/:<-@\\^|~;]+|,+))|\s*(\n)|`(\w+'*)`")
#
# link = word | < ascii punctuation > + | ',' + | ( '`', word, '`' ) | '\n'
#
# word = ( < alphanumeric > | '_' ) +, "'" *
#
def link(stream, token, infixn={'if', 'else', 'or', 'and', 'in', 'is', 'where'}):

    infix = token.group(2) or token.group(3) or token.group(4)
    return tree.Link(infix or token.group(), infix or (token.group() in infixn))


@tokens('\(')
#
# do = '('
#
def do(stream, token, ends={')'}, preserve_close_state=False):

    par = token.group().strip() if token else ''
    object   = tree.Constant(None).at(stream, token.end())
    can_join = False

    for item in stream:

        if isinstance(item, tree.Internal):

            item.value in ends or stream.error(
              'unexpected block delimiter' if item.value else
              'unexpected EOF'             if stream.offset >= len(stream.buffer) else
              'unexpected dedent', item.location.start[0]
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


@tokens(r'\)|$')
#
# end = ')' | $
#
def end(stream, token):

    return tree.Internal(token.group())


@tokens(r'"|\'')
#
# string_err = "'" | '"'
#
def string_err(stream, token):

    stream.error('unexpected EOF while reading a string literal', token.start())


@tokens(r'.')
#
# error = < unmatched symbol >
#
def error(stream, token):

    stream.error('invalid input', token.start())
