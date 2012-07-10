import sys
import argparse

from . import parse
from . import compile
from . import runtime
from .interactive import Interactive


class Interactive (Interactive):

    def compile(self, code):

        q = parse.r.compile_command(code)
        return q if q is None else compile.r().compile(q, name='<module>')

    def eval(self, q, ns):

        self.displayhook(eval(q, ns))

    def traceback(self, trace):

        return super().traceback(trace)[sys.stdin.isatty() or 4:]

    def run(self, ns):

        q = parse.r(sys.stdin.read(), sys.stdin.name)
        q = compile.r().compile(q, name='<module>')
        return eval(q, ns)


parser = argparse.ArgumentParser()
parser.add_argument('file', nargs='?', help='files to parse/compile', type=argparse.FileType())
parser.add_argument('arguments', nargs='*', help='additional arguments')
args = parser.parse_args()

sys.argv = [args.file.name if args.file else '-'] + args.arguments
sys.stdin = args.file or sys.stdin

Interactive().shell(__name__)
