import sys
import argparse

from . import parse
from . import compile
from . import runtime
from .interactive import Interactive


class Interactive (Interactive):

    def __init__(self, args):

        super().__init__()

        self.args = args

    def traceback(self, trace):

        # When running in non-interactive mode, strip the first 4 lines.
        # These correspond to stuff in this module.
        return super().traceback(trace)[4 * (not sys.stdin.isatty()):]

    def compile(self, code):

        q = parse.r.compile_command(code)
        q = q if q is None else compile.r(q, name='<module>', single=True)
        return q

    def run(self, ns):

        q = parse.r(sys.stdin.read(), sys.stdin.name)
        q = compile.r(q, name='<module>')
        return self.eval(q, ns)


parser = argparse.ArgumentParser()
parser.add_argument('file', nargs='?', help='files to parse/compile', type=argparse.FileType())
parser.add_argument('arguments', nargs='*', help='additional arguments')
args = parser.parse_args()

sys.argv = [args.file.name if args.file else '-'] + args.arguments
sys.stdin = args.file or sys.stdin

Interactive(args).shell(__name__)
