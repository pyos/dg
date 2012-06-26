import sys
import operator

import dg
import interactive

from . import compiler


class Interactive (interactive.Interactive):

    PARSER   = dg.Parser()
    COMPILER = compiler.Compiler()
    GLOBALS  = {
        # Runtime counterparts of some stuff in `Compiler.builtins`.

        '$': lambda f, *xs: f(*xs)
      , ':': lambda f, *xs: f(*xs)

      , '<':  operator.lt
      , '<=': operator.le
      , '==': operator.eq
      , '!=': operator.ne
      , '>':  operator.gt
      , '>=': operator.ge
      , 'is': operator.is_
      , 'in': lambda a, b: a in b

      , 'not': operator.not_
      , '~':  operator.invert
      , '+':  compiler.varary(operator.pos, operator.add)
      , '-':  compiler.varary(operator.neg, operator.sub)
      , '*':  operator.mul
      , '**': operator.pow
      , '/':  operator.truediv
      , '//': operator.floordiv
      , '%':  operator.mod
      , '!!': operator.getitem
      , '&':  operator.and_
      , '^':  operator.xor
      , '|':  operator.or_
      , '<<': operator.lshift
      , '>>': operator.rshift
    }

    def compile(self, code):

        q = self.PARSER.compile_command(code)
        q = q if q is None else self.COMPILER.compile(q, name='<module>', single=True)
        return q

    def run(self, ns):

        q = self.PARSER.parse(sys.stdin, '<stdin>')
        q = self.COMPILER.compile(q, name='<module>')
        return self.eval(q, ns)


Interactive().shell(__name__, Interactive.GLOBALS)
