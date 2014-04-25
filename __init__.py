import os
import sys
import marshal


if not hasattr(sys, 'implementation'):
    raise ImportError('python >= 3.3 required')

if sys.implementation.cache_tag is None:
    raise ImportError('python implementation does not use bytecode')

PY_TAG      = sys.implementation.cache_tag
PY_VERSION  = sys.hexversion
BUNDLE_DIR  = os.path.join(__path__[0], 'bundle')
BUNDLE_FILE = os.path.join(BUNDLE_DIR, PY_TAG + '.dgbundle')

if not os.path.exists(BUNDLE_FILE):
    raise ImportError('python implementation {!r} not supported'.format(PY_TAG))

with open(BUNDLE_FILE, 'rb') as _fd:
    for _c in marshal.load(_fd):
        eval(_c)

del _c
del _fd
