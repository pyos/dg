import types
import marshal
import os.path
# This stuff is not self-sufficient yet.
import dg


SRC_DIR    = os.path.join(__path__[0], 'core')
BUNDLE_DIR = os.path.join(__path__[0], 'bundles')


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


#make_bundle('cpython-33')
mod = load_bundle('cpython-33')
eval(mod.compile('print (1 + 1)'))
