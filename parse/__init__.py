import ast

from . import core
from . import tree

r = core.Parser

SIG_CLOSURE_END    = type('SIG_CLOSURE_END', (tree.Constant, tree.Internal), {})
STATE_AFTER_OBJECT = next(core.STATEGEN)


# Handle an infix link.
#
# The right-hand statement is assumed to be unparsed yet.
#
def infixl(stream, op):

    stream.state &= ~STATE_AFTER_OBJECT

    br  = False
    rhs = next(stream)
    rhsbound = False

    # Note that constant strings aren't equal to anything but themselves.
    # This will only return True for a link.
    while rhs == '\n':

        br  = br or rhs
        rhs = next(stream)

    if isinstance(rhs, tree.Internal):

        # `(a R)`
        stream.repeat.appendleft(rhs)
        rhs = None

    elif br == '\n' != op and not rhs.indented:

        # `a R \n b` <=> `a R b` iff `b` is indented.
        stream.repeat.appendleft(rhs)
        rhs = br

    if isinstance(rhs, tree.Link) and not rhs.closed and rhs.infix:

        # `a R Q b` <=> `(a R) Q b` if R is prioritized over Q,
        #               `a R (Q b)` otherwise.
        rhsbound = stream.has_priority(op, rhs)
        rhs      = None if rhsbound else rhs

    # Chaining a single expression doesn't make sense.
    if rhs is not None or op not in ('\n', ''):

        stream.stuff = infixl_insert_rhs(stream, stream.stuff, op, rhs)

    stream.state |= STATE_AFTER_OBJECT
    rhsbound and infixl(stream, rhs)


# Recursive implementation of bracketless shunting-yard algorithm.
#
# Tests show that it's NOT much slower than iterative version, but this one looks
# neater. Note that if this hits the stack limit, the compiler would do that, too.
#
def infixl_insert_rhs(stream, root, op, *rhs):

    if root.traversable:

        if stream.has_priority(op, root[0]):

            # `a R b Q c` <=> `a R (b Q c)` if Q is prioritized over R
            root.append(infixl_insert_rhs(stream, root.pop(), op, *rhs))
            return root

        elif op == root[0] and rhs is not None:

            root.extend(rhs)  # A small extension to the shunting-yard.
            return root       # `a R b R c` <=> `R a b c` if R is left-fixed.

    # `R`         <=> `Link R`
    # `R rhs`     <=> `Expression [ Link '', Link R, Link rhs ]`
    # `lhs R`     <=> `Expression [ Link R, Link lhs ]`
    # `lhs R rhs` <=> `Expression [ Link R, Link lhs, Link rhs ]`
    e = tree.Expression([op, root] if rhs is None else [op, root, rhs])
    return e.in_between(root, op if rhs is None else rhs)


@r.token(r' *', core.STATE_AT_LINE_START)
#
# indent = ^ ' ' *
#
def indent(stream, token):

    indent = len(token.group())

    if indent > stream.indent[-1]:

        stream.indent.append(indent)
      # yield from do(stream, token, indented=True)
        for _ in do(stream, token, indented=True): yield _
        return

    while indent != stream.indent.pop():

        yield SIG_CLOSURE_END('')
        stream.indent or stream.error('no matching indentation level', after=True)

    stream.indent.append(indent)


@r.token(r'[^\S\n]+|\s*#[^\n]*')
#
# whitespace = < whitespace > | '#', < anything but line feed >
#
def whitespace(stream, token):

    return ()


@r.token(r'(?i)0(b[0-1]+|o[0-7]+|x[0-9a-f]+)')
#
# intb = int2 | int8 | int16
# int2 = '0b', ( '0' .. '1' ) +
# int8 = '0o', ( '0' .. '7' ) +
# int16 = '0x', ( '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' ) +
#
def intb(stream, token):

    yield tree.Constant(ast.literal_eval(token.group()))


@r.token(r'([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?(j|J)?')
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
    yield tree.Constant((int(integral) * 10 ** exponent + fraction) * sign * imag)


@r.token(r'(b?r?)([\'"]{3}|"|\')((?:\\?.)*?)\2')
#
# string = 'b' ?, 'r' ?, ( sq_string | dq_string | sq_string_m | dq_string_m )
#
# sq_string = "'", ( '\\' ?, < any character > ) * ?, "'"
# dq_string = '"', ( '\\' ?,  < any character > ) * ?, '"'
# sq_string_m = "'''", ( '\\' ?, < any character > ) * ?, "'''"
# dq_string_m = '"""', ( '\\' ?,  < any character > ) * ?, '"""'
#
def string(stream, token):

    g = token.group(2) * (4 - len(token.group(2)))
    yield tree.Constant(ast.literal_eval('{1}{0}{3}{0}'.format(g, *token.groups())))


@r.token(r'(\w+|[!$%&*+\--/:<-@\\^|~]+|,+)|`(\w+)`|\s*(\n)')
#
# link = word | < ascii punctuation > + | ',' + | ( '`', word, '`' ) | '\n'
#
# word = ( < alphanumeric > | '_' ) +
#
def link(stream, token):

    yield tree.Link(next(_ for _ in token.groups() if _))

    stream.state & STATE_AFTER_OBJECT and \
      (token.group().startswith('`') or stream.repeat[-1].infix) and \
        infixl(stream, stream.repeat.pop())


@r.token('[\(\[\{]')
#
# do = '(' | '[' | '{'
#
def do(stream, token, indented=False, pars={'(': ')', '{': '}', '[': ']'}):

    par = token.group() if token else ''
    state_backup = stream.state & STATE_AFTER_OBJECT
    stuff_backup = stream.stuff

    stream.state &= ~STATE_AFTER_OBJECT
    stream.stuff = tree.Constant(None).at(stream)

    for item in stream:

        if not indented and stream.state & core.STATE_AT_FILE_END:

            stream.error('mismatched parentheses')

        elif isinstance(item, SIG_CLOSURE_END) and item.value == pars.get(par, ''):

            break

        elif isinstance(item, tree.Internal):

            stream.error('invalid indentation or mismatched parentheses', after=True)

        elif stream.state & STATE_AFTER_OBJECT:

            # Two objects in a row should be joined with an empty infix link.
            stream.repeat.appendleft(item)
            infixl(stream, tree.Link('').before(item))

        # Ignore line feeds directly following an opening parentheses.
        elif item != '\n':

            stream.stuff = item
            stream.state |= STATE_AFTER_OBJECT

    # When handling literals, wrap the block into a prefix function call.
    if par in ('{', '['):

        stream.repeat.appendleft(stream.stuff)
        stream.stuff = tree.Link(par + pars[par]).before(stream.stuff)
        infixl(stream, tree.Link('').before(stream.stuff))

    stream.stuff.indented = indented
    stream.stuff.closed   = True

    # Further expressions should not touch this block.
    indented and stream.repeat.appendleft(tree.Link('\n').at(stream))

    stream.repeat.appendleft(stream.stuff)

    stream.state &= ~STATE_AFTER_OBJECT
    stream.state |= state_backup
    stream.stuff = stuff_backup
    return ()


@r.token(r'', core.STATE_AT_FILE_END)
@r.token(r'[\)\]\}]')
#
# end = ')' | ']' | '}' | $
#
def end(stream, token):

    yield SIG_CLOSURE_END(token.group())


@r.token(r'"|\'')
#
# string_err = "'" | '"'
#
def string_err(stream, token):

    stream.error('mismatched quote')


@r.token(r'.')
#
# error = < unmatched symbol >
#
def error(stream, token):

    stream.error('invalid input')
