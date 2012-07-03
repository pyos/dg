import sys
import operator

from . import parse
from .compiler.core import Compiler, varary
from .interactive import Interactive


class Interactive (Interactive):

    COMPILER = Compiler()
    GLOBALS  = {
        # Runtime counterparts of some stuff in `Compiler.builtins`.

        '$': lambda f, *xs: f(*xs)
      , ':': lambda f, *xs: f(*xs)
      , ',': lambda a, *xs: (a,) + xs

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
      , '+':  varary(operator.pos, operator.add)
      , '-':  varary(operator.neg, operator.sub)
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

        q = parse.r.compile_command(code)
        q = q if q is None else self.COMPILER.compile(q, name='<module>', single=True)
        return q

    def run(self, ns):

        q = parse.r(sys.stdin.read(), '<stdin>')
        q = self.COMPILER.compile(q, name='<module>')
        return self.eval(q, ns)


Interactive().shell(__name__, Interactive.GLOBALS)
