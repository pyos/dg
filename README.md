# dg

A (technically) simple language that compiles to CPython bytecode.

## Interpreter Support

Version      | Compiles | Runs     | Runs flawlessly | Reason
------------ | -------- | -------- | --------------- | -------------------------------------------------------
CPython 3.3  | Probably | Probably | Probably        | Not much changed since 3.2
CPython 3.2  | Yes      | Yes      | Yes (for now)   | Import hooks and other stuff will require 3.3
CPython 3.1  | Probably | Probably | Probably        | The new opcodes in 3.2 are not used by dg
CPython 3.0  | No       | No       | No              | Old-style jumps (that don't pop items off the stack)
Any Python 2 | No       | No       | No              | Guess why.

## TODO

 * a neater syntax for loops (both `for` and `while`)
 * context manager support (i.e. `with ... as ...`)
 * special syntax for slices (they are currently available as the `slice` built-in, though)
 * dg import hook, which compiles modules with `parse.r` and `compile.r` instead of the built-in `compile`, but is otherwise similar to the default CPython one
 * command-line interface to `parse` and `compile`
 * other minor syntax enhancements such as regex literals and dedented multi-line strings
 * useful runtime stuff not found in standard libraries (e.g. [built-in attribute setter context manager](http://code.activestate.com/recipes/577089/))

