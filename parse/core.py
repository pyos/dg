import collections

from . import tree
from . import libparse


class Parser (libparse.Parser):

    # Whether to use indentation to delimit blocks in parentheses
    #
    # Requires ALLOW_BREAKS_IN_PARENTHESES
    #
    #    on   indent @ unindent
    #    off  any indent in parentheses is ignored
    #
    ALLOW_INDENT_IN_PARENTHESES = True

    # Whether to allow expression breaks in parenthesized closures
    #
    #    on   parentheses are syntactically equivalent to indentation
    #    off  parentheses contain a single expression
    #
    ALLOW_BREAKS_IN_PARENTHESES = True or ALLOW_INDENT_IN_PARENTHESES

    OPERATOR_RIGHT_FIXITY = {'**', ':', '$', '->', '=', 'if', 'unless', 'else'}
    OPERATOR_PRECEDENCE = lambda self, i, q={
      # Scope resolution
        '.':   0,
      # Keyword arguments
        ':':  -1,
      # Function application
         '':  -2,
      # Container subscription
       '!!':  -3,
      # Math
       '**':  -4,
        '*':  -5,
        '/':  -5,
       '//':  -5,
        '%':  -5,
        '+':  -6,
        '-':  -6,
      # Comparison
        '<':  -8,
       '<=':  -8,
       '>=':  -8,
        '>':  -8,
       '==':  -9,
       '/=':  -9,
      # Binary operations
       '<<': -10,
       '>>': -10,
        '&': -11,
        '^': -12,
        '|': -13,
      # Logic
       '&&': -14,
       '||': -15,
      # Low-priority binding
        '$': -16,
      # Function definition
       '->': -17,
      # Sequential evaluation
        ',': -18,
      # Assignment
        '=': -19,
      # Conditionals
       'if': -20,
   'unless': -20,
     'else': -21,
    }.get: q(i, -7)  # Default

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.stack = None
        self.indent = collections.deque([0])

    # Whether an operator's priority is higher than the other one's.
    #
    # :param in_relation_to: operator to the left.
    #
    def has_priority(self, operator, in_relation_to):

        if operator == '->':

            # `a R b -> c` should always parse as `a R (b -> c)`.
            #
            # Note that this means that for `a R b -> c Q d` to parse
            # as `a R (b -> (c Q d))` this method should return True for both
            # (R, Q) and ('->', Q). Otherwise, the output is `a R (b -> c) Q d`.
            # That's not of concern when doing stuff like `f = x -> print "yay"`
            # 'cause `=` has the lowest possible priority.
            #
            # What               How                 Why
            # -----------------------------------------------------------
            # a b -> c d         a (b -> c) d        ('', '') -> False
            # a = b -> c = d     a = (b -> c) = d    ('->', '=') -> False
            # a $ b -> c $ d     a $ (b $ (c $ d))   everything's True
            # a b -> c.d         a (b -> (c.d))      also True
            #
            return True

        p1 = self.OPERATOR_PRECEDENCE(operator)
        p2 = self.OPERATOR_PRECEDENCE(in_relation_to)
        return p1 + (operator in self.OPERATOR_RIGHT_FIXITY) > p2

    @classmethod
    # A compiler function for `interactive`, similar to `code.compile_command`.
    #
    # :param code: what to compile.
    #
    # :return: None if `code` is incomplete, `parse(code)` otherwise.
    #
    def compile_command(cls, code):

        try:

            res = cls(code, '<stdin>')

        except SyntaxError as e:

            if e.args[0] in ('non-closed block at EOF', 'unclosed string literal'):

                # The code is incomplete by definition if there are
                # unmatched parentheses or quotes in it.
                return None

            # Other errors are irrepairable.
            raise

        # Search for incomplete operator expressions.
        expr = res

        while expr and isinstance(expr[-1], tree.Expression) and len(expr[-1]) > 2:

            expr = expr[-1]

        return None if (
            res
            and not code.endswith('\n')
            and (
                # If this condition is met, then `len(expr[-1])` must've been 2.
                expr and isinstance(expr[-1], tree.Expression)
                or code[code.rfind('\n') + 1] == ' '
            )
        ) else res

