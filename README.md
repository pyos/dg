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
 * a neater syntax for loops and list/dict/set literals
 * ^ + minor syntax enhancements such as regex literals and dedented multi-line strings
 * ^ + function annotations (they are quite simple, but the syntax is a problem)
 * parser and compiler performance improvements
 * ^ + bytecode optimizer (or an interface to `PyCode_Optimize`)
