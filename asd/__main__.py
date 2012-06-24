import sys
import operator

import dg
import interactive

from . import asd


class Interactive (interactive.Interactive):

    PARSER   = dg.Parser()
    COMPILER = asd.Compiler()
    GLOBALS  = {
        # Runtime counterparts of some stuff in `Compiler.builtins`.

        '$': lambda f, x: f(x)
      , ':': lambda f, x: f(x)

        # TODO various operators
      , '+':  operator.add
      , '-':  operator.sub
      , '!!': operator.getitem
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
