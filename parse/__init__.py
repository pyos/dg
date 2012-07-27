import ast

from . import core
from . import tree
from .core import Parser as r

SIG_CLOSURE_END = tree.Internal()

STATE_AFTER_OBJECT = core.STATE_CUSTOM << 0


@r.token(r'', core.STATE_AT_FILE_START)
#
# bof = ^^
#
def bof(stream, token):

    stream.state |= core.STATE_AT_LINE_START
    return do(stream, token, indented=True)


@r.token(r'\s*(?:#.*?\s*)*(\n)')
#
# soft_break = ( ( comment, '\n' ) *, comment ) ?, '\n'
#
def soft_break(stream, token):

    return operator(stream, token) if stream.state & STATE_AFTER_OBJECT \
      else [tree.Link('\n')]

@r.token(r'\s*#[^\n]*')
#
# comment = '#', < anything but line feed >
#
def comment(stream, token):

    return ()


@r.token(r' *', core.STATE_AT_LINE_START)
#
# indent = ^ ( ' ' | '\t' ) *
#
def indent(stream, token):

    indent = len(token.group())

    if indent > stream.indent[-1]:

        stream.indent.append(indent)
      # yield from do(stream, token, indented=True)
        for _ in do(stream, token, indented=True): yield _
        return

    while indent != stream.indent.pop():

        yield SIG_CLOSURE_END
        stream.indent or stream.error('no matching indentation level', after=True)

    stream.indent.append(indent)


@r.token(r'', core.STATE_AT_FILE_END)
@r.token(r'\)')
#
# end = ')' | $
#
def end(stream, token):

    yield SIG_CLOSURE_END


@r.token(r'(`\w+`|[!$%&*+\--/:<-@\\^|~]+|,+|if|unless|else|and|or)', STATE_AFTER_OBJECT)
#
# operator = < ascii punctuation > + | ',' + | ( '`', word, '`' ) | word_op
#
# word = ( < alphanumeric > | '_' ) +
# word_op = 'if' | 'else' | 'unless' | 'or' | 'and'
#
def operator(stream, token):

    stream.state &= ~STATE_AFTER_OBJECT

    lhs = [stream.stuff]
    dedent = getattr(lhs[-1], 'indented', False)

    while not dedent and not getattr(lhs[-1], 'closed', True):

        lhs = lhs[-1]
        dedent |= len(lhs) < 3 or getattr(lhs[-1], 'indented', False)

    br  = None
    op  = token.group(1).strip('`') if token else '\n' if dedent else ''
    op  = stream.located(tree.Link(op))
    lhs = [stream.stuff]
    rhs = next(stream)
    rhsless = False

    while isinstance(rhs, tree.Link) and rhs == '\n':

        br  = rhs
        rhs = next(stream)  # Skip soft breaks.

    # rhsless is true:   `(lhs R)` or `lhs R \n not_rhs`
    # rhsless is false:  `lhs R rhs` or `lhs R \n indented_block`
    if isinstance(rhs, tree.Internal):

        yield rhs
        rhsless = True

        if op == '\n':

            # Chaining a single expression doesn't make sense.
            return

    elif token and br is not None and op != '\n' and not getattr(rhs, 'indented', False):

        # The operator was followed by something other than an object or
        # an indented block.
        yield rhs
        rhsless = True

    while not getattr(lhs[-1], 'closed', True) and stream.has_priority(op, lhs[-1][0]):

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
        e = tree.Expression((op, lhs.pop()) if rhsless else (op, lhs.pop(), rhs))

        if not lhs:

            # That was a fake expression, appending to it is futile.
            stream.stuff = stream.located(e)

        else:

            lhs.append(stream.located(e))

    stream.state |= STATE_AFTER_OBJECT


@r.token('\(')
#
# do = '('
#
def do(stream, token, indented=False):

    state_backup = stream.state & STATE_AFTER_OBJECT
    stuff_backup = stream.stuff

    stream.state &= ~STATE_AFTER_OBJECT
    stream.stuff = None

    for item in stream:

        if item is SIG_CLOSURE_END:

            (
                not indented
                and stream.state & core.STATE_AT_FILE_END
                and stream.error('non-closed block at EOF')
            )

            break

        elif stream.state & STATE_AFTER_OBJECT:

            # Two objects in a row should be joined with an empty operator.
            stream.repeat.appendleft(item)
          # yield from operator(stream, None)
            for _ in operator(stream, None): yield _

        else:

            stream.stuff = item
            stream.state |= STATE_AFTER_OBJECT

    # These SIG_CLOSURE_END are put there by `indent` when it unindents
    # for more than one level. All other stuff should have been handled.
    assert not set(stream.repeat) - {SIG_CLOSURE_END}

    if hasattr(stream.stuff, '__dict__'):

        # Note that constants cannot be marked as indented/closed.
        # The only objects those marks make sense for are expressions, though.
        stream.stuff.indented = indented
        stream.stuff.closed   = True

    # If we use yield instead, outer blocks will receive SIG_CLOSURE_END
    # from `indent` before they get to this block. That may have some...
    # unexpected results, such as *inner* blocks going to the *outermost*
    # expression.
    stream.repeat.appendleft(stream.located(stream.stuff))

    stream.state &= ~STATE_AFTER_OBJECT
    stream.state |= state_backup
    stream.stuff = stuff_backup


@r.token(r'0b([0-1]+)')
#
# int2 = '0b', ( '0' .. '1' ) +
#
def int2(stream, token):

    yield int(token.group(1), 2)


@r.token(r'0o([0-7]+)')
#
# int8 = '0o', ( '0' .. '7' ) +
#
def int8(stream, token):

    yield int(token.group(1), 8)


@r.token(r'0x([0-9a-fA-F]+)')
#
# int16 = '0x', ( '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' ) +
#
def int16(stream, token):

    yield int(token.group(1), 16)


@r.token(r'([+-]?)([0-9]+)(?:\.([0-9]+))?(?:[eE]([+-]?[0-9]+))?(j|J)?')
#
# number = int10, ( '.', int10 ) ?, ( [eE], [+-] ?, intpart ) ?, [jJ] ?
#
# int10  = ( '0' .. '9' ) +
#
def number(stream, token):

    sign, integral, fraction, exponent, imag = token.groups()
    exponent = int(exponent or 0)
    fraction = int(fraction) / 10 ** (len(fraction) - exponent) if fraction else 0
    integral = int(integral) * 10 ** exponent
    yield (integral + fraction) * (1j if imag else 1) * (-1 if sign == '-' else 1)


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
    yield ast.literal_eval('{1}{0}{3}{0}'.format(g, *token.groups()))


@r.token(r'"|\'')
#
# string_err = "'" | '"'
#
def string_err(stream, token):

    stream.error('unclosed string literal')


@r.token(r'\w+|[!$%&*+\--/:<-@\\^|~]+|,+|`\w+`')
#
# link = word | operator
#
def link(stream, token):

    yield tree.Link(token.group().strip('`'))


@r.token('\s')
#
# whitespace = < whitespace >
#
def whitespace(stream, token):

    return ()


@r.token()
def error(stream, token):

    stream.error('invalid input')
