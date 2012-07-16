# dg

A (technically) simple language that compiles to CPython bytecode.

## Interpreter Support

**Supported**: CPython 3.2 onwards, as well as any other Python 3.2+ implementations that use CPython bytecode format (none at the moment, all of them implement Python 2.)

**Probably supported**: CPython 3.1 (lacks `DUP_TOP_TWO` and `DELETE_DEREF` opcodes, which are not used.)

**Unsupported**: CPython 3.0 (lacks various jump instructions) as well as all kinds of Python 2 (the compiler itself is in Python 3.)

## TODO

 * a neater syntax for loops (both `for` and `while`)
 * context manager support (i.e. `with ... as ...`)
 * special syntax for slices (they are currently available as the `slice` built-in, though)
 * dg import hook, which compiles modules with `parse.r` and `compile.r` instead of the built-in `compile`, but is otherwise similar to the default CPython one
 * command-line interface to `parse` and `compile`
 * other minor syntax enhancements such as regex literals and dedented multi-line strings
 * useful runtime stuff not found in standard libraries (e.g. [built-in attribute setter context manager](http://code.activestate.com/recipes/577089/))

