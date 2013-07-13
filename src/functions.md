## Functions

### Calling them...

The syntax for calling functions is a mix of ones found in Haskell and
Smalltalk. There are no parentheses around arguments, neither are there
commas in between them.

```dg
# Here `sep` and `end` are *keyword argument names*.
# The order of these keyword arguments may be arbitrary;
# they may even come before positional ones. The only requirement
# is that none of them "collide" with a positional argument.
print 'Hello' 'print' sep: ', ' end: '!\n'
```

If the last argument is a call to another function, `$` will work
as a large opening parenthesis that is closed at the end of the line
or at a next comma:

```dg
person  = 'John'
command = 'Boggle vacantly at these shenanigans'
print $ '> {}: {}'.format person command
```

Obviously, simply typing `print` won't do anything other than
returning a `function` object. If you really want to call it with no arguments
(unlikely,) add an exclamation mark at the end.

```dg
print!
```

Also works if you want to retrieve an attribute of the returned object.

```dg
getlocal = locals!.__getitem__
```

Avoid creating too much functions without arguments, as these are a sign of a
poor design full of (possibly undesired) side effects.

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

### ...and creating some new ones.

Functions are defined with the `->` operator. Argument specifications
are similar to those when calling functions, but with a few quirks.

 * only something that can be assigned to (i.e. a name, an attribute, a subitem, or a tuple) is accepted as an argument name;
 * `a: b` defines an argument `a` with a default value `b`;
 * `*: a` stores the [remainder of the positional arguments](http://en.wikipedia.org/wiki/Variadic_function) in `a`;
 * `**: a` does the same thing for keyword arguments;
 * if a positional argument has a default value, all positional arguments that come after it must have them, too;
 * `**: a`, if defined, should be the last argument.

```dg
double = x -> x * 2
double 10 #=> 20

# These have no arguments and always return None. Useless.
constant  = () -> None
constant1 = () -> ()
# If either side of `->` is omitted, it is inferred to be `()`.
constant2 = -> ()
constant3 = () ->
constant4 = ->

# This one accepts any amount of arguments.
doubleMany = *: xs -> map double xs
doubleMany!      #=> empty `map` object
doubleMany 1 2 3 #=> `map` object containing 2, 4, and 6

# This one requires one argument and will accept more.
mapOverArgs = function *: xs -> map function xs
mapOverArgs double       #=> empty `map` object
mapOverArgs double 1 2 3 #=> `map` object containing 2, 4, and 6

# This one has one argument with a default value.
greet = whom: 'World' -> print 'Hello' whom sep: ', ' end: '!\n'
greet!         #=> 'Hello, World!'
greet 'Reader' #=> 'Hello, Reader!'

# This one returns its keyword arguments.
dict'' = **: kwargs -> kwargs
dict'' a: 1 == dict' ('a', 1)

# And this one unpacks a tuple when called.
# Simulating Python syntax 'n' stuff.
lolParentheses = (a, b) -> a + b
lolParentheses(1, 2)

# And so on.
```

Functions always return the last value they evaluate.

```dg
definitelyADoublingFunction = x ->
  x * 2
  x

definitelyADoublingFunction 10  #=> still 10 :-/
```

Thanks to these awesome anonymous functions, there's little need for decorators
anymore. Simply call a decorator with a function as its argument.

```dg
wtf = staticmethod $ ->
  print "I know static methods don't make sense outside of a class,"
  print "but this was the most obvious decorator I could think of."
```

And, of course, [yield](http://docs.python.org/py3k/reference/simple_stmts.html#the-yield-statement)
turns a function into a coroutine (aka [generator](http://docs.python.org/dev/glossary.html#term-generator).)
`yield` is a function of two arguments, `item` and `from`. Only one of them may
be specified at a time. (Well, not really, but passing both at the same time
is not possible in Python, so I wouldn't recommend that.)

```dg
count = start ->
  yield start
  yield from: (count $ start + 1)
```
