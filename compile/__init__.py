import re
import os.path

from . import core
from .. import const
from .. import parse
from ..parse import tree
from ..parse import syntax


#
# `var = expr`
#
# Assign `var` the value of `expr`.
#
def store(self, var, expr):

    expr, type, var, *args = syntax.assignment(var, expr)

    if type == const.AT.IMPORT:

        self.opcode('IMPORT_NAME', args[0], None, arg=expr, delta=1)

    else:

        self.load(expr)

    store_top(self, type, var, *args)


def store_top(self, type, var, *args, dup=True):

    dup and self.opcode('DUP_TOP', delta=1)

    if type == const.AT.UNPACK:

        ln, star = args
        op  = 'UNPACK_SEQUENCE'            if star <  0 else 'UNPACK_EX'
        arg = star + 256 * (ln - star - 1) if star >= 0 else ln
        self.opcode(op, arg=arg, delta=ln - 1)

        for item in var:

            store_top(self, *item, dup=False)

    elif type == const.AT.ATTR:

        syntax.ERROR(var[1] in self.fake_methods, const.ERR.FAKE_METHOD_ASSIGNMENT)
        self.opcode('STORE_ATTR', var[0], arg=var[1], delta=-1)

    elif type == const.AT.ITEM:

        self.opcode('STORE_SUBSCR', *var, delta=-1)

    else:

        syntax.ERROR(var in self.builtins, const.ERR.BUILTIN_ASSIGNMENT)
        syntax.ERROR(var in self.fake_methods, const.ERR.BUILTIN_ASSIGNMENT)
        syntax.ERROR(var in self.code.cellnames, const.ERR.FREEVAR_ASSIGNMENT)

        self.opcode(
            'STORE_DEREF' if var in self.code.cellvars else
            'STORE_NAME'  if self.code.slowlocals else
            'STORE_FAST',
            arg=var, delta=-1
        )


#
# `argspec -> body`
#
# Allow to evaluate `body` passing it stuff that matches `argspec`.
#
def function(self, args, code):

    args, kwargs, defs, kwdefs, varargs, varkwargs, code = syntax.function(args, code)
    self.load(**kwdefs)
    self.load(*defs)

    mcode = codegen.MutableCode(True, args, kwargs, varargs, varkwargs, self.code)

    hasattr(self.code, 'f_hook') and self.code.f_hook(mcode)
    code = self.compile(code, mcode, name='<lambda>')

    self.opcode(
        preload_free(self, code), code,
        arg=len(defs) + 256 * len(kwdefs),
        delta=-len(kwdefs) * 2 - len(defs) - bool(code.co_freevars) + 1
    )


def preload_free(self, code):

    if code.co_freevars:

        for freevar in code.co_freevars:

            if freevar in self.code.varnames:

                # Make fast slot accessible from inner scopes.
                self.opcode('LOAD_FAST',   arg=freevar, delta=1)
                self.opcode('STORE_DEREF', arg=freevar, delta=-1)

            self.opcode('LOAD_CLOSURE', arg=freevar, delta=1)

        self.opcode('BUILD_TUPLE', arg=len(code.co_freevars), delta=-len(code.co_freevars) + 1)

    return 'MAKE_CLOSURE' if code.co_freevars else 'MAKE_FUNCTION'


class r (core.Compiler):

    # Stuff not worth named functions.
    builtins = {
        '':   core.Compiler.call
      , ':':  core.Compiler.call
      , '=':  store
      , '->': function
      , ',':  lambda self, a, *bs: self.opcode('BUILD_TUPLE', *syntax.tuple_(a, *bs), delta=1)
      , '.':  lambda self, a, b: self.opcode('LOAD_ATTR', a, arg=b, delta=1)
      , '$':  lambda self, a, *bs, c=tree.Closure: self.call(a, *[c([b]) for b in bs] or [c()])
    }

    fake_methods = {}


# Now, load the remaining parts.
for p in sorted(os.listdir(os.path.dirname(__file__))):

    if re.match('\d+-', p):

        __debug__ and print('--- bootstrapping', p)
        n = os.path.join(os.path.dirname(__file__), p)
        q = parse.r().reset(open(n).read(), n)
        c = r().compile(next(q))
        eval(c, {'__package__': __package__, '__file__': n})
        __debug__ and print('    done')

