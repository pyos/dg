import os.path
import marshal

from .core import Compiler as r
from .. import const
from .. import parse
from ..parse import syntax

def callable(func):

    def f(self, *args):

        _, posargs, kwargs, vararg, varkwarg = syntax.call(None, *args)
        (vararg or varkwarg) and const.ERR.VARARG_WITH_BUILTIN
        return func(self, *posargs, **kwargs)

    return f


parser   = parse.r()
compiler = r()

container = os.path.join(os.path.dirname(__file__), 'bootstrap')
preloaded = os.path.join(container, 'bootstrap.pyc')
all_files = sorted(filter(lambda q: q.endswith('.dg'), os.listdir(container)))
unparsed  = [os.path.join(container, p) for p in all_files]

# If the precompiled file is up to date, load it instead.
modified = max(os.stat(p).st_mtime for p in unparsed)
compiled = os.stat(preloaded).st_mtime if os.path.exists(preloaded) else float('-inf')

try:

    cs = compiled >= modified and marshal.load(open(preloaded, 'rb'))

except Exception:

    cs = False

else:

    if cs:

        for c in cs:

            eval(c, {'__package__': __package__, '__file__': '<frozen>'})

if cs is False:

    codes = []

    for p in unparsed:

        c = compiler.compile(parser.parse(open(p).read(), p))
        eval(c, {'__package__': __package__, '__file__': p})
        codes.append(c)

    marshal.dump(codes, open(preloaded, 'wb'))
