import dg


class Parser (dg.Parser):

    OPERATOR_RIGHT_FIXITY = ('**', ':', '$', '->', '=')
    OPERATOR_PRECEDENCE_DEFAULT = -7
    OPERATOR_PRECEDENCE = {
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
    }


