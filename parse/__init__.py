import ast

from . import core
from . import tree

r = core.Parser

SIG_CLOSURE_END    = type('SIG_CLOSURE_END', (tree.Constant, tree.Internal), {})
STATE_AFTER_OBJECT = next(core.STATEGEN)


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


def infixl(stream, op):  # (this isn't a token, this is a helper)

    stream.state &= ~STATE_AFTER_OBJECT

    br  = False
    lhs = [stream.stuff]
    rhs = next(stream)
    rhsless = False
    rhsbound = False

    # Note that constant strings aren't equal to anything but themselves.
    # This will only return True for a link.
    while rhs == '\n':

        br  = True
        rhs = next(stream)

    if isinstance(rhs, tree.Internal):

        # `(a R)`
        stream.repeat.appendleft(rhs)
        rhsless = True

    elif br and op != '\n' and not rhs.indented:

        # `a R \n b` <=> `a R (\n b)` <=> `a R b` if `b` is indented,
        #                `(a R) \n b`             otherwise.
        stream.repeat.appendleft(rhs)
        rhsless = rhsbound = True
        rhs = tree.Link('\n')

    elif isinstance(rhs, tree.Link) and not rhs.closed and rhs.infix:

        # `a R Q b` <=> `(a R) Q b` if R is prioritized over Q,
        # `a R (Q b)` otherwise.
        rhsless = rhsbound = not stream.has_priority(rhs, op)

    # Chaining a single expression doesn't make sense.
    if not rhsless or op not in ('\n', ''):

        while isinstance(lhs[-1], tree.Expression) and not lhs[-1].closed and stream.has_priority(op, lhs[-1][0]):

            # `a R b Q c` <=> `a R (b Q c)` if Q is prioritized over R,
            # `(a R b) Q c` otherwise.
            lhs = lhs[-1]

        if isinstance(lhs[-1], tree.Expression) and not lhs[-1].closed and lhs[-1][0] == op and not rhsless:

            # `a R b R c` <=> `Op R (Link a) (Link b) (Link c)`
            # unless R is right-fixed.
            lhs[-1].append(rhs)

        else:

            # `R`         <=> `Op R`
            # `R rhs`     <=> `Call (Link R) (Link rhs)`
            # `lhs R`     <=> `Op R (Link lhs)`
            # `lhs R rhs` <=> `Op R (Link lhs) (Link rhs)`
            e = tree.Expression([op, lhs.pop()] + [rhs] * (not rhsless))

            if lhs:

                lhs.append(stream.located(e))

            else:

                # That was a fake expression, appending to it is futile.
                stream.stuff = stream.located(e)

    stream.state |= STATE_AFTER_OBJECT

    if rhsbound:

      # yield from infixl(stream, rhs)
        for _ in infixl(stream, rhs): yield _


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

    if stream.state & STATE_AFTER_OBJECT and (token.group().startswith('`') or stream.repeat[-1].infix):

      # yield from infixl(stream, stream.repeat.pop())
        for _ in infixl(stream, stream.repeat.pop()): yield _


@r.token('[\(\[\{]')
#
# do = '(' | '[' | '{'
#
def do(stream, token, indented=False, pars={'(': ')', '{': '}', '[': ']'}):

    par = token.group() if token else ''
    state_backup = stream.state & STATE_AFTER_OBJECT
    stuff_backup = stream.stuff

    stream.state &= ~STATE_AFTER_OBJECT
    stream.stuff = tree.Constant(None)

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
          # yield from infixl(stream, stream.located(tree.Link('')))
            for _ in infixl(stream, stream.located(tree.Link(''))): yield _

        # Ignore line feeds directly following an opening parentheses.
        elif item != '\n':

            stream.stuff = item
            stream.state |= STATE_AFTER_OBJECT

    # When handling literals, wrap the block into a prefix function call.
    if par in ('{', '['):

        op  = stream.located(tree.Link(''))
        lhs = stream.located(tree.Link(par + pars[par]))
        stream.stuff = tree.Expression([op, lhs, stream.stuff])

    stream.stuff.indented = indented
    stream.stuff.closed   = True

    # Further expressions should not touch this block.
    indented and stream.repeat.appendleft(tree.Link('\n'))

    stream.repeat.appendleft(stream.located(stream.stuff))

    stream.state &= ~STATE_AFTER_OBJECT
    stream.state |= state_backup
    stream.stuff = stuff_backup


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
