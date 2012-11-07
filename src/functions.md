## Functions

### Calling them...

The syntax for calling functions is a mix of ones found in Haskell and
Smalltalk. There are no parentheses around arguments, neither are there
commas in between them.

```dg
# Here `sep` and `end` are *keyword argument names*.
# The order of these keyword arguments may be arbitrary;
# they may even come before positional ones. The only requirement
# is that none of them "collides" with a positional argument.
print 'Hello' 'print' sep: ', ' end: '!\n'
```

If the last argument is a call to another function, `$` will work
as a large parenthesis lasting up to the next comma, assignment, or
conditional:

```dg
print $ '* {}'.format 'Take out the trash'
print $ '* {}'.format 'Clean the kitchen' if not kitchen.clean
```

Obviously, simply typing `print` won't call it (instead, it would yield the
function object itself.) To call a function with no arguments, add
an exclamation mark after its name:

```dg
print!
```

Avoid creating too much functions without arguments — these are a sign of a
poor design full of magic and/or (possibly undesired) side effects.
When a function doesn't modify the state, but uses it, it's better to use
[properties](http://docs.python.org/dev/library/functions.html#property):

```dg
MyType = inherit object $
  state = 10
  stateful_function = property $ self -> self.state * 2
```

Two keyword argument names, `*` and `**`, are special.
Whatever is passed as `*` is interpreted as a collection of the remaining
positional arguments. `**` is similar, but takes a dictionary of keyword
arguments instead:

```dg
print 1 2 3 sep: ';' end: '.\n'

items   = 1, 2, 3
options = dict sep: ';' end: '.\n'
print *: items **: options
```

### ...and creating new ones.

Functions are defined with the `->` operator. Argument specifications
are similar to those when calling functions, but with a few changes and more
strict:

 * anything that can be assigned to is accepted as an argument name;
 * `a: b` defines an argument `a` with a default value `b`;
 * if an argument before `*: a` has a default value, all arguments up to the `*: a` (or the end of the argument list) must have default values, too;
 * any argument after `*: a` *can't* be passed as a positional argument, only a keyword one;
 * `**: a`, if defined, should be the last argument.

```dg
double = x -> x * 2
double 10 #=> 20

# These have no arguments and always return None.
constant  = () -> None
constant' = () -> ()

# This one accepts any amount of arguments.
doubleMany = (*: xs) -> map double xs
doubleMany!      #=> empty `map` object
doubleMany 1 2 3 #=> `map` object containing 2, 4, and 6

# This one requires one argument and will accept more.
map_over_args = (function *: xs) -> map function xs
map_over_args double       #=> empty `map` object
map_over_args double 1 2 3 #=> `map` object containing 2, 4, and 6

# This one has one argument with a default value.
greet = (whom: 'World') -> print 'Hello' whom sep: ', ' end: '!\n'
greet!         #=> 'Hello, World!'
greet 'Reader' #=> 'Hello, Reader!'

# This one returns its keyword arguments.
dict'' = (**: kwargs) -> kwargs

# And this one unpacks a tuple when called.
# Simulating Python syntax 'n' stuff.
lol_parentheses = (a, b) -> a + b
lol_parentheses (1, 2)
```

Functions return the last value they evaluate unless explicitly
told to do otherwise by adding a semicolon to an expression:

```dg
doubleIf = (f x) ->
  x * 2; if f x
  x

doubleIf (> 5) 10  #=> 20
doubleIf (> 5)  3  #=>  3
```

The `->` operator always consumes exactly one object to the left;
that way it is possible to create anonymous functions in the middle of
an expression without using parentheses in some cases:

```dg
list $ map x -> x.bit_length! $ list' 1 2 3 #=> 1, 2, 2
list $ map x -> (int x 16) '1639F16BA' #=> 1, 6, 3, 9, 15, 1, 6, 11, 10
```

Thanks to these awesome anonymous functions, there's little need for decorators
anymore. Simply pass functions to other functions:

```dg
wtf = staticmethod () ->
  print 'A static method outside of a class?!'
```

And, of course, [yield](http://docs.python.org/py3k/reference/simple_stmts.html#the-yield-statement)
turns a function into a coroutine (or a [generator](http://docs.python.org/dev/glossary.html#term-generator).)
`yield` is a function of two arguments, `item` and `from`. Only one of them may
be specified at a time. (Well, not really, but using both arguments at the same
time is probably not standardized in Python.)

Note that `from` requires Python 3.3 or newer. Also, returning some value
other than `None` from a generator in earlier versions will yield that
value; if you care about backward compatibility, make sure to end all
generators with `None`.

```dg
count = start ->
  yield start
  yield from: (count $ start + 1)
  None
```
