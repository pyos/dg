import sys
import argparse

from . import parse
from . import compile

from .runtime.shell import Interactive


parser = argparse.ArgumentParser()
parser.add_argument('file', nargs='?', help='files to parse/compile', type=argparse.FileType(), default=sys.stdin)
parser.add_argument('arguments', nargs='*', help='additional arguments')
args = parser.parse_args()

sys.argv = [args.file.name if args.file else '-'] + args.arguments
Interactive(args.file).shell()
