import sys

from . import parse
from . import compile
from . import runtime
from .interactive import Interactive


class Interactive (Interactive):

    def compile(self, code):

        q = parse.r.compile_command(code)
        q = q if q is None else compile.r(q, single=True)
        return q

    def run(self, ns):

        q = parse.r(sys.stdin.read(), '<stdin>')
        q = compile.r(q)
        return self.eval(q, ns)


Interactive().shell(__name__)
