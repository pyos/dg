from ..core import CodeGenerator, INFIXL, INFIXR, PREFIX
from ..     import syntax
from ...    import parse


def ensure(f, args, min=1, max=float('inf')):

    len(args) < min and syntax.error('not enough arguments (got {}, min. {})'.format(len(args), min), f)
    len(args) > max and syntax.error('too many aguments (got {}, max. {})'   .format(len(args), max), f)
    return args


def unpack(f, args, g):

    try:

        a, _, _, kw, va, vkw = syntax.argspec(args, definition=False)
        (va or vkw) and syntax.error("can't use varargs with macros", f)
        return g(*a, **kw)

    except TypeError as e:

        syntax.error(str(e), f)

SUBMODULE_NS = globals().copy()

import os
import imp
import marshal
import posixpath

PREFIX.update({
    '\n':  lambda self, _, args: self.chain   (*args)
  , '':    lambda self, _, args: self.call    (*args, rightbind=True)
  , '=':   lambda self, f, args: self.store   (*ensure(f, args, 2, 2))
  , '->':  lambda self, f, args: self.function(*ensure(f, args, 2, 2))

  , '.':      lambda self, f, args: getattr(self, f, *ensure(f, args, 2, 2))
  , 'import': lambda self, f, args: import_(self, f, *ensure(f, args, 1, 2))
})


def getattr(self, _, a, b):
    '''Retrieve an attribute of some object.

        a.b

    '''

    isinstance(b, parse.Link) or syntax.error('not an attribute', b)
    self.load(a)
    self.loadop('LOAD_ATTR', arg=b, delta=0)


def import_(self, _, name, qualified=None):
    '''Import a module given a POSIX-style path.

        import 'path/to/the/object'            # => `object`
        import 'path/to/the/object' qualified  # => `path`

        All paths are relative to the current package.
        Absolute imports start with a single slash.

    '''

    isinstance(name, parse.Constant) or syntax.error('should be constant', name)
    isinstance(name.value, str)      or syntax.error('should be a string', name)
    qualified in (None, 'qualified') or syntax.error('invalid argument', qualified)

    path   = posixpath.normpath(name.value).split(posixpath.sep)
    parent = 1

    while path and path[0] == ''           and not path.pop(0): parent  = 0
    while path and path[0] == posixpath.pardir and path.pop(0): parent += 1
    while path and path[0] == posixpath.curdir and path.pop(0): pass

    path or syntax.error('no module name', name)

    if qualified or len(path) == 1:

        self.loadop('IMPORT_NAME', parent, None, arg='.'.join(path), delta=1)

    else:

        *dir, file = path
        self.loadop('IMPORT_NAME', parent, (file,), arg='.'.join(dir), delta=1)
        self.loadop('IMPORT_FROM', arg=file, delta=1)
        self.loadop('ROT_TWO', delta=0)
        self.loadop('POP_TOP', delta=-1)

    self.loadop('DUP_TOP', delta=1)
    self.store_var(path[-(not qualified)])


for f in [
       'shortcuts.dg'
  , 'conditionals.dg',  'unary.dg'
  ,       'binary.dg', 'switch.dg', 'inherit.dg'
  ,   'comparison.dg',  'where.dg',   'loops.dg', 'yield.dg'
  ,   'functional.dg', 'unsafe.dg',    'with.dg'
  ,      'imphook.dg'
]:
    f = os.path.join(__path__[0], f)
    q = imp.cache_from_source(f)

    try:

        c = os.stat(q).st_mtime > os.stat(f).st_mtime and marshal.load(open(q, 'rb'))

    except Exception:

        c = None

    if not c:

        os.makedirs(os.path.dirname(q), exist_ok=True)
        p = CodeGenerator('<module>')
        p.loadop('RETURN_VALUE', parse.fd(open(f)), delta=0)
        c = p.compiled
        marshal.dump(c, open(q, 'wb'))

    eval(c, SUBMODULE_NS.copy())
