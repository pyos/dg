import sys
import types
import marshal
import os.path
# This stuff is not self-sufficient yet.
import dg


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


def make_bundle(id):
    c = dg.compile.core.CodeGenerator('<module>')

    for f in sorted(os.listdir(SRC_DIR)):
        with open(os.path.join(SRC_DIR, f), 'r') as fd:
            c.loadop('POP_TOP', dg.parse.fd(fd), delta=0)

    c.loadop('RETURN_VALUE', None, delta=0)

    os.makedirs(BUNDLE_DIR, exist_ok=True)
    with open(os.path.join(BUNDLE_DIR, id + '.bundle'), 'wb') as fd:
        marshal.dump(c.compiled, fd)


def load_bundle(id):
    with open(os.path.join(BUNDLE_DIR, id + '.bundle'), 'rb') as fd:
        code = marshal.load(fd)
    mod = types.ModuleType('dgx')
    eval(code, mod.__dict__, mod.__dict__)
    return mod


make_bundle(tag)
mod = load_bundle(tag)
eval(mod.compile('print ((x -> x + 2) (1 + 1))'))
