# dg

A (technically) simple language that compiles to CPython bytecode.

## Interpreter Support

dg supports all Python implementations that use CPython 3.2 bytecode.
(That is, only CPython 3.2 and 3.3 are supported. It's disappointing
that other interpreters are still trying to implement Python 2.)

CPython 3.1 lacks support for bytecode repositories. (The only problem is absence of [imp.cache_from_source](http://docs.python.org/py3k/library/imp.html#imp.cache_from_source) function, actually.)

CPython 3.0 utilizes non-popping jump bytecodes (`JUMP_IF_TRUE`/`JUMP_IF_FALSE`).

All Python 2 implementations are unable to run the compiler at all.

## TODO

 * full context manager support (i.e. `with ... as ...`)
 * function annotations (they are quite simple, but the syntax is a problem)
 * a neater syntax for loops (both `for` and `while`)
 * a syntax for list/dict/set literals
 * special syntax for slices (they are currently available as the `slice` built-in, though)
 * command-line interface to `parse` and `compile`
 * minor syntax enhancements such as regex literals and dedented multi-line strings
 * parser and compiler performance improvements
 * bytecode optimizer (or an interface to `PyCode_Optimize`)
