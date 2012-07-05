import builtins
import operator
import functools

from ..compile import varary


builtins.__dict__.update({
    # Runtime counterparts of some stuff in `Compiler.builtins`.
    '$': lambda f, *xs: f(*xs)
  , ':': lambda f, *xs: f(*xs)
  , ',': lambda a, *xs: (a,) + xs

  , '<':  operator.lt
  , '<=': operator.le
  , '==': operator.eq
  , '!=': operator.ne
  , '>':  operator.gt
  , '>=': operator.ge
  , 'is': operator.is_
  , 'in': lambda a, b: a in b

  , 'not': operator.not_
  , '~':  operator.invert
  , '+':  varary(operator.pos, operator.add)
  , '-':  varary(operator.neg, operator.sub)
  , '*':  operator.mul
  , '**': operator.pow
  , '/':  operator.truediv
  , '//': operator.floordiv
  , '%':  operator.mod
  , '!!': operator.getitem
  , '&':  operator.and_
  , '^':  operator.xor
  , '|':  operator.or_
  , '<<': operator.lshift
  , '>>': operator.rshift

    # Useful stuff.
  , 'foldl': functools.reduce
  , '~:': functools.partial
})
