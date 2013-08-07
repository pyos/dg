import sys
import marshal
import os.path


if not hasattr(sys, 'implementation'):
    if sys.hexversion >= 0x03020000:
        # 3.2 is supported, although it lacks `sys.implementation`.
        # We'll use `platform` instead.
        import platform

        tag = platform.python_implementation().lower() + '-32'
    else:
        raise ImportError('Python 3.2 or newer is required.')
else:
    tag = sys.implementation.cache_tag

if tag is None:
    # Never seen this to be true, but Python documentation
    # mentions that it's possible.
    raise ImportError('Module caching is disabled. Cannot load the bundle.')

bundle = os.path.join(__path__[0], 'bundles', tag + '.dgbundle')

if not os.path.isfile(bundle):
    # Probably unsupported.
    raise ImportError('No bundle found for `{}`.'.format(tag))

try:
    with open(bundle, 'rb') as _fd:
        for _c in marshal.load(_fd):
            eval(_c)
except IOError:
    raise ImportError('The bundle for `{}` is inaccessible.'.format(tag))
except Exception:
    raise ImportError('The bundle for `{}` is corrupt.'.format(tag))
