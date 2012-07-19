import re
import os.path

from .core import Compiler as r
from .. import const
from .. import parse
from ..parse import syntax


def callable(func):

    def f(self, *args):

        _, posargs, kwargs, vararg, varkwarg = syntax.call(None, *args)
        syntax.ERROR(vararg or varkwarg, const.ERR.VARARG_WITH_BUILTIN)
        return func(self, *posargs, **kwargs)

    return f


parser   = parse.r()
compiler = r()

for p in sorted(os.listdir(os.path.dirname(__file__))):

    if re.match('\d+-', p):

        __debug__ and print('--- bootstrapping', p, end='...')
        n = os.path.join(os.path.dirname(__file__), p)
        q = parser.reset(open(n).read(), n)
        c = compiler.compile(next(q))
        eval(c, {'__package__': __package__, '__file__': n})
        __debug__ and print('done')
