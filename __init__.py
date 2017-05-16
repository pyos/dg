import os
import sys
import types

try:
    PY_TAG     = sys.implementation.cache_tag or 'unknown'
    PY_VERSION = sys.hexversion
    BUNDLE_DIR = os.path.join(__path__[0], 'bundle')
except AttributeError:
    raise ImportError('Python >= 3.4 required')

def load():
    from marshal import load

    try:
        with open(os.path.join(BUNDLE_DIR, PY_TAG + '.dgbundle'), 'rb') as fd:
            for code in load(fd):
                eval(code)
    except FileNotFoundError:
        try:
            with open(os.path.join(BUNDLE_DIR, PY_TAG + '.dgbundle.py')) as fd:
                for code in eval(fd.read(), {'C': types.CodeType}):
                    eval(code)
        except FileNotFoundError:
            raise ImportError('python implementation {!r} not supported'.format(PY_TAG))

load()
