import os
import imp
import marshal
import posixpath

from ..core import CodeGenerator, INFIXL, INFIXR, PREFIX
from ...    import parse


PREFIX.update({
    '\n':  lambda self, _, args: self.chain   (*args)
  , '':    lambda self, _, args: self.call    (*args, rightbind=True)
  , '=':   lambda self, f, args: self.store   (*unpack(f, args, 2, 2)[0])
  , '->':  lambda self, f, args: self.function(*unpack(f, args, 2, 2)[0])

  , '.':      lambda self, f, args: getattr(self, f, *unpack(f, args, 2, 2)[0])
  , 'import': lambda self, f, args: import_(self, f, *unpack(f, args, 1, 2)[0])
})


def unpack(f, args, min, max, keywords=None, var=False):

    LOW  = 'not enough arguments (got {}, min. {})'
    HIGH = 'too many aguments (got {}, max. {})'
    KERR = 'unknown keywords: {}'
    VERR = 'varargs are not allowed here'

    a, _, _, kw, va, vkw = \
      (args, (), (), {}, (), ()) if keywords is None or (f.infix and not f.closed) else \
      parse.syntax.argspec(args, definition=False)

    len(a) < min and parse.syntax.error(LOW .format(len(a), min), f)
    len(a) > max and parse.syntax.error(HIGH.format(len(a), max), f)

    if kw:
        unknown = kw.keys() - keywords
        unknown and parse.syntax.error(KERR.format(unknown), f)

    not var and (va or vkw) and parse.syntax.error(VERR, f)
    return a, kw, va, vkw
    

def getattr(self, _, a, b):
    '''Retrieve an attribute of some object.

        a.b

    '''

    isinstance(b, parse.tree.Link) or parse.syntax.error('not an attribute', b)
    self.load(a)
    self.loadop('LOAD_ATTR', arg=b, delta=0)


def import_(self, _, name, qualified=None):
    '''Import a module given a POSIX-style path.

        import '/path/to/the/object'            # => `object`
        import '/path/to/the/object' qualified  # => `path`

        All paths are relative to the current package.
        Absolute imports start with a single slash.

    '''

    isinstance(name, parse.tree.Constant) or parse.syntax.error('should be constant', name)
    isinstance(name.value, str)           or parse.syntax.error('should be a string', name)
    qualified in (None, 'qualified') or parse.syntax.error('invalid argument', qualified)

    path   = posixpath.normpath(name.value).split(posixpath.sep)
    parent = 1

    while path and path[0] == ''           and not path.pop(0): parent  = 0
    while path and path[0] == posixpath.pardir and path.pop(0): parent += 1
    while path and path[0] == posixpath.curdir and path.pop(0): pass

    path or parse.syntax.error('no module name', name)

    if qualified or len(path) == 1:

        qualified and parent and parse.syntax.error("relative imports can't be qualified", qualified)
        self.loadop('IMPORT_NAME', parent, None, arg='.'.join(path), delta=1)
        self.loadop('DUP_TOP', delta=1)
        self.store_top(parse.tree.Link(path[0]).before(name))

    else:

        *dir, file = path
        self.loadop('IMPORT_NAME', parent, (file,), arg='.'.join(dir), delta=1)
        self.loadop('IMPORT_FROM', arg=file, delta=1)
        self.loadop('ROT_TWO', delta=0)
        self.loadop('POP_TOP', delta=-1)
        self.loadop('DUP_TOP', delta=1)
        self.store_top(parse.tree.Link(file).before(name))


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
        p = CodeGenerator('<module>', '')
        p.loadop('RETURN_VALUE', parse.fd(open(f)), delta=0)
        c = p.compiled
        marshal.dump(c, open(q, 'wb'))

    eval(c, {'__package__': __package__, 'INFIXL': INFIXL, 'INFIXR': INFIXR, 'PREFIX': PREFIX, 'parse': parse, 'unpack': unpack})
