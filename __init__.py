import sys
import marshal
import os.path


if not hasattr(sys, 'implementation'):
    raise ImportError('Python 3.3 or newer is required')

PY_INIT    = True
PY_TAG     = sys.implementation.cache_tag
PY_VERSION = sys.hexversion

if PY_TAG is None:
    # Never seen this to be true, but Python documentation
    # mentions that it's possible.
    raise ImportError('cannot load the bundle since module caching is disabled')

__file__ = os.path.join(__path__[0], 'bundle', PY_TAG + '.dgbundle')

try:
    with open(__file__, 'rb') as _fd:
        for _c in marshal.load(_fd):
            eval(_c)
except IOError:
    raise ImportError('`{}.dgbundle` is inaccessible'.format(PY_TAG))
except Exception:
    raise ImportError('`{}.dgbundle` is corrupt'.format(PY_TAG))
