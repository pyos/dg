from . import parser


CO_OPTIMIZED = 1   # PyFrame should ignore `f_locals` in favor of fast slots
CO_NEWLOCALS = 2   # PyFrame should create a new dict for `f_locals`
CO_VARARGS   = 4   # code object is a function with *varargs
CO_VARKWARGS = 8   # code object is a function with *varkwargs
CO_NESTED    = 16  # code object uses non-local variables
CO_GENERATOR = 32  # code object yields values
CO_NOFREE    = 64  # code object is NOT a closure neither it produces one


# Attempted to store an imported module in a non-variable (e.g. object attribute.)
ERR_NONCONST_IMPORT = 'use `__import__` instead'
# Attempted to pass a kwarg with an invalid name.
ERR_NONCONST_KEYWORD = 'argument names should be...well, names'
# Attempted to get an attribute by non-constant name.
ERR_NONCONST_ATTR = 'use `setattr` instead'
# Attempted to assign a value to something but a name.
ERR_NONCONST_VARNAME = 'can\'t assign to non-constant names'
# Attempted to assign a value to a non-local variable.
ERR_FREEVAR_ASSIGNMENT = 'can\'t assign to free variables'
# More than 255 arguments in a function definition.
ERR_TOO_MANY_ARGS = 'CPython can\'t into 256+ arguments'
# Two or more *varargs definitions.
ERR_MULTIPLE_VARARGS = 'multiple *varargs are not allowed'
# Same as above, but for **varkwargs.
ERR_MULTIPLE_VARKWARGS = 'multiple **varkwargs are not allowed'
# *varargs or **varkwargs have been assigned a default value in function definition.
ERR_VARARGS_DEFAULT = 'neither *varargs nor **varkwargs can have default values'
# **varkwargs is not the last argument in function definition.
ERR_ARG_AFTER_VARARGS = '**varkwargs must be the last argument'
# An argument between one with a default value and *varargs lacks such a value.
ERR_NO_DEFAULT = 'one of the arguments lacks the required default value'


( # Common syntactic constructs.
    ST_CLOSURE,    # (expression in parentheses)
    ST_IMPORT,     # import statement (a constant RHS to assignment operator)

    ST_OP_FUNCALL,    # function call with a single argument
    ST_OP_TUPLE,      # tuple constructor (i.e. infix comma)
    (ST_OP_TUPLE_S,), # tuple with a single item (i.e. unary postfix comma)
    ST_OP_ATTRIBUTE,  # attribute getter (i.e. infix dot)
    ST_OP_ITEM,       # item getter

    ST_ARG_KW,         # keyword argument to a function call
    ST_ARG_VAR,        # *varargs
    ST_ARG_VAR_KW,     # **varkwargs
) = parser.Parser().parse(
    '(_); import;'
    '_ _; _, _; (_,); _._; _ !! _;'
    '_: _; *_; **_'
)


