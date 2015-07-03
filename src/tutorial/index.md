### Installation

Easy!

```bash
pip3 install git+https://github.com/pyos/dg
```

Alternatively, you can run

```bash
git clone https://github.com/pyos/dg
```

then move the repository to some directory that is in `$PYTHONPATH`. Or
to `/usr/lib/python3.*/site-packages/`, or a virtual environment. In fact,
if you don't want to install it system-wide, just leave it alone:
Python always scans the current working directory for modules.

### Usage

Even easier.

```bash
python3 -m dg  # REPL!
python3 -m dg file.dg --do-something-useful-this-time  # Script!
python3 -m dg -m module  # Module! (Or package!)
python3 -m dg -c 'print "Command!"'
```

##### Q: I expected a copy of a help message.

```
python3 [options] -m dg -h
python3 [options] -m dg -b [tag [hexversion]]
python3 [options] -m dg [-c <command> | -m <module> | <file>] ...

VM options that make sense when used with dg:

  -B           don't save bytecode cache (i.e. `.pyc` and `.pyo` files);
  -E           ignore environment variables
  -s           don't add user site directory to sys.path
  -S           don't `import site` on startup
  -u           don't buffer standard output
  -v           trace import statements
  -X           implementation-specific options

Arguments:

  -h           show this message and exit
  -b           rebootstrap the compiler
    tag        cache tag of the target interpreter (e.g. `cpython-35`)
    hexversion version of the target interpreter as 8 hex digits (e.g. `030500A0`)
  -c command   run a single command, then exit
  -m module    run a module (or a package's `__main__`) as a script
  file         run a script
  ...          additional arguments accessible through `sys.argv`

Environment variables:

  PYTHONSTARTUP     a Python file executed on interactive startup
  PYTHONSTARTUPMOD  a name of the module to use instead of PYTHONSTARTUP
  PYTHONPATH        a `:`-separated list of directories to search for modules in
  PYTHONPREFIX      override the `--prefix` option of `configure`

...that have the same effect as options:

  PYTHONDONTWRITEBYTECODE    -B
  PYTHONNOUSERSITE           -s
  PYTHONUNBUFFERED           -u
  PYTHONVERBOSE              -v

```

##### Q: All the cool modules for Python have entry point scripts. Do you have a script?

Why would you need one? Most shells support `alias`.

```sh
$ alias dg="python3 -m dg"
$ dg # Good ones do, anyway.
>>>
```

Just put that in your `.bashrc` or something.

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
b"Byte literals are ASCII-only and represent binary data. \x42\x08\x15\x00"
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

Lists have the same syntax, but with square brackets instead of parentheses.
(Also, the alias is `list`, not `tuple`. Duh.)

```dg
[0, 1, 2, 3, 4]
[]
[0,]
list  (0..5)
list'  0 1 2 3 4
```

Dictionaries, too. These require each item to be a pair (i.e. a 2-tuple), though.
The first object is the key, the second is the value.

```dg
{('a', 1), ('b', 2)}
{('a', 1),}
dict  [('a', 1), ('b', 2)]
dict'  ('a', 1)  ('b', 2)
```

There's a shorthand notation for dictionaries with identifier keys:

```dg
dict  a: 1 b: 2
dict' a: 1 b: 2
```

Sets can only be created through an alias. There's no set literal.

```dg
set  'abcdabc'
set' 'a' 'd' 'c' 'b'
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

Sure. `name: value`.

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
print $ "> {}: {}".format "Karkat" "Reference something other than Doge"
```

##### Q: F# is better than Haskell.

In that case, use `<|` or `|>` instead.

```dg
print <| 'What' + 'ever.'
'This is the same thing ' + 'in a different direction.' |> print
```

Additionally, `something |>.attribute` is the same thing as `(something).attribute`.

```dg
'     wow     '.lstrip ' ' |>.rstrip ' ' |>.upper!
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

### External modules

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

There are some flags that modify the behavior of `import`. `pure` makes it, well, pure:
that is, it will not store the module in a variable (but will return it.)

```dg
# Assuming you haven't imported posixpath yet:
import '/posixpath' pure  #=> <module posixpath ...>
posixpath                 #=> NameError
```

`pure` also allows you to import a module even if you don't know its name until run-time:

```dg
name  = '/o'
name += 's'
import name       #=> SyntaxError
import name pure  #=> <module os ...>
```

While `import` normally returns the object that corresponds to the last item of the path,
`qualified` will make it return the first one instead:

```dg
import '/os/path' #=> <module somekindofpath ...>
import '/os/path' qualified #=> <module os ...>
```

`import` caches modules, meaning when called with the same module name, it will return
the same object instead of reloading the module every time. `reload` overrides that:

```dg
import '/os' reload
# `os.py` is re-evaluated.
```

(Note that if that's the first time you import a module, `reload` will import it *twice*.)

Obviously, you can combine these flags in one statement:

```dg
import '/xml/etree/ElementTree' qualified pure reload
#=> <module xml ...>
#   Only `ElementTree.py` is re-evaluated, and no variable is created.
```

### Assignment

```dg
such_variable = "much_constant"
```

##### Q: Where `such_variable` is?..

Any sequence of alphanumeric characters or underscores that does not start with a digit
and may end with an arbitrary amount of apostrophes.

```dg
__im_a_1337_VARIABLE'''''
```

If the value on the right side is a collection, it can be unpacked.

```dg
very_pattern, so_two_items, *rest = 3 * 'wow', 5 * 'sleep', 1 * 'eat', 2 * 'woof'
```

List syntax can be used, too. It means the exact same thing.

```dg
[a, b, *c, d] = 1, 2, 3, 4, 5
#=> a = 1
#   b = 2
#   c = [3, 4]
#   d = 5
```

Assignment is right-associative, so you can assign the same thing to many variables at once.

```dg
x = y = 1
```

##### Q: How do I modify variables defined in outside scopes? `=` seems to create a new local one.

Use `:=` instead.

```dg
outer = a ->
  inner = x -> (a = x)
  inner (a + 1)
  a

outer  #=> 5
```

```dg
outer = a ->
  inner = x -> (a := x)
  inner (a + 1)
  a

outer 5  #=> 6
```

This will change the value of the variable in the innermost scope it was defined with `=` in.
If there is no such scope, it is assumed to be global.

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

Anything that is valid to the left of `=` is also valid as an argument name.

```dg
snd = (whole_tuple = (a, b)) -> b
snd (1, 2) #=> 2
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
  yield from $ count (start + 1)
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

All of the above operators have an in-place form:

```dg
x += y  # sets x to (x + y)
x /= y  # sets x to (x / y)
x |= y  # you get the idea
```

Prefix:

```dg
~x # bitwise inversion
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

These should be pretty straightforward.

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

Call `break` with no arguments to stop the loop prematurely, or `continue` to skip
to the next iteration. The loop's return value will be `True` iff it was not broken.

```dg
ok = for x in range 10 =>
  if x == 5 => break!
  print x # 0..4
print ok  # False

ok = for x in range 10 =>
  if x == 11 => break!
  print x # 0..9
print ok  # True
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

Note, though, that since `where` creates a new scope, variables outside of it
can only be changed with `:=` (as if it were a function.)

### What does it have to do with...

OK, ready? `subclass` turns the local namespace into a class, and a local namespace
is exactly what `where` creates. Its arguments are base classes. The `metaclass`
keyword argument is optional.

```dg
ShibaInu = subclass object metaclass: type where
  cuteness = 80

  __init__ = self name ->
    # Don't forget to call the same method of the next base class.
    # Unless you completely override its behaviour, of course.
    super!.__init__!
    self.name = name
    # __init__ must always return None.
    # CPython limitation, not mine.
    None
```

If you ever get tired of writing `self`, change `->` to `~>`, `self.` to `@`,
and `super!.` to `@@`. A method with no arguments created with `~>` is automatically
converted into a property by calling `property` (so assigning something else to
`property` will change the behavior of `~>`).

```dg
Doge = subclass ShibaInu where
  __init__ = name ~>
    @@__init__ name
    @theOneAndOnly = True
    # `__init__` still has to return `None`.
    None

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

`::` is short for `isinstance`:

```dg
(1, 2, 3) :: tuple
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
