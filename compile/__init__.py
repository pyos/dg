import imp
import os.path
import marshal

from .core import Compiler as r

from . import bootstrap
from .. import parse


parser    = parse.r()
compiler  = r()
container = os.path.dirname(bootstrap.__file__)

for f in [
       'shortcuts.dg'
  , 'conditionals.dg',      'unary.dg'
  ,       'binary.dg', 'comparison.dg'
  ,      'inherit.dg',     'switch.dg', 'where.dg'
  ,        'loops.dg',     'unsafe.dg',  'with.dg', 'yield.dg'
  ,      'imphook.dg'
]:
    f = os.path.join(container, f)
    q = imp.cache_from_source(f)

    try:

        c = os.stat(q).st_mtime > os.stat(f).st_mtime and marshal.load(open(q, 'rb'))

    except Exception:

        c = None

    if not c:

        c = compiler.compile(parser.parse(open(f).read(), f))
        os.makedirs(os.path.dirname(q), exist_ok=True)
        marshal.dump(c, open(q, 'wb'))

    eval(c, {'__package__': __package__})
