### Core operators and functions

In order to provide interoperability with Python code (and, as a corollary,
be actually able to do anything) dg provides lots of built-in functions and operators
that translate directly to CPython bytecode. Here they are.

#### ..infix.. \\s ..:: (\.\.\. -> a) \.\.\. -> a..

Used to perform function calls.

```dg
a b c ...
```

#### ..special-case infix.. : ..:: no type..

When used in a function call, separates a name of the argument and its value.

```dg
function named_argument: its_value
```

Otherwise, triggers a syntax error.

```dg
i_say_syntax: you_say_error
```

#### ..infix.. \\n ..:: \.\.\. a -> a..

Evaluate all expressions from top to bottom, return the result of the last one.

```dg
a
b
c
...
```

#### ..infix.. = ..:: var a -> a..

Assign a name to some object. If the name does not exist in the current local scope,
create it. (This operator can overshadow non-local variables.)

```dg
a = b
```

If the "name" is actually a comma-separated list of names, assume the value
is an iterable and assign each name its own item from the iterable. Prefixing a
name with `*` will make it grab as much elements as it can and store them as a list.

```dg
a, b, c, *the_rest, d = some_iterable
```

#### ..infix.. := ..:: var a -> a..

Same as `:=`, but does not create a new local variable if one with the same name
was already defined in a parent scope (except for the global scope.)

```dg
a := b
```

#### ..infix/prefix/postfix.. -> ..:: argspec a -> (\.\.\. -> a)..

Create a function. If the argument list is omitted, it will accept no arguments.
If the body is omitted, it is assumed to return `None`.

```dg
arg ... -> body
```

#### ..infix/prefix/postfix.. ~> ..:: argspec a -> Either (\.\.\. -> a) property..

Same as `self ... -> ...`. If there are no other arguments, returns a `property` instead.

```dg
arg ... ~> body
```

#### ..first-class infix.. $ ..:: (a -> b) a -> b..

A reverse pipe (i.e. same as a space, but with low priority.)

```dg
a $ b
```

?? %div class="alert alert-info"
??   %h5 -> Q: What does "first-class" mean?
??   %p
??     A: this operator can be passed around as a generic function.
??     <code>map ($) xs ys</code>, for example, would be equivalent to
??     <code>map (x y -> x $ y) xs ys</code>.

#### ..postfix.. ! ..:: (-> a) -> a..

Call a function with no arguments.

```dg
a!
```

#### ..assignable infix.. . ..:: a var -> b..

Retrieve an attribute of an object by constant name.

```dg
a.name
```

?? %div class="alert alert-info"
??   %h5 -> Q: Assignable?
??   %p
??     A: this operator can be assigned to: <code>a.name = b</code>. In theory, this should
??     make <code>a.name</code> return <code>b</code> at any later point. In practice,
??     objects may override this behavior.

#### ..assignable prefix.. @ ..:: var -> a..

Same as `self.name`

```dg
@name
```

#### ..infix.. !. ..:: (-> a) var -> b..

`!` and `.` combined in one operator.

```dg
a!.name
```

#### ..infix.. .~ ..:: a var -> NoneType..

Remove an attribute that could have been accessed with `.`. Returns `None`.

```dg
a.~b
```

#### ..first-class infix.. , ..:: \.\.\. -> tuple a..

Create a tuple from its arguments.

```dg
a, b, c, ...
```

#### ..assignable first-class infix.. !! ..:: (Collection a b) a -> b..

Fetch an item from a collection by its index/key/whatever.

```dg
a !! b
```

#### ..in-place infix.. !!= ..:: (Collection a b) a -> b..

In-place equivalent of `!!`.

```dg
a !!= b
```

?? %div class="alert alert-info"
??   %h5 -> Q: Anything about in-place operators?
??   %p
??     A: In-place operators, in addition to returning the result,
??     assign it to their left-hand argument. Note that in-place operators may
??     choose to modify the contents of <code>a</code>, which will change ALL references
??     to the same object, not only <code>a</code> itself.

#### ..first-class infix.. !!~ ..:: (Collection a b) a -> NoneType..

Remove an item that was previously accessible as `a !! b`. Returns `None`.

```dg
a !!~ b
```

#### ..first-class infix.. standard math ..:: Number Number -> Number..

  * **+**:     addition.
  * **-**:     subtraction.
  * **\***:    multiplication.
  * **/**:     floating-point division.
  * **//**:    integer division.
  * **%**:     modulus.
  * **\*\***:  exponentiation.
  * **&**:     bitwise and/set intersection.
  * **|**:     bitwise or/set union.
  * **^**:     bitwise xor/symmetric difference.
  * **<<**:    bitwise left shift.
  * **>>**:    bitwise right shift.

```dg
a + b
```

#### ..in-place infix.. more standard math ..:: Number Number -> Number..

  * **+=**:    in-place addition.
  * **-=**:    in-place subtraction.
  * **\*=**:   in-place multiplication.
  * **/**:     in-place floating-point division.
  * **//**:    in-place integer division.
  * **%=**:    in-place modulus.
  * **\*\*=**: in-place exponentiation.
  * **&=**:    in-place bitwise and.
  * **|=**:    in-place bitwise or.
  * **^=**:    in-place bitwise xor.
  * **<<=**:   in-place bitwise left shift.
  * **>>=**:   in-place bitwise right shift.

```dg
a <<= b
```

#### ..prefix.. even more standard math ..:: Number -> Number..

  * **-**: numeric negation.
  * **~**: bitwise inversion.

```dg
-a
```

#### ..first-class chainable infix.. comparison ..:: a b -> bool..

  * **==**:    check for equality of two objects.
  * **!=**:    inverse of `==`.
  * **<**:     less than.
  * **<=**:    less than or equal to.
  * **>**:     greater than.
  * **>=**:    greater than or equal to.
  * **is**:    is actually the exact same object (as determined by pointers.)
  * **in**:    is a part of a collection.

```dg
a < b <= c
```

?? %div class="alert alert-info"
??   %h5 -> Q: Is that some sort of "how many buzzwords you can invent" competition?
??   %p
??     A: let R and Q be a combination of any of the above operators.
??     Then <code>a R b Q c</code> is equivalent to <code>a R b and b Q c</code>,
??     except <code>b</code> is only calculated once.

#### ..infix.. => ..:: a b -> Either a b..

If-then. Has a really low priority (lower than assignment!)

```dg
a => b  # b is only evaluated if a is true
```

Essentially the same thing as

#### ..infix.. and ..:: a b -> Either a b..

Evaluates the second argument only if the first is True. Also, boolean "and".

```dg
a and b
```

#### ..function.. break ..:: -> void..

Skip to the end of the loop. The loop itself will return `False`.

```dg
(for x in xs => break!) is False
```

#### ..function.. continue ..:: -> void..

Skip to the next iteration of the loop. Does not affect its return value.

```dg
(for x in xs => if x != 2 => continue!) is True
```

#### ..function.. except ..:: (var => a) \.\.\. -> a..

Basically a `try-catch` block. Its arguments must have the `u => v` form. Any exceptions
raised by `v` of the first argument are caught and stored as `u`. If no exceptions were
caught, `u` becomes `None`. The rest of the arguments are the same as in an `if` call;
if an exception was caught and any of the conditions matches, the exception is prevented
from propagating. Either the value of the matched condition or the value of the
exception-throwing block is returned. If the last condition is `finally`, its action
is evaluated anyway, but its value will never be returned (and it cannot `break` or
`continue` outside loops.)

```dg
except
  err => error_prone_function!
  err :: ZeroDivisionError => False, "Division by zero"
  err is None => True, "No errors"
  finally => print "all done"
```

#### ..function with a block.. for ..:: (var in a) => b -> bool..

`for` iterates over a collection, evaluating another expression once
for every item in it. The results of that expression are discarded.

```dg
for element in collection => do_something_with element
```

`for` is a loop, and therefore may contain calls to `break` or
`continue`; the return value will be `True` iff `break` was not called,
`False` otherwise.

```dg
didnt_find_4 = for element in collection => if element == 4 => break!
didnt_find_4 == not (4 in collection)
```

#### ..function.. if ..:: \.\.\. -> a..

`if` accepts multiple arguments of form `u => v`. For each of these arguments,
`u` is evaluated. If it returns a truthful value, `v` is evaluated, its value - returned;
otherwise, `if` goes on to the next argument. If no argument matched, `None` is returned.

```dg
if
  condition1 => value1
  condition2 => value2
  otherwise  => if_no_condition_matched
```

#### ..function.. import ..:: str \.\.\. -> a..

Given a POSIX-style path, `import` loads an external module for the Python VM,
stores it in the local namespace, then returns it.

```dg
import '/absolute' == absolute
import 'relative' == relative
import '../relative_from_parent' == relative_from_parent
import '/some_module/submodule' == submodule
```

If `qualified` is added to the call, `import` will store (and return) the root
instead of the leaf.

```dg
import '/some_module/submodule' qualified == some_module
```

#### ..first-class function.. list' ..:: \.\.\. -> [a]..

Given some arguments, cram them into a Python list.

```dg
list' 1 2 3
```

#### ..first-class function.. not ..:: \.\.\. -> bool..

Inverts the boolean meaning of an object. Note that this is a function, not an operator;
therefore, it obeys precedence rules of all function calls.

```dg
not (another_function argument)
```

#### ..infix.. or

Evaluates the second argument only if the first is False. Also, boolean "or".

```dg
a or b
```

#### ..function.. raise ..:: Exception -> void..

Stop execution immediately with an exception.

```dg
raise $ Exception 'a critical error has occured, cannot do anything'
```

Note that it always requires exactly one argument. To re-raise a previously catched
exception, pass it as an argument explicitly.

#### ..first-class function.. set' ..:: \.\.\. -> set a..

Given some arguments, create an immutable unordered collection (i.e. a set) that contains them.

```dg
set' 1 2 3
```

#### ..function.. subclass ..:: \.\.\. -> type..

Create a new type (aka class) that contains all the stuff from the local namespace
as attributes. It accepts any number of base classes as arguments, as well as
a special keyword argument `metaclass` and any keyword arguments the metaclass
can handle (hint: the default metaclass, `type`, can handle none.)

```dg
a = 1
b = 2
T = subclass object
```

?? %div class="alert alert-info"
??   %h5 -> Q: How do I create a new local namespace?
??   %p
??     A: with <code>where</code>. See below.

#### ..first-class function.. tuple' ..:: \.\.\. -> tuple a..

Does the same thing as a comma.

```dg
tuple' 1 2 3 == (1, 2, 3)
```

#### ..infix.. where ..:: a b -> a..

Limit visibility of variables to a single expression.

```dg
a where a = b
```

Works by creating a new local namespace, synergizing with `subclass`.

```dg
T = subclass object where
  a = 1
  b = 2
```

Can be used to implement generator expressions in conjunction with `yield`.

```dg
(where for x in xs => yield $ x * 2)
```

#### ..function with a block.. while ..:: bool => a -> bool..

If the condition is `True`, evaluate an expression and repeat. Returns `True` if
the condition became `False`; `False` if forcibly stopped by calling `break`.

```dg
x = 0
while x != 10 =>
  x += 1
```

#### ..function with a block.. with ..:: (Either (a = b) b) => c -> c..

1. Call `b`'s `__enter__` method.
2. Optionally, assign it to `a`.
3. Evaluate `c`.
4. Call `b`'s `__exit__` method (even if `c` failed.)
5. Return the value of `c`.

```dg
x = with fd = open 'README.md' => fd.read!
# `x` contains the contents of README.md.
# `fd` was automatically closed.
```

#### ..function.. yield ..:: a -> b..

The existence of calls to this in a function makes it a generator. Instead
of returning values, generators `yield` them; these values are then retrieved
from the outside using the standard iterator protocol.

```dg
counter = x ->
  while True =>
    yield x
    x += 1

for x in counter 5 => ...
```

When there are no more values to be `yield`ed, the generator raises `StopIteration`.
Its `value` attribute is the value returned by the generator (i.e. the last expression
evaluated.)

If an outside coroutine decides to pass some object into the generator using
the `send` method, `yield` will return that value.
