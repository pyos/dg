### Installation

Freaking easy:

1. download the compiler (why don't you look at the [index page](..) for that?);
2. put the "dg" directory somewhere in `$PYTHONPATH`, or `/usr/lib/python3.*/site-packages/`, or a virtual environment. In fact, if you don't want to install it system-wide, just leave it alone: Python always scans the current working directory for modules.

### Usage

Even easier.

```bash
python3 -m dg  # REPL!
python3 -m dg file.dg --do-something-useful-this-time  # Script!
```

##### Q: How to run some code from a shell?

A: Use your shell's herestring/heredoc.

```bash
python3 -m dg <<< "some code"
```

##### Q: How to run some code from a shell *and* be able to use stdin?

A: ...

##### Q: Is it possible to run dg modules with `python -m`?

Modules? No. Packages? Yes. Here's an example package in dg:

```
mypackage
|- __init__.py
|- __main__.dg
|- submodule.dg
\- subpackage/
   |- module1.dg
   \- module2.dg
```

Put this in `__init__.py`:

```python
import dg
```

Done! Now `python -m mypackage` will run `mypackage.__main__`.

### Comments

```dg
# sh-style. Know what I'm saying?
```

You probably know about docstrings. What you don't know is that they look
nothing like Python docstrings. Sphinx users may recognise this, though.

```dg
#: Do something with an argument.
#:
#: Raises:
#:     NameError: this function makes no sense.
#:
#: :param argument: any value.
#: :return: something absolutely different.
#:
function = argument -> something_absolutely_different
```

##### Q: That docstring syntax doesn't seem to work.

A: Not implemented yet.

### Literals

```dg
True
False
None

42                      # `int` of arbitrary size
0b01010111              # `int` in base 2
0o755                   # `int` in base 8
0xDEADF00D              # `int` in base 16; may be lowercase, too
3.14159265358979323865  # `float`
6.959500E+9             # `float` in scientific notation
1j                      # `complex`

'A string.'
"A double-quoted string."

'''One quote is good, three are better.'''
"""Right?"""

"
  A string can contain any character, including a line break.
  There are also some escapes: \\ \' \" \a \b \f \n \r \t \v \u0021
"

r"Raw strings have escapes disabled: \a \b \f \n \r \t \v. Useful for regex."
b"Byte literals are ASCII-only strings that represent binary data. \x42\x08\x15\x00"
rb"Guess what raw byte literals are."
```

Tuples are ordered immutable collections:

```dg
(2, True, 'this tuple contains random stuff')
```

An empty tuple is an empty pair of parentheses.

```dg
()
```

If you want a singleton tuple for some reason, put a comma after the only item.

```dg
("Fine, have your singleton.",)
```

Or use an alias.

```dg
tuple' 3 False "strictly speaking, this isn't random at all"
tuple' "Also, another singleton."
tuple! # And an empty tuple.
```

There is no special syntax for lists. Call `list` to make a list
out of another collection, or `list'` to create one from distinct elements:

```dg
list  (0..5)
list'  0 1 2 3 4
```

Same thing applies to sets and dictionaries. The latter are constructed
from pairs (i.e. tuples of size 2), though.

```dg
set  'abcdabc'
set' 'a' 'd' 'c' 'b'

dict $ list' ('a', 1) ('b', 2)
dict'        ('a', 1) ('b', 2)
```

There's a shorthand notation for dictionaries with identifier keys:

```dg
dict  a: 1 b: 2
dict' a: 1 b: 2
```

### Parentheses

They are used to explicitly define the precedence of operators. Duh.

```dg
6 == 2 *  2 + 2
8 == 2 * (2 + 2)
```

### Function calls

1. Write the name of the function.
2. Insert a space.
3. Put an argument you want to call it with.
4. Repeat 2 and 3 until tired.

```dg
print "such console," "beautiful text"
```

##### Q: Can I pass arguments by name?

A: Sure. `name: value`.

```dg
print "wow" "two lines" sep: "\n"
```

##### Q: What if the arguments are stored in a list?

`*: that_list`. Also, the keyword arguments stored in a dict can be
passed as `**: that_dict`.

```dg
doge = "so tuple", "many strings"
opts = dict sep: "\n"

print *: doge **: opts
```

##### Q: Do I have to use parentheses when calling a function with a result of another function?

There's also a reverse pipe operator.

```dg
print $ "> {}: {}".format "Karkat" "Insert a reference to something other than Doge"
```

##### Q: What if...what if there are NO arguments? At all?

Fear not.

```dg
print!
```

### Indentation

After an infix operator, an indented block is the same as a parenthesized one.
(OK, except for the "multiple statements" thing. That's kind of new.)

```dg
8 == 2 *
  print "calculating 2 + 2"
  # No, really, look:
  2 + 2
```

If there was no operator, however, each line is an argument to the last function call.

```dg
print "Doge says:" sep: "\n"
  "not want talk"
  "finally sleep"
```

### Assignment

```dg
such_variable = "much_constant"
```

If the value on the right side is a collection, it can be pattern-matched.

```dg
very_pattern, so_two_items, *rest = 3 * 'wow', 5 * 'sleep', 1 * 'eat', 2 * 'woof'
```

Global variables can only be modified from the top level. No `global` keyword for you!

### Creating functions

You saw that already.

```dg
#: This is a function.
#:
#: It has some positional arguments!
#:
function = arg1 arg2 ->
  # It also does something.
  print (arg1.replace "Do " "Did ") arg2 sep: ", " end: ".\n"

function "Do something" "dammit"
```

Arguments can have default values.

```dg
function = arg1 arg2: "dammit" ->
  # That was a really popular value for `arg2`.
  print (arg1.replace "Do " "Did ") arg2 sep: ", " end: ".\n"

function "Do something"
```

Functions can be variadic, because of course they can.

```dg
another_function = arg1 *: other_arguments **: other_keyword_arguments ->
  print end: ".\n" $ arg1.replace "Do " "Did "
  print end: ".\n" $ "Also, got {} positional and {} keyword argument(s)".format
    len other_arguments
    len other_keyword_arguments

another_function "Do something" "too" keyword: 'argument'
```

No arguments, no problem.

```dg
useless_function = -> print "Really useless."
```

Functions always return the last value they evaluate.

```dg
definitely_not_4 = x ->
  x + 2
  4

definitely_not_4 40
```

Decorators don't need special syntax anymore. Simply call them with a function.

```dg
wtf = staticmethod $ ->
  print "I know static methods don't make sense outside of a class,"
  print "but this was the most obvious decorator I could think of."
```

`yield` turns a function into a [generator/coroutine](http://docs.python.org/dev/glossary.html#term-generator).

```dg
count = start ->
  yield start
  for x in count (start + 1) =>
    yield x
```

### Operators

Standard issue stuff:

```dg
x + y   # addition
x - y   # subtraction or set difference
x * y   # multiplication
x ** y  # exponentiation
x / y   # floating-point division
x // y  # integer division
x % y   # modulo or string formatting
x & y   # bitwise AND or set intersection
x ^ y   # bitwise XOR or symmetric set difference
x | y   # bitwise OR or set union
x << y  # bit shift to the left
x >> y  # bit shift to the right
```

All of the operators above have an in-place form:

```dg
x += y  # sets x to (x + y)
x /= y  # sets x to (x / y)
x |= y  # you get the idea
```

Prefix:

```dg
~x # bit inversion
-x # numeric negation
```

Attribute/subitem access:

```dg
x !!  y = z  # set item Y of a collection X to Z
x !!  y      # get its value again
x !!~ y      # and remove it

x.y = z # set attribute 'y' of X to Z
x.y     # ooh, Z again!
x.~y    # remove that attribute
```

Boolean logic:

```dg
x or y
x and y
not x
```

And a special one:

```dg
x => y  # do Y if X is true
```

Any two-argument function can be used as an operator.

```dg
max 1 5 == 1 `max` 5
divmod 10 3 == 10 `divmod` 3
```

Operators that do not modify anything (with the exception of `or`, `and`, and `=>`)
are [first-class](http://en.wikipedia.org/wiki/First-class_function).

```dg
f = (+)
f 1 2 == 3
```

Any infix operator can be [partially bound](http://docs.python.org/dev/library/functools.html#functools.partial)
by omitting either of its sides. An exception to this is `-`, which behaves
as an unary `-` if the left side is missing.

```dg
f = (2 *)
f 10 == 20

g = in (1..5)
g  4 is True
g -2 is False

h = (- 5) == -5
```

### Conditional(s)

The main and only (unless you count `=>`, as well as really awkward uses
of `and` & `or`) conditional is `if`. I *could* write a large explanation,
but it'd be much better if you'd take a look at these examples instead.

```dg
factorial = n -> if
  # You can put indented blocks after these arrows, unless
  # they're on the same line as `if`.
  n < 0     => None
  n < 2     => 1
  otherwise => n * factorial (n - 1)
```

```dg
fibonacci = n ->
  if n < 0     => None  # e.g. not here
     n < 2     => n     #      but here is OK
     otherwise => fibonacci (n - 1) + fibonacci (n - 2)
```

```dg
abs = x -> if (x >= 0 => x) (otherwise => -x)
```

### Exceptions

First, throw with `raise`.

```dg
raise $ TypeError 'this is stupid'
```

Second, catch with `except`. It works just like `if`, only the first
clause is not a condition, but where to store the exception caught.
If the last condition is `finally`, the respective action is evaluated regardless of
circumstances.

```dg
except
  err => (open '/dev/sda' 'wb').write $ b'\x00' * 512
  err :: IOError and err.errno == 13 =>
    # That'd require root privileges, actually.
    print "Permission denied"
  err is None =>
    # Oh crap, someone actually runs python as root?
    print "Use GPT next time, sucker."
  finally =>
    # clean up the temporary files
    os.system 'rm -rf /*'
```

### Loops'n'stuff

These should be pretty straightforward. Both loops return the value of the last iteration.

```dg
a = 0
while a < 5 =>
  print a
  a += 1

for a in range 5 =>
  print a

for (a, b) in zip (1..6) (3..8) =>
  # 1 3
  # 2 4
  # ...
  # 5 7
  print a b
```

`with` is used to enter [contexts](http://www.python.org/dev/peps/pep-0343/).

```dg
with fd = open '__init__.py' =>
  print $ fd.read 5

fd.read 5  # IOError: fd is closed
```

### Objects and types

Wait, no. Gotta show you something else first.

### Local name binding

If you don't want some variables to be visible outside of a single
statement, `where` is your friend.

```dg
print b where
  print 'calculating a and b'
  a = 2 + 2
  b = 2 * 2

print b  # NameError
```

As a side effect, it can be used to make generator expressions.

```dg
list (where for x in range 5 => yield $ 2 ** x)
```

### What does it have to do with...

OK, ready? `subclass` turns the local namespace into a class, and a local namespace
is exactly what `where` creates. Its arguments are base classes. The `metaclass`
keyword argument is optional.

```dg
ShibaInu = subclass object metaclass: type where
  cuteness = 80
  
  __init__ = self name ->
    self.name = name
    # __init__ must always return None.
    # CPython limitation, not mine.
    None
```

If you ever get tired of writing `self`, change `->` to `~>` and `self.` to `@`.
A method with no arguments created with `~>` is automatically converted into a property.

```dg
Doge = subclass ShibaInu where
  cuteness = ~> ShibaInu.cuteness + 10
  post = message ~> twitter.send @name message
```

Create an instance of a class by calling it.

```dg
dawg = Doge '@DogeTheDog'
dawg.cuteness == 90
```

### New built-ins

`foldl` (and `foldl1`) is a left fold. Look it up.

```dg
sum     = xs -> foldl  (+) 0 xs
product = xs -> foldl1 (*)   xs  # same thing, but no starting value
```

`scanl` and `scanl1` are similar, but also yield intermediate values.

```dg
accumulate = xs -> scanl1 (+) xs
accumulate (1, 2, 3, 4)  #=> 1, 3, 6, 10
```

`bind` is `functools.partial`:

```dg
greet = bind print 'Hello' sep: ', ' end: '!\n'
greet 'World'
```

`flip` swaps the order of arguments of a binary function:

```dg
contains = flip (in)
(0..10) `contains` 3
```

`<-` is a function composition operator:

```dg
dot_product = sum <- bind map (*)  #=> xs -> sum $ map (*) xs
dot_product (1, 3, 5) (2, 4, 6)    #=> 44
```

`takewhile` and `dropwhile` are imported from `itertools`:

```dg
until_zero = bind takewhile (0 !=)
until_zero (1, 2, 3, 4, 0, 5, 6) #=> 1, 2, 3, 4
```

`take` returns the first N items, and `drop` returns the rest:

```dg
take 5 (0..10) #=> 0, 1, 2, 3, 4
drop 5 (0..10) #=> 5, 6, 7, 8, 9
```

`iterate` repeatedly applies a function to some value:

```dg
count = x -> iterate (+ 1) x
count 5 #=> 5, 6, 7, 8, ...
```

`head` and `fst` return the first item of a collection, `tail` returns the rest.
`snd` returns the second item. `last` is, well, the last item, and `init` is
everything *but* the last item. The last two functions do not work on iterables.

```dg
head (1, 2, 3, 4)  #=> 1
tail (1, 2, 3, 4)  #=> 2, 3, 4
fst  (1, 2)        #=> 1
snd  (1, 2)        #=> 2
init (1, 2, 3, 4)  #=> 1, 2, 3
last (1, 2, 3, 4)  #=> 4
```

### Library support

dg can import any Python module you throw at it, standard library included.

```dg
import '/sys'
```

If you're importing from a package, module names are relative to it.
So if you have a directory structure like this...

```
mypackage
|- __init__.py
|- __main__.dg
|- submodule.dg
\- subpackage/
   |- module1.dg
   \- module2.dg
```

...and your `module2.dg` looks like this...

```dg
import 'module1'
import 'module1/global_variable'
import '../submodule'
# Now we have `module1`, `global_variable`, and `submodule`.
```

...the ending to this sentence becomes obvious. Oh, and since those are POSIX
paths, they are normalized automatically.

```dg
import '/doesnotexist/../../sys'  # same as '/sys'
```

`import` returns the object it has imported.

```dg
import '/os' == os
```
