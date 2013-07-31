from __future__ import print_function
import sys
import marshal
import os.path


SRC_DIR    = os.path.join(__path__[0], 'core')
BUNDLE_DIR = os.path.join(__path__[0], 'bundles')


if not hasattr(sys, 'implementation'):
    print('FATAL:', 'Your Python version is too old. 3.3 is required,', file=sys.stderr)
    print('      ', 'as it supports a lot of cool new features.',       file=sys.stderr)
    print('FATAL:', 'dg requires cool features to operate.',            file=sys.stderr)
    exit(1)

_tag = sys.implementation.cache_tag

if _tag is None:
    print('FATAL:', 'Module caching is disabled on iterpreter level.', file=sys.stderr)
    print('FATAL:', 'dg requires module caching to load itself.',      file=sys.stderr)
    exit(1)

_bundle = os.path.join(BUNDLE_DIR, _tag + '.bundle')

if len(sys.argv) > 1 and '--build' in sys.argv:
    try:
        import dg
    except ImportError:
        print('NOTE: ', 'This crap is not self-sufficient yet.', file=sys.stderr)
        print('FATAL:', '`master` branch of dg was not found.',  file=sys.stderr)
        exit(1)

    if not os.path.isdir(SRC_DIR):
        print('FATAL:', 'Cannot find the source code.',      file=sys.stderr)
        print('      ', 'Your copy of the repo is corrupt.', file=sys.stderr)
        exit(1)

    _code = dg.compile.core.CodeGenerator('<module>')

    for _f in sorted(os.listdir(SRC_DIR)):
        with open(os.path.join(SRC_DIR, _f), 'r') as _fd:
            _code.loadop('POP_TOP', dg.parse.fd(_fd), delta=0)

    _code.loadop('RETURN_VALUE', None, delta=0)
    _code = _code.compiled

    try:
        os.makedirs(BUNDLE_DIR, exist_ok=True)
        with open(_bundle, 'wb') as _fd:
            marshal.dump(_code, _fd)
    except IOError as e:
        print('DEBUG:', str(e),                                   file=sys.stderr)
        print('FATAL:', 'Unable to store the compiled data.',     file=sys.stderr)
        print('FATAL:', "Bundle was not created. dg won't work.", file=sys.stderr)
        exit(1)
    exit(0)

else:
    if not os.path.isfile(_bundle):
        print('FATAL:', 'No bundle found for your interpreter.', file=sys.stderr)
        print('      ', "Try running this module with --build.", file=sys.stderr)
        print('DEBUG:', 'Interpreter tag:', tag,                 file=sys.stderr)
        exit(1)

    with open(_bundle, 'rb') as _fd:
        try:
            _code = marshal.load(_fd)
        except Exception as e:
            print('FATAL:', 'Failed to load the precompiled bundle.', file=sys.stderr)
            print('      ', "It's probably corrupt or something.",    file=sys.stderr)
            print('DEBUG:', type(e).__name__ + ':', str(e),           file=sys.stderr)
            exit(1)


eval(_code)
