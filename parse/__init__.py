import ast

from . import core
from . import tree
from . import libparse

SIG_CLOSURE_END        = tree.Internal()
SIG_EXPRESSION_BREAK   = tree.Internal()
SIG_EXPRESSION_BR_HARD = tree.Internal()

STATE_AFTER_OBJECT = libparse.STATE_CUSTOM << 0
STATE_PARSE_INDENT = libparse.STATE_CUSTOM << 1


class r (core.Parser):

    tokens = []


@r.token
#
# bof = ^^
#
def bof(stream: libparse.STATE_AT_FILE_START, token: r''):

    stream.state |= libparse.STATE_AT_LINE_START
    return do(stream, token, indented=True)


@r.token
#
# separator = '\n' | ';'
#
def separator(stream, token: r'\s*\n|;'):

    ok = stream.state & STATE_PARSE_INDENT or stream.ALLOW_BREAKS_IN_PARENTHESES

    if ';' in token.group():

        ok or stream.error('can\'t chain expressions here')
        yield SIG_EXPRESSION_BR_HARD

    elif ok:

        yield SIG_EXPRESSION_BREAK


@r.token
#
# comment = '#', < anything but '\n' > *
#
def comment(stream, token: r'\s*#[^\n]*'):

    # Note that any indentation strictly before a comment is ignored.
    return ()


@r.token
#
# indent = ^ ( ' ' | '\t' ) *
#
def indent(stream: libparse.STATE_AT_LINE_START | STATE_PARSE_INDENT, token: r' *'):

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


@r.token
#
# eof = $
#
def eof(stream: libparse.STATE_AT_FILE_END, token: r''):

    yield SIG_CLOSURE_END


@r.token
#
# end = ')'
#
def end(stream, token: r'\)'):

    yield SIG_CLOSURE_END


@r.token
#
# operator = < ascii punctuation > + | ( '`', word, '`' ) | word_op
#
# word = ( < alphanumeric > | '_' ) +
# word_op = 'if' | 'else' | 'unless' | 'or' | 'and'
#
def operator(stream: STATE_AFTER_OBJECT, token: r'`\w+`|[!$%&*-/:<-@\\^|~]+|if|unless|else|and|or'):

    stream.state &= ~STATE_AFTER_OBJECT

    br  = False  # whether there was a soft expression break after the operator
    op  = stream.located(tree.Link(token.group().strip('`') if token else ''))
    lhs = stream.stack
    rhs = next(stream)

    while rhs is SIG_EXPRESSION_BREAK:

        br  = True
        rhs = next(stream)  # Skip soft breaks.

    # rhsless is true:   `lhs R;` or `(lhs R)` or `lhs R \n not_rhs`
    # rhsless is false:  `lhs R rhs` or `lhs R \n indented_block`
    if isinstance(rhs, tree.Internal):

        # Either an explicit expression break or a block end was encountered.
        yield rhs
        rhsless = True

    elif bool(token) and br and not getattr(rhs, 'indented', False):

        # The operator was followed by something other than an object or
        # an indented block.
        yield SIG_EXPRESSION_BREAK
        yield rhs
        rhsless = True

    else:

        rhsless = False

    while isinstance(lhs[-1], tree.Expression) and stream.has_priority(op, lhs[-1][0]):

        lhs = lhs[-1]

    # `R`         <=> `Op R`
    # `R rhs`     <=> `Call (Link R) (Link rhs)`
    # `lhs R`     <=> `Op R (Link lhs)`
    # `lhs R rhs` <=> `Op R (Link lhs) (Link rhs)`
    e = tree.Expression((op, lhs.pop()) if rhsless else (op, lhs.pop(), rhs))
    lhs.append(stream.located(e))

    stream.state |= STATE_AFTER_OBJECT


@r.token
#
# do = '('
#
def do(stream, token: r'\(', indented=False):

    state_backup = stream.state & (STATE_PARSE_INDENT | STATE_AFTER_OBJECT)
    stack_backup = stream.stack

    stream.state &= ~(STATE_PARSE_INDENT | STATE_AFTER_OBJECT)
    stream.stack = tree.Closure()
    stream.stack.indented = indented

    if indented or stream.ALLOW_INDENT_IN_PARENTHESES:

        # Only enable indentation when the closure is not parenthesized.
        # (May also affect expression separators.)
        stream.state |= STATE_PARSE_INDENT

    for item in stream:

        if item is SIG_CLOSURE_END:

            (
                not indented
                and stream.state & libparse.STATE_AT_FILE_END
                and stream.error('non-closed block at EOF')
            )

            break

        elif item in (SIG_EXPRESSION_BREAK, SIG_EXPRESSION_BR_HARD):

            stream.state &= ~STATE_AFTER_OBJECT

        elif stream.state & STATE_AFTER_OBJECT:

            # Two objects in a row should be joined with an empty operator.
            stream.repeat.appendleft(item)
          # yield from operator(stream, None)
            for _ in operator(stream, None): yield _

        else:

            stream.stack.append(item)
            stream.state |= STATE_AFTER_OBJECT

    # These SIG_CLOSURE_END are put there by `indent` when it unindents
    # for more than one level. All other stuff should have been handled.
    assert not set(stream.repeat) - {SIG_CLOSURE_END}

    if indented:

        # Don't allow the expression on the next line touch the indented block.
        yield SIG_EXPRESSION_BREAK
        # Put that stuff before closure ends yielded by `indent`.
        # (We already know there's nothing else in the queue.)
        stream.repeat.appendleft(stream.repeat.pop())

    yield stream.stack
    # If we don't do that, outer blocks will receive SIG_CLOSURE_END
    # from `indent` before they get to this block. That may have some...
    # unexpected results, such as *inner* blocks going to the *outermost*
    # expression.
    stream.repeat.appendleft(stream.repeat.pop())

    stream.state &= ~(STATE_PARSE_INDENT | STATE_AFTER_OBJECT)
    stream.state |= state_backup
    stream.stack = stack_backup


@r.token
#
# int2 = '0b', ( '0' .. '1' ) +
#
def int2(stream, token: r'0b([0-1]+)'):

    yield int(token.group(1), 2)


@r.token
#
# int8 = '0o', ( '0' .. '7' ) +
#
def int8(stream, token: r'0o([0-7]+)'):

    yield int(token.group(1), 8)


@r.token
#
# int16 = '0x', ( '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' ) +
#
def int16(stream, token: r'0x([0-9a-fA-F]+)'):

    yield int(token.group(1), 16)


@r.token
#
# number = int10, ( '.', int10 ) ?, ( [eE], [+-] ?, intpart ) ?, [jJ] ?
#
# int10  = ( '0' .. '9' ) +
#
def number(stream, token: r'([0-9]+)(?:\.([0-9]+))?(?:[eE]([+-]?[0-9]+))?(j|J)?'):

    integral, fraction, exponent, imag = token.groups()
    exponent = int(exponent or 0)
    fraction = int(fraction) / 10 ** (len(fraction) - exponent) if fraction else 0
    integral = int(integral) * 10 ** exponent
    yield (integral + fraction) * (1j if imag else 1)


@r.token
#
# string = 'r' ?, 'b' ?, ( sq_string | dq_string | sq_string_m | dq_string_m )
#
# sq_string = "'", ( '\\' ?, < any character > ) * ?, "'"
# dq_string = '"', ( '\\' ?,  < any character > ) * ?, '"'
# sq_string_m = "'''", ( '\\' ?, < any character > ) * ?, "'''"
# dq_string_m = '"""', ( '\\' ?,  < any character > ) * ?, '"""'
#
def string(stream, token: r'(b?r?)([\'"]{3}|"|\')((?:\\?.)*?)\2'):

    g = token.group(2) * (4 - len(token.group(2)))
    yield ast.literal_eval('{1}{0}{3}{0}'.format(g, *token.groups()))


@r.token
#
# string_err = "'" | '"'
#
def string_err(stream, token: r'"|\''):

    stream.error('unclosed string literal')


@r.token
#
# link = word | operator
#
def link(stream, token: r'\w+|[!$%&*-/:<-@\\^|~]+|`\w+`'):

    yield tree.Link(token.group().strip('`'))


@r.token
#
# whitespace = < whitespace >
#
def whitespace(stream, token: '\s'):

    return ()


@r.token
def error(stream, token):

    stream.error('invalid input')
