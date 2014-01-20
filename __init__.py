import sys
import marshal
import os.path


if not hasattr(sys, 'implementation'):
    raise ImportError('Python 3.3 or newer is required')

if sys.implementation.cache_tag is None:
    raise ImportError('cannot load the bundle since module caching is disabled')

PY_TAG      = sys.implementation.cache_tag
PY_VERSION  = sys.hexversion
BUNDLE_DIR  = os.path.join(__path__[0], 'bundle')
BUNDLE_FILE = os.path.join(BUNDLE_DIR, PY_TAG + '.dgbundle')

if not os.path.exists(BUNDLE_FILE):
    raise ImportError('unsupported platform: {}'.format(PY_TAG))

with open(BUNDLE_FILE, 'rb') as _fd:
    for _c in marshal.load(_fd):
        eval(_c)

del _c
del _fd
