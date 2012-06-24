# asd

[dg](https://github.com/pyos/dg) to CPython byte-compiler.

### Wait, what?

In case you don't know that already, CPython is just a stack-based virtual
machine with a built-in Python to CPython compiler. This module is similar
to that compiler part, but it a) accepts dg structures instead of Python
programs; and b) produces less tested and less optimized output.

### What a good name for a compiler.

As you may have already noticed, I have some problems thinking of project names.
Got any suggestions?

## Requirements

 * [dg](https://github.com/pyos/dg)
 * [interactive](https://github.com/pyos/interactive)

## Unsupported features

1. `try/except/else/finally` clauses produce very complex bytecode sequences I was unable to decode so far. Maybe later.
2. `if/elif/else` is not something I've started working on.
3. Methods lack `__class__` cell; `super` needs both arguments to work correctly.
4. Functions only support positional arguments with no default values. Support for defaults, keyword-only arguments, var(kw)args and annotations will be implemented later.
5. Most of the operators are not available yet, but they are easy to implement. Alternatively, you may define them at runtime by doing tricks like `operator = import; // = operator.truediv`
6. Only absolute imports.

## Did you just *assign to an operator*?

Yeah, using `dg` as a parser allows you to do cool things that may impress your
friends (if they don't know about [Haskell](http://www.haskell.org/).)

### Examples are (sometimes) better than words.

```python
dis = import      # import dis
os.path = import  # import os.path

# Function definition syntax was borrowed from CoffeeScript.
f = (a, b) -> print a 'and' b 'are the arguments you called `f` with'

# That's how you call a function.
f 1 2

# You may omit the parentheses if a function has only one argument.
h = x -> y -> x + y

# As always, parentheses can be used to explicitly set the order of operations.
(h 2) 3

# You may define your own operators, but you can't set their precedence,
# at least for now. Parentheses in the left-hand statement are optional.
#
# There's no alternative syntax for function calls.
# `(x, y)` here is just a tuple.
#
$@%^ = (x, y) -> max (x, y) + x + y

# $ is the best operator in the world.
# Equivalent to `print (567 $@%^ 123 $@%^ 41823548)`.
print $ 567 $@%^ 123 $@%^ 41823548

# Classes are supported, too. And they are anonymous by default!
# (Unless you bind them to a name like in this example.)
A = inherit object:
  a = 1
  b = 2

  __init__ = (self) ->
    # Argumentless `super` does not work yet
    # because there is no `__class__` free variable.
    #:(:super).__init__
    :(super A self).__init__

    print "Created an instance of A"

print $ isinstance (:A) A

# Subscription syntax is similar to that in Haskell, not Python.
a = :dict
a !! 'b' = 'c'
print (a !! 'b')
```

