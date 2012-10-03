import os
import imp
import marshal

from .core import Compiler as r
from .. import parse

### Public API

it = r.compile
fd = lambda fd, name='<stream>': it(parse.fd(fd, name))

### Bootstrap

for f in [
       'shortcuts.dg'
  , 'conditionals.dg',      'unary.dg'
  ,       'binary.dg', 'comparison.dg'
  ,      'inherit.dg',     'switch.dg', 'where.dg'
  ,        'loops.dg',     'unsafe.dg',  'with.dg', 'yield.dg'
  ,      'imphook.dg', 'functional.dg'
]:
    f = os.path.join(os.path.join(__path__[0], 'bootstrap'), f)
    q = imp.cache_from_source(f)

    try:

        c = os.stat(q).st_mtime > os.stat(f).st_mtime and marshal.load(open(q, 'rb'))

    except Exception:

        c = None

    if not c:

        c = fd(open(f))
        os.makedirs(os.path.dirname(q), exist_ok=True)
        marshal.dump(c, open(q, 'wb'))

    eval(c, {'__package__': __package__})
