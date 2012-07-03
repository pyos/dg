import ast

from . import core
from . import tree
from . import libparse

SIG_CLOSURE_END       = tree.Internal()
SIG_EXPRESSION_BREAK  = tree.Internal()

STATE_CAN_POP_FROM_STACK = libparse.STATE_CUSTOM << 0
STATE_INDENT_IS_ALLOWED  = libparse.STATE_CUSTOM << 1

r = core.Parser.make()


@r.token
#
# bof = ^^
#
def bof(stream: libparse.STATE_AT_FILE_START, token: r''):

    stream.state |= libparse.STATE_AT_LINE_START
    return do(stream, None)


@r.token
#
# separator = '\n' | ';'
#
def separator(stream, token: r'\s*(?:\n|;[^\S\n]*)'):

    ok = stream.state & STATE_INDENT_IS_ALLOWED or stream.ALLOW_BREAKS_IN_PARENTHESES
    ok or ';' not in token.group() or stream.error('can\'t chain expressions here')

    if ok:

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
def indent(stream: libparse.STATE_AT_LINE_START, token: r' *'):

    if not stream.state & STATE_INDENT_IS_ALLOWED:

        # Indent is not allowed, yet we need to consume the whitespace.
        # FIXME whitespace should be handled by some other token handler.
        return

    indent = len(token.group())

    if indent > stream.indent[-1]:

        stream.indent.append(indent)
      # yield from do(stream, None)
        for _ in do(stream, None): yield _
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
def end(stream, token: r'[^\S\n]*\)'):

    yield SIG_CLOSURE_END


@r.token
#
# operator = non_empty_operator | ''
#
# non_empty_operator = < some punctuation > + | ( '`', word, '`' )
# word = ( < alphanumeric > | '_' ) +
#
def operator(stream: STATE_CAN_POP_FROM_STACK, token: r'\s*(`\w+`|[!$%&*-/:<-@\\^|~]*)[^\S\n]*\n*'):

    stream.state &= ~STATE_CAN_POP_FROM_STACK

    yield tree.Link(token.group(1).strip('`'))

    op  = stream.repeat.pop()
    lhs = stream.stack
    rhs = next(stream)

    # true   `lhs R;` or `(lhs R)`
    # false  `lhs R rhs`
    rhsless = isinstance(rhs, tree.Internal)
    rhsless and stream.repeat.append(rhs)

    while isinstance(lhs[-1], tree.Expression) and stream.has_priority(op, lhs[-1][0]):

        lhs = lhs[-1]

    # `R`         <=> `Op R`
    # `R rhs`     <=> `Call (Link R) (Link rhs)`
    # `lhs R`     <=> `Op R (Link lhs)`
    # `lhs R rhs` <=> `Op R (Link lhs) (Link rhs)`
    yield tree.Expression((op, lhs.pop()) if rhsless else (op, lhs.pop(), rhs))
    lhs.append(stream.repeat.pop())

    stream.state |= STATE_CAN_POP_FROM_STACK


@r.token
#
# do = '('
#
def do(stream, token: r'\('):

    STATE_INDENT_BACKUP = stream.state & STATE_INDENT_IS_ALLOWED

    # Reset the parser state.
    stream.state &= ~STATE_INDENT_IS_ALLOWED
    stream.state &= ~STATE_CAN_POP_FROM_STACK
    stream.stack, stack_backup = tree.Closure(), stream.stack

    # Only enable indentation when the closure is not parenthesized.
    # (May also affect expression separators.)
    stream.state |= (not token or stream.ALLOW_INDENT_IN_PARENTHESES) and STATE_INDENT_IS_ALLOWED

    for item in stream:

        if item is SIG_CLOSURE_END:

            (
                token
                and stream.state & libparse.STATE_AT_FILE_END
                and stream.error('non-closed block at EOF')
            )

            break

        if item is SIG_EXPRESSION_BREAK:

            stream.state &= ~STATE_CAN_POP_FROM_STACK
            continue

        stream.stack.append(item)
        stream.state |= STATE_CAN_POP_FROM_STACK

    stream.stack, result = stack_backup, stream.stack
    stream.state &= ~STATE_INDENT_IS_ALLOWED
    stream.state |=  STATE_INDENT_BACKUP

    yield result

    if not token:

        # Don't allow the expression on the next line touch the indented block.
        yield SIG_EXPRESSION_BREAK


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
# string = 'r' ?, 'b' ?, sq_string | dq_string
#
# sq_string = "'", ( '\\' ?, < any character > ) * ?, "'"
# dq_string = '"', ( '\\' ?,  < any character > ) * ?, '"'
#
def string(stream, token: r'(b?r?)("|\')((?:\\?.)*?)\2'):

    yield ast.literal_eval('{0}{1}{1}{1}{2}{1}{1}{1}'.format(*token.groups()))


@r.token
#
# string_err = "'" | '"'
#
def string_err(stream, token: r'"|\''):

    stream.error('unclosed string literal')


@r.token
#
# link = word | non_empty_operator
#
def link(stream, token: r'\w+|[!$%&*-/:<-@\\^|~]+|`\w+`'):

    yield tree.Link(token.group())


@r.token
def error(stream, token):

    stream.error('invalid input')

