import sys
import argparse

from . import dg


p = argparse.ArgumentParser()
p.add_argument('file', nargs='?', help='files to parse/compile', type=argparse.FileType(), default=sys.stdin)
p.add_argument('arguments', nargs='*', help='additional arguments')
args = p.parse_args()

sys.argv = [args.file.name] + args.arguments
dg(args.file)
