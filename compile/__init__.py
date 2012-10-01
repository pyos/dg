import imp
import os.path
import marshal

from . import core
from . import bootstrap
from .. import parse

# Public API
r  = core.Compiler
it = core.Compiler.compile
# End of public API

for f in [
       'shortcuts.dg'
  , 'conditionals.dg',      'unary.dg'
  ,       'binary.dg', 'comparison.dg'
  ,      'inherit.dg',     'switch.dg', 'where.dg'
  ,        'loops.dg',     'unsafe.dg',  'with.dg', 'yield.dg'
  ,      'imphook.dg', 'functional.dg'
]:
    f = os.path.join(bootstrap.__path__[0], f)
    q = imp.cache_from_source(f)

    try:

        c = os.stat(q).st_mtime > os.stat(f).st_mtime and marshal.load(open(q, 'rb'))

    except Exception:

        c = None

    if not c:

        c = it(parse.fd(open(f)))
        os.makedirs(os.path.dirname(q), exist_ok=True)
        marshal.dump(c, open(q, 'wb'))

    eval(c, {'__package__': __package__})
