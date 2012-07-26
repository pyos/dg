import glob
import os.path
import marshal

from .core import Compiler as r
from .. import parse


parser   = parse.r()
compiler = r()

container = os.path.join(os.path.dirname(__file__), 'bootstrap')
compiled  = os.path.join(container, 'bootstrap.pyc')
all_files = sorted(glob.glob(os.path.join(container, '*.dg')))


try:

    if os.stat(compiled).st_mtime < max(os.stat(p).st_mtime for p in all_files):

        raise Exception

    for c in marshal.load(open(compiled, 'rb')):

        eval(c, {'__package__': __package__})

except Exception as e:

    cs = (compiler.compile(parser.parse(open(p).read(), p)) for p in all_files)
    cs = [_ for _ in cs if eval(_, {'__package__': __package__}) or True]
    marshal.dump(cs, open(compiled, 'wb'))
