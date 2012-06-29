import re
import ast
import collections

from . import tree


SIG_CLOSURE_END      = tree.Internal()
SIG_EXPRESSION_BREAK = tree.Internal()

STATE_AT_LINE_START      = 1
STATE_AT_FILE_START      = 2
STATE_AT_FILE_END        = 4
STATE_CAN_POP_FROM_STACK = 8
STATE_INDENT_IS_ALLOWED  = 16

ParseLocation = collections.namedtuple('ParseLocation', 'start, end, filename')
ParseError    = type('ParseError', (SyntaxError,), {})


class Parser (collections.Iterator):

  ### OPTIONS

    # Whether to allow expression breaks in parenthesized closures.
    #
    #    False:: only insert breaks in indented blocks
    #    True::  enable breaks in any type of closures
    #
    ALLOW_BREAKS_IN_PARENTHESES = False

    # Whether operators accept variable amount of arguments.
    #
    #    False:: `a + b + c` <=> `+ (+ a b) c`
    #    True::  `a + b + c` <=> `+ a b c`
    #
    JOIN_OPERATOR_CALLS = False

    # Constants used by default :func:`has_priority` implementation.
    OPERATOR_RIGHT_FIXITY = ()       # a container of operators w/ right fixity
    OPERATOR_PRECEDENCE_DEFAULT = 0  # default priority
    OPERATOR_PRECEDENCE = {}         # priority override

    # Whether an operator's priority is higher than the other one's.
    #
    # :param in_relation_to: operator to the left.
    #
    def has_priority(self, operator, in_relation_to):

        p1 = self.OPERATOR_PRECEDENCE.get(operator,       self.OPERATOR_PRECEDENCE_DEFAULT)
        p2 = self.OPERATOR_PRECEDENCE.get(in_relation_to, self.OPERATOR_PRECEDENCE_DEFAULT)
        return p1 >= p2 + (operator not in self.OPERATOR_RIGHT_FIXITY)

  ### INTERNAL PARSER STUFF

    # Convert primitive Python types to objects.
    #
    # This allows to store the position on them.
    #
    TYPE_MAPPING = {
        str:     type('str',     (str,),     {}),
        int:     type('int',     (int,),     {}),
        float:   type('float',   (float,),   {}),
        complex: type('complex', (complex,), {}),
    }

    def __init__(self):

        super().__init__()

        self.tokens = [
            (
                h.__annotations__.get(h.__code__.co_varnames[1], 0),
                re.compile(h.__annotations__.get(h.__code__.co_varnames[0], '.'), re.DOTALL),
                h
            ) for h in (
                bof, eof, separator, comment, indent, end,
                operator, do, number, string, link,
            )
        ]

    def parse(self, *args, **kwargs):

        return next(self.reset(*args, **kwargs))

    def reset(self, input, filename='<string>'):

        self.buffer = input
        self.ecache = self.buffer  # FIXME wtf?
        self.lineno = 1
        self.charno = 1
        self.offset = 0
        self.pstack = collections.deque()
        self.repeat = collections.deque()
        self.state = STATE_AT_LINE_START | STATE_AT_FILE_START
        self.filename = filename
        self.stack = None
        self.indent = collections.deque([0])
        return self

    def error(self, description, after=False):

        raise ParseError(
            description,
            (
                self.filename,
                self.lineno if after else self.pstack[-1][1],
                self.charno if after else self.pstack[-1][2],
                self.ecache[self.ecache.rfind('\n', 0, self.offset if after else self.pstack[-1][0]) + 1:],
            )
        )

    def located(self, q):

        q = self.TYPE_MAPPING[type(q)](q) if type(q) in self.TYPE_MAPPING else q
        q.reparse_location = ParseLocation(
            self.pstack[-1],
            (self.offset, self.lineno, self.charno),
            self.filename
        )
        return q

    def __next__(self):

        while not self.repeat:

            # Do not raise StopIteration, allow handlers
            # to parse EOF nicely instead.
            self.state |= not self.buffer and STATE_AT_FILE_END

            self.pstack.append((self.offset, self.lineno, self.charno))

            for st, rx, f in self.tokens:

                match = self.state & st == st and rx.match(self.buffer)

                if match:

                    self.state &= ~STATE_AT_FILE_START
                    self.state &= ~STATE_AT_LINE_START
                    self.state |= match.group().endswith('\n') and STATE_AT_LINE_START

                    self.offset += match.end()
                    self.lineno += match.group().count('\n')
                    self.charno  = 1 + match.end() - (match.group().rfind('\n') + 1 or -self.charno + 1)
                    self.buffer  = self.buffer[match.end():]
                    self._token  = f

                    tk = f(match, self)
                    tk is None or self.repeat.appendleft(self.located(tk))
                    break

            else:

                self.error('invalid input')

            self.pstack.pop()

        return self.repeat.popleft()

    # A compiler function for `interactive`, similar to `code.compile_command`.
    #
    # :param code: what to compile.
    #
    # :return: None if `code` is incomplete, `parse(code)` otherwise.
    #
    def compile_command(self, code):

        try:

            res = self.parse(code, '<stdin>')

        except ParseError as e:

            if e.args[0] == 'non-closed block at EOF':

                return None

            raise

        # Search for incomplete operator expressions.
        expr = res

        while expr and isinstance(expr[-1], tree.Expression) and len(expr[-1]) > 2:
        
            expr = expr[-1]

        return None if res and not code.endswith('\n') and (
            expr and isinstance(expr[-1], tree.Expression) or
            code[code.rfind('\n') + 1] in ' \t'
        ) else res


#
# bof = BOF
#
def bof(token: r'', stream: STATE_AT_FILE_START):

    return do(None, stream)


#
# do = '('
#
def do(token: r'\(', stream):

    STATE_INDENT_BACKUP = stream.state & STATE_INDENT_IS_ALLOWED

    # Reset the parser state.
    stream.state &= ~STATE_INDENT_IS_ALLOWED
    stream.state &= ~STATE_CAN_POP_FROM_STACK
    stream.stack, stack_backup = tree.Closure(), stream.stack

    # Only enable indentation when the closure is not parenthesized.
    # Note that this also disables expression chaining inside parentheses,
    # unless ALLOW_BREAKS_IN_PARENTHESES is true.
    stream.state |= not token and STATE_INDENT_IS_ALLOWED

    for item in stream:

        if item is SIG_CLOSURE_END:

            (
                not stream.state & STATE_INDENT_IS_ALLOWED
                and stream.state & STATE_AT_FILE_END
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
    return result


#
# end = ')'
#
def end(token: r'[^\S\n]*\)', stream):

    return SIG_CLOSURE_END


#
# eof = EOF
#
def eof(token: r'', stream: STATE_AT_FILE_END):

    return SIG_CLOSURE_END


#
# separator = '\n' | ';'
#
def separator(token: r'\s*(?:\n|;[^\S\n]*)', stream):

    if stream.state & STATE_INDENT_IS_ALLOWED or stream.ALLOW_BREAKS_IN_PARENTHESES:

        # Expression chaining is enabled, insert an expression break.
        return SIG_EXPRESSION_BREAK

    elif token and ';' in token.group():

        # Expression chaining is disabled and the programmer
        # has explicitly requested a break.
        stream.error('can\'t chain expressions here')

#
# comment = '#', < anything but '\n' > *
#
def comment(token: r'\s*#[^\n]*', stream):

    pass


#
# indent = ^ ( ' ' | '\t' ) *
#
def indent(token: r'[ \t]*', stream: STATE_AT_LINE_START):

    if not stream.state & STATE_INDENT_IS_ALLOWED:

        # Indent is not allowed, yet we need to consume the whitespace.
        return

    indent = len(token.group()) + token.group().count('\t') * 3  # 1 tab = 4 spaces

    if indent > stream.indent[-1]:

        stream.indent.append(indent)
        return do(None, stream)

    while indent != stream.indent.pop():

        stream.repeat.append(SIG_CLOSURE_END)
        stream.indent or stream.error('no matching indentation level', after=True)

    # Don't allow further expressions touch the indented block.
    stream.repeat and stream.repeat.append(SIG_EXPRESSION_BREAK)
    stream.indent.append(indent)


#
# operator = non_empty_operator | ''
#
# non_empty_operator = < some punctuation > + | ( '`', word, '`' )
# word = ( < letter > | < digit > | < underscore > ) +
#
def operator(token: r'\s*(`[\w\d_]+`|[!$%&*-/:<-@\\^|~]*)[^\S\n]*', stream: STATE_CAN_POP_FROM_STACK):

    op = tree.Link(token.group(1).strip('`'))
    op = stream.located(op)

    stream.state &= ~STATE_CAN_POP_FROM_STACK

    rhs = next(_ for _ in stream if _ is not SIG_EXPRESSION_BREAK)
    rhsless = isinstance(rhs, tree.Internal)
    rhsless and stream.repeat.append(rhs)

    stream.state |= STATE_CAN_POP_FROM_STACK

    # Find the closest left-hand statement that either isn't
    # an operator expression or has bigger priority than this operator.
    lhs = stream.stack
    can_join = not rhsless and op not in stream.OPERATOR_RIGHT_FIXITY

    while isinstance(lhs[-1], tree.Expression):

        if stream.JOIN_OPERATOR_CALLS and can_join and lhs[-1][0] == op:

            return lhs[-1].append(rhs)

        if stream.has_priority(op, lhs[-1][0]):

            lhs = lhs[-1]

        else:

            break

    e = tree.Expression((op, lhs.pop()) if rhsless else (op, lhs.pop(), rhs))
    lhs.append(stream.located(e))


#
# number = '-' ?, ( int10, fraction10 ?) | ( int10, 'x', int36, fraction36 ? ), exponent ?, 'J' ?
#
# int10 = < any digit > +
# int36 = < any lowercase alphanumeric character > +
# fraction10 = '.', int10
# fraction36 = '.', int36
# exponent  = 'E', sign ?, int10
#
def number(token: r'(-)?(?:(\d+)x)?((?(2)[\da-z]+|\d+))(?:\.((?(2)[\da-z]+|\d+)))?(?:E([+-]\d+))?(J)?', stream):

    sign, base, integer, fraction, exponent, imag = token.groups()
    base     = int(base     or 10)
    exponent = int(exponent or 0)
    fraction = int(fraction, base) / base ** (len(fraction) - exponent) if fraction else 0
    integer  = int(integer,  base) * base ** exponent
    return (integer + fraction) * (-1 if sign else 1) * (1j if imag else 1)


#
# string = 'r' ?, 'b' ?, sq_string | dq_string
#
# sq_string = "'", ( '\\' ?, < any character > ) * ?, "'"
# dq_string = '"', ( '\\' ?,  < any character > ) * ?, '"'
#
def string(token: r'(b?r?)("|\')((?:\\?.)*?)\2', stream):

    return ast.literal_eval('{0}{1}{1}{1}{2}{1}{1}{1}'.format(*token.groups()))


#
# link = word | non_empty_operator
#
def link(token: r'[\w\d_]+|[!$%&*-/:<-@\\^|~]+|`[\w\d_]+`', stream):

    return tree.Link(token.group())

