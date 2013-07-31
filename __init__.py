from __future__ import print_function
import sys
import types
import marshal
import os.path


SRC_DIR    = os.path.join(__path__[0], 'core')
BUNDLE_DIR = os.path.join(__path__[0], 'bundles')


if not hasattr(sys, 'implementation'):
    print('FATAL:', 'Your Python version is too old. 3.3 is required,', file=sys.stderr)
    print('      ', 'as it supports a lot of cool new features.',       file=sys.stderr)
    print('FATAL:', 'dg requires cool features to operate.',            file=sys.stderr)
    exit(1)

tag = sys.implementation.cache_tag

if tag is None:
    print('FATAL:', 'Module caching is disabled on iterpreter level.', file=sys.stderr)
    print('FATAL:', 'dg requires module caching to load itself.',      file=sys.stderr)
    exit(1)

bundle = os.path.join(BUNDLE_DIR, tag + '.bundle')

if len(sys.argv) > 1 and '--build' in sys.argv:
    if not os.path.isdir(SRC_DIR):
        print('FATAL:', 'Cannot find the source code.',      file=sys.stderr)
        print('      ', 'Your copy of the repo is corrupt.', file=sys.stderr)
        exit(1)

    try:
        import dg
    except ImportError:
        print('NOTE: ', 'This crap is not self-sufficient yet.', file=sys.stderr)
        print('FATAL:', '`master` branch of dg was not found.',  file=sys.stderr)
        exit(1)

    c = dg.compile.core.CodeGenerator('<module>')

    for f in sorted(os.listdir(SRC_DIR)):
        with open(os.path.join(SRC_DIR, f), 'r') as fd:
            c.loadop('POP_TOP', dg.parse.fd(fd), delta=0)

    c.loadop('RETURN_VALUE', None, delta=0)
    code = c.compiled

    try:
        os.makedirs(BUNDLE_DIR, exist_ok=True)
        with open(bundle, 'wb') as fd:
            marshal.dump(code, fd)
    except IOError as e:
        print('DEBUG:', str(e),                                   file=sys.stderr)
        print('WARN: ', 'Unable to store the compiled data.',     file=sys.stderr)
        print('WARN: ', 'Bundle was not created. Running as is.', file=sys.stderr)

else:
    if not os.path.isfile(bundle):
        print('FATAL:', 'No bundle found for your interpreter.', file=sys.stderr)
        print('      ', "Try running this module with --build.", file=sys.stderr)
        print('DEBUG:', 'Interpreter tag:', tag,                 file=sys.stderr)
        exit(1)

    with open(bundle, 'rb') as fd:
        try:
            code = marshal.load(fd)
        except Exception as e:
            print('FATAL:', 'Failed to load the precompiled bundle.', file=sys.stderr)
            print('      ', "It's probably corrupt or something.",    file=sys.stderr)
            print('DEBUG:', type(e).__name__ + ':', str(e),           file=sys.stderr)
            exit(1)


module = types.ModuleType('dgx')
module.__file__ = bundle
module.__path__ = __path__
eval(code, module.__dict__)
sys.modules['dgx'] = module
