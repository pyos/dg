import ast

from . import core
from . import tree

r = core.Parser

SIG_CLOSURE_END    = type('SIG_CLOSURE_END', (str, tree.Internal), {})
STATE_AFTER_OBJECT = core.STATE_CUSTOM << 0


@r.token(r' *', core.STATE_AT_LINE_START)
@r.token(r'',   core.STATE_AT_FILE_START)  # Always start with an indent of 0.
#
# indent = ^ ( ' ' | '\t' ) *
#
def indent(stream, token):

    indent = len(token.group())

    if indent > stream.indent[-1]:

        stream.indent.append(indent)
      # yield from do(stream, token, indented=True, closed=bool(indent))
        for _ in do(stream, token, indented=True, closed=bool(indent)): yield _
        return

    while indent != stream.indent.pop():

        yield SIG_CLOSURE_END('')
        stream.indent or stream.error('no matching indentation level', after=True)

    stream.indent.append(indent)


@r.token(r'([!$%&*+\--/:<-@\\^|~]+|,+|if|unless|else|and|or)', STATE_AFTER_OBJECT)
@r.token(r'`(\w+)`', STATE_AFTER_OBJECT)
@r.token(r'\s*(\n)', STATE_AFTER_OBJECT)
#
# infix = < ascii punctuation > + | ',' + | ( '`', word, '`' ) | word_op | '\n'
#
# word = ( < alphanumeric > | '_' ) +
# word_op = 'if' | 'else' | 'unless' | 'or' | 'and'
#
def infix(stream, token):

    op = token if isinstance(token, str) else token.group(1)
    return infixl(stream, stream.located(tree.Link(op)))


def infixl(stream, op):

    stream.state &= ~STATE_AFTER_OBJECT

    br  = False
    lhs = [stream.stuff]
    rhs = next(stream)
    rhsless = False
    rhsbound = False

    while isinstance(rhs, tree.Link) and rhs == '\n':

        br  = True
        rhs = next(stream)

    if isinstance(rhs, tree.Internal):

        # `(a R)`
        stream.repeat.appendleft(rhs)
        rhsless = True

    elif br and op != '\n' and not getattr(rhs, 'indented', False):

        # `a R \n b` <=> `a R (\n b)` <=> `a R b` if `b` is indented,
        #                `(a R) \n b`             otherwise.
        stream.repeat.appendleft(rhs)
        rhsless = rhsbound = True
        rhs = tree.Link('\n')

    elif isinstance(rhs, tree.Link) and not hasattr(rhs, 'closed') and rhs.infix:

        # `a R Q b` <=> `(a R) Q b` if R is prioritized over Q,
        # `a R (Q b)` otherwise.
        rhsless = rhsbound = not stream.has_priority(rhs, op)

    # Chaining a single expression doesn't make sense.
    if not rhsless or op not in ('\n', ''):

        while not getattr(lhs[-1], 'closed', True) and stream.has_priority(op, lhs[-1][0]):

            # `a R b Q c` <=> `a R (b Q c)` if Q is prioritized over R,
            # `(a R b) Q c` otherwise.
            lhs = lhs[-1]

        if not getattr(lhs[-1], 'closed', True) and lhs[-1][0] == op and not rhsless:

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


@r.token('\(|\[|\{')
#
# do = '(' | '[' | '{'
#
def do(stream, token, indented=False, closed=True, pars={'(': ')', '{': '}', '[': ']'}):

    par = token.group() if token else ''
    closed = None if par in ('{', '[') else closed
    state_backup = stream.state & STATE_AFTER_OBJECT
    stuff_backup = stream.stuff

    stream.state &= ~STATE_AFTER_OBJECT
    stream.stuff = None

    for item in stream:

        if not indented and stream.state & core.STATE_AT_FILE_END:

            stream.error('mismatched parentheses')

        elif isinstance(item, SIG_CLOSURE_END) and item == pars.get(par, ''):

            break

        elif isinstance(item, tree.Internal):

            stream.error('invalid indentation or mismatched parentheses', after=True)

        elif stream.state & STATE_AFTER_OBJECT:

            # Two objects in a row should be joined with an empty infix link.
            stream.repeat.appendleft(item)
          # yield from infix(stream, '')
            for _ in infix(stream, ''): yield _

        # Ignore line feeds directly following an opening parentheses.
        elif not isinstance(item, tree.Link) or item != '\n':

            stream.stuff = item
            stream.state |= STATE_AFTER_OBJECT

    if hasattr(stream.stuff, '__dict__') and closed is not None:

        stream.stuff.indented = indented
        stream.stuff.closed   = closed or isinstance(stream.stuff, tree.Constant)

    # Further expressions should not touch this block.
    indented and stream.repeat.appendleft(tree.Link('\n'))

    # When handling literals, wrap the block into a prefix function call.
    if par in ('{', '['):

        op  = stream.located(tree.Link(''))
        lhs = stream.located(tree.Link(par + pars[par]))
        stream.stuff = tree.Expression([op, lhs, stream.stuff])
        stream.stuff.closed = True

    # If we use yield instead, outer blocks will receive SIG_CLOSURE_END
    # from `indent` before they get to this block. That may have some...
    # unexpected results, such as *inner* blocks going to the *outermost*
    # expression.
    stream.repeat.appendleft(stream.located(stream.stuff))

    stream.state &= ~STATE_AFTER_OBJECT
    stream.state |= state_backup
    stream.stuff = stuff_backup


@r.token(r'', core.STATE_AT_FILE_END)
@r.token(r'\)|\]|\}')
#
# end = ')' | ']' | '}' | $
#
def end(stream, token):

    yield SIG_CLOSURE_END(token.group())


@r.token(r'0(b)([0-1]+)')
@r.token(r'0(o)([0-7]+)')
@r.token(r'0(x)([0-9a-fA-F]+)')
#
# intb = int2 | int8 | int16
# int2 = '0b', ( '0' .. '1' ) +
# int8 = '0o', ( '0' .. '7' ) +
# int16 = '0x', ( '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' ) +
#
def intb(stream, token, bases={'b': 2, 'o': 8, 'x': 16}):

    yield tree.Constant(int(token.group(2), bases[token.group(1)]))


@r.token(r'([+-]?)([0-9]+)(?:\.([0-9]+))?(?:[eE]([+-]?[0-9]+))?(j|J)?')
#
# number = int10, ( '.', int10 ) ?, ( [eE], [+-] ?, int10 ) ?, [jJ] ?
#
# int10  = ( '0' .. '9' ) +
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
# string = 'r' ?, 'b' ?, ( sq_string | dq_string | sq_string_m | dq_string_m )
#
# sq_string = "'", ( '\\' ?, < any character > ) * ?, "'"
# dq_string = '"', ( '\\' ?,  < any character > ) * ?, '"'
# sq_string_m = "'''", ( '\\' ?, < any character > ) * ?, "'''"
# dq_string_m = '"""', ( '\\' ?,  < any character > ) * ?, '"""'
#
def string(stream, token):

    g = token.group(2) * (4 - len(token.group(2)))
    yield tree.Constant(ast.literal_eval('{1}{0}{3}{0}'.format(g, *token.groups())))


@r.token(r'"|\'')
#
# string_err = "'" | '"'
#
def string_err(stream, token):

    stream.error('mismatched quote')


# Note that "\w+" implies "if" and other infix links.
@r.token(r'(\w+|[!$%&*+\--/:<-@\\^|~]+|,+)')
@r.token(r'`(\w+)`')
@r.token(r'\s*(\n)')
#
# link = word | infix
#
def link(stream, token):

    yield tree.Link(token.group(1))


@r.token(r'\s')
@r.token(r'\s*#[^\n]*')
#
# whitespace = < whitespace > | '#', < anything but line feed >
#
def whitespace(stream, token):

    return ()


@r.token(r'.')
#
# error = < unmatched symbol >
#
def error(stream, token):

    stream.error('invalid input')
