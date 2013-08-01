import sys
import marshal
import os.path


if not hasattr(sys, 'implementation'):
    raise ImportError('Python version is too old. 3.3. is required.')

_tag = sys.implementation.cache_tag

if _tag is None:
    raise ImportError('Module caching is disabled. Failed to locate the bundle.')

_bundle = os.path.join(__path__[0], 'bundles', _tag + '.dgbundle')

if not os.path.isfile(_bundle):
    raise ImportError('No bundle found for this interpreter (tag: {}).'.format(tag))

with open(_bundle, 'rb') as _fd:
    try:
        _codes = marshal.load(_fd)
    except Exception as e:
        raise ImportError('Corrupt bundle (tag: {}).'.format(tag))


for _c in _codes: eval(_c)
