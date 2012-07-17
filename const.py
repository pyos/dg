class ERR:

    DEFAULT = 'invalid syntax'

  ### SYNTAX

    # Attempted to store an imported module in a non-variable (e.g. object attribute.)
    NONCONST_IMPORT = 'can\'t infer module name from variable name'
    # Attempted to pass a kwarg with an invalid name.
    NONCONST_KEYWORD = 'keyword argument names should be constant'
    # Attempted to get an attribute by non-constant name.
    NONCONST_ATTR = 'can\'t access attributes with non-constant names'
    # Attempted to assign a value to something but a name.
    NONCONST_VARNAME = 'can\'t assign to non-constant names'
    # Same as above, but for function arguments.
    NONCONST_ARGUMENT = 'pattern-matching of function arguments is not supported'

    # Two or more *varargs definitions.
    MULTIPLE_VARARGS = 'multiple *varargs are not allowed'
    # Same as above, but for **varkwargs.
    MULTIPLE_VARKWARGS = 'multiple **varkwargs are not allowed'
    # *varargs or **varkwargs have been assigned a default value in function definition.
    VARARG_DEFAULT = 'neither *varargs nor **varkwargs can have default values'
    # **varkwargs is not the last argument in function definition.
    ARG_AFTER_VARKWARGS = '**varkwargs must be the last argument'
    # *varargs or **varkwargs used on a compile-time function
    VARARG_WITH_BUILTIN = 'can\'t call compile-time functions with *varargs'

    # `else` did not follow an `if` directly.
    NOT_AFTER_IF = 'that should be used only after `if` or `unless`'

    # `switch` contains something other than assignments
    INVALID_STMT_IN_SWITCH = 'all rules in `switch` must be of form `condition = action`'

  ### UNDEFINED BEHAVIOR

    # Attempted to assign a value to a non-local variable.
    FREEVAR_ASSIGNMENT = 'can\'t assign to free variables'

  ### CPYTHON LIMITATIONS

    # More than 255 arguments in a function definition.
    TOO_MANY_ARGS = 'CPython can\'t into 256+ arguments'
    # More than 255 items before a *starred expression in iterable unpacking.
    TOO_MANY_ITEMS_BEFORE_STAR = 'too many items before a *starred expression'
    # An argument between one with a default value and *varargs lacks such a value.
    NO_DEFAULT = 'one of the arguments lacks the required default value'


class CO:

    OPTIMIZED, NEWLOCALS, VARARGS, VARKWARGS, NESTED, GENERATOR, NOFREE = map(
        lambda x: 2 ** x,
        range(7)
    )


class AT: IMPORT, UNPACK, ATTR, ITEM, NAME = range(5)

