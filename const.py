from . import parser


class FlagSet(list):

    def __getattr__(self, name):

        return 2 ** self.index(name)


class AttrDict (dict):

    def __getattr__(self, name):

        try:

            return self[name]

        except KeyError:

            raise AttributeError(name)


CO = FlagSet([  # code flags
    'OPTIMIZED'  # PyFrame should ignore `f_locals` in favor of fast slots
  , 'NEWLOCALS'  # PyFrame should create a new dict for `f_locals`
  , 'VARARGS'    # code object is a function with *varargs
  , 'VARKWARGS'  # code object is a function with *varkwargs
  , 'NESTED'     # code object uses non-local variables
  , 'GENERATOR'  # code object yields values
  , 'NOFREE'     # code object is NOT a closure neither it produces one
])


ERR = AttrDict(  # error descriptions

    DEFAULT = 'invalid syntax'

  ### SYNTAX

    # Attempted to store an imported module in a non-variable (e.g. object attribute.)
  , NONCONST_IMPORT = 'use `__import__` instead'
    # Attempted to pass a kwarg with an invalid name.
  , NONCONST_KEYWORD = 'keyword argument names should be constant'
    # Attempted to get an attribute by non-constant name.
  , NONCONST_ATTR = 'use `setattr` instead'
    # Attempted to assign a value to something but a name.
  , NONCONST_VARNAME = 'can\'t assign to non-constant names'

    # Two or more *varargs definitions.
  , MULTIPLE_VARARGS = 'multiple *varargs are not allowed'
    # Same as above, but for **varkwargs.
  , MULTIPLE_VARKWARGS = 'multiple **varkwargs are not allowed'
    # *varargs or **varkwargs have been assigned a default value in function definition.
  , VARARGS_DEFAULT = 'neither *varargs nor **varkwargs can have default values'
    # **varkwargs is not the last argument in function definition.
  , ARG_AFTER_VARARGS = '**varkwargs must be the last argument'

  ### UNDEFINED BEHAVIOR

    # Attempted to assign a value to a non-local variable.
  , FREEVAR_ASSIGNMENT = 'can\'t assign to free variables'

  ### CPYTHON LIMITATIONS

    # More than 255 arguments in a function definition.
  , TOO_MANY_ARGS = 'CPython can\'t into 256+ arguments'
    # More than 255 items before a *starred expression in iterable unpacking.
  , TOO_MANY_ITEMS_BEFORE_STAR = 'too many items before a *starred expression'
    # An argument between one with a default value and *varargs lacks such a value.
  , NO_DEFAULT = 'one of the arguments lacks the required default value'

)


AT = FlagSet([  # assignment types
    'IMPORT'
  , 'UNPACK'
  , 'ATTR'
  , 'ITEM'
  , 'NAME'
])
