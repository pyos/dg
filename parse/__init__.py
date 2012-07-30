import ast

from . import core
from . import tree
from .core import Parser as r

SIG_SET_END          = tree.Internal()
SIG_LIST_END         = tree.Internal()
SIG_CLOSURE_END      = tree.Internal()
SIG_EXPRESSION_BREAK = tree.Internal()

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

        yield SIG_CLOSURE_END
        stream.indent or stream.error('no matching indentation level', after=True)

    stream.indent.append(indent)


@r.token(r'(`\w+`|[!$%&*+\--/:<-@\\^|~]+|,+|if|unless|else|and|or)', STATE_AFTER_OBJECT)
#
# operator = < ascii punctuation > + | ',' + | ( '`', word, '`' ) | word_op | '\n'
#
# word = ( < alphanumeric > | '_' ) +
# word_op = 'if' | 'else' | 'unless' | 'or' | 'and'
#
def operator(stream, token):

    op = token if isinstance(token, str) else token.group(1).strip('`')
    return operator_(stream, stream.located(tree.Link(op)))


def operator_(stream, op):

    stream.state &= ~STATE_AFTER_OBJECT

    br  = False
    lhs = [stream.stuff]
    rhs = next(stream)
    rhsless = False
    rhsbound = False

    while rhs is SIG_EXPRESSION_BREAK:

        br  = True
        rhs = next(stream)  # Skip soft breaks.

    if isinstance(rhs, tree.Internal):

        # `(a R)`
        stream.repeat.appendleft(rhs)
        rhsless = True

    elif br and op != '\n' and not getattr(rhs, 'indented', False):

        # The operator was followed by something other than an object or
        # an indented block.
        stream.repeat.appendleft(rhs)
        stream.repeat.appendleft(SIG_EXPRESSION_BREAK)
        rhsless = True

    elif isinstance(rhs, tree.Link) and not hasattr(rhs, 'closed') and rhs.operator:

        # `a R Q b` <=> `(a R) Q b` if R is prioritized over Q,
        # `a R (Q b)` otherwise.
        rhsless = rhsbound = stream.has_priority(op, rhs)

    if rhsless and (op == '\n' or op == ''):

        # Chaining a single expression doesn't make sense.
        return

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
        e = tree.Expression((op, lhs.pop()) if rhsless else (op, lhs.pop(), rhs))

        if not lhs:

            # That was a fake expression, appending to it is futile.
            stream.stuff = stream.located(e)

        else:

            lhs.append(stream.located(e))

    stream.state |= STATE_AFTER_OBJECT

    if rhsbound:

      # yield from operator_(rhs)
        for _ in operator_(stream, rhs): yield _


@r.token('\(')
#
# do = '('
#
def do(stream, token, indented=False, closed=True, until=SIG_CLOSURE_END):

    state_backup = stream.state & STATE_AFTER_OBJECT
    stuff_backup = stream.stuff

    stream.state &= ~STATE_AFTER_OBJECT
    stream.stuff = None

    for item in stream:

        if not indented and stream.state & core.STATE_AT_FILE_END:

            stream.error('mismatched parentheses')

        if item is until:

            break

        elif item is SIG_EXPRESSION_BREAK and not stream.state & STATE_AFTER_OBJECT:

            # Ignore line feeds directly following an opening parentheses.
            pass

        elif item is SIG_EXPRESSION_BREAK:

            # Two expressions in a row should be joined with a line feed operator.
          # yield from operator(stream, None)
            for _ in operator(stream, '\n'): yield _

        elif isinstance(item, tree.Internal):

            stream.error('invalid indentation or mismatched parentheses')

        elif stream.state & STATE_AFTER_OBJECT:

            # Two objects in a row should be joined with an empty operator.
            stream.repeat.appendleft(item)
          # yield from operator(stream, None)
            for _ in operator(stream, ''): yield _

        else:

            stream.stuff = item
            stream.state |= STATE_AFTER_OBJECT

    # These SIG_CLOSURE_END are put there by `indent` when it unindents
    # for more than one level. All other stuff should have been handled.
    assert not set(stream.repeat) - {SIG_CLOSURE_END}

    if isinstance(stream.stuff, tree.Expression) and closed is not None:

        # Note that constants cannot be marked as indented/closed.
        # The only objects those marks make sense for are expressions, though.
        stream.stuff.indented = indented
        stream.stuff.closed   = closed

    if indented:

        # Further expressions should not touch this block.
        stream.repeat.appendleft(SIG_EXPRESSION_BREAK)

    # If we use yield instead, outer blocks will receive SIG_CLOSURE_END
    # from `indent` before they get to this block. That may have some...
    # unexpected results, such as *inner* blocks going to the *outermost*
    # expression.
    stream.repeat.appendleft(stream.located(stream.stuff))

    stream.state &= ~STATE_AFTER_OBJECT
    stream.state |= state_backup
    stream.stuff = stuff_backup


@r.token(r'\[')
#
# list_do = '['
#
def list_do(stream, token):

  # yield from do(stream, token, closed=None, until=SIG_LIST_END)
    for _ in do(stream, token, closed=None, until=SIG_LIST_END): yield _
    e = tree.Expression([stream.located(tree.Link('[]')), next(stream)])
    e.closed = True
    yield e


@r.token(r'\{')
#
# set_do = '{'
#
def set_do(stream, token):

  # yield from do(stream, token, closed=None, until=SIG_LIST_END)
    for _ in do(stream, token, closed=None, until=SIG_LIST_END): yield _
    e = tree.Expression([stream.located(tree.Link('{}')), next(stream)])
    e.closed = True
    yield e


@r.token(r'', core.STATE_AT_FILE_END)
@r.token(r'\)')
#
# end = ')' | $
#
def end(stream, token):

    yield SIG_CLOSURE_END


@r.token(r'\]')
#
# list_end = ']'
#
def list_end(stream, token):

    yield SIG_LIST_END


@r.token(r'\}')
#
# set_end = '}'
#
def list_end(stream, token):

    yield SIG_SET_END


@r.token(r'\s*\n')
#
# soft_break = '\n'
#
def soft_break(stream, token):

    yield SIG_EXPRESSION_BREAK


@r.token(r'\s*#[^\n]*')
#
# comment = '#', < anything but line feed >
#
def comment(stream, token):

    return ()


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
# number = int10, ( '.', int10 ) ?, ( [eE], [+-] ?, int10 ) ?, [jJ] ?
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

    stream.error('mismatched quote')


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
