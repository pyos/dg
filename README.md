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

## Unsupported features

1. `try/except/else/finally` clauses produce very complex bytecode sequences I was unable to decode so far. Maybe later.
2. `if/elif/else` is not something I've started working on.
3. Methods lack `__class__` cell; `super` needs both arguments to work correctly.
4. Functions only support positional arguments with no default values. Support for defaults, keyword-only arguments, var(kw)args and annotations will be implemented later.
5. Most of the operators are not available yet, but they are easy to implement. Alternatively, you may defined them at runtime by doing tricks like `operator = import; // = operator.truediv`
6. Only absolute imports.

## Did you just *assign to an operator*?

Yeah, using `dg` as a parser allows you to do cool things that may impress your
friends (if they don't know about [Haskell](http://www.haskell.org/).)

### Examples are (sometimes) better than words.

```python

dis = import      # import dis
os.path = import  # import os.path

f a b = print a 'and' b 'are the arguments you called `f` with'

# Alternative syntax for function definition.
# `\args: ...` is actually an anonymous function.
# Don't forget to put a space between the slash and the colon if there
# are no arguments.
g = \x:

    print "Did you know that the colon right there"
    print "can be replaced with a dollar sign?"
    print "(Oh, and this anonymous function spans multiple lines!)"
    print "By the way, `x` was" x

# That's how you call a function.
# Prints "1 and 2 are the arguments you called `f` with".
f 1 2

# Syntax for calling functions without arguments is not so neat.
# It's `:function`. Or `$function`. But not `function`.
g (:object)

# There's no alternative syntax for function calls.
# `(x, y)` here is just a tuple.
# As in Haskell, `f a + b + c` is parsed as `((f a) + b) + c`.
$@%^ = \x y: max (x, y) + x + y

# $ is the best operator in the world.
# Equivalent to `print (567 $@%^ 123 $@%^ 41823548)`.
print $ 567 $@%^ 123 $@%^ 41823548

# Yes, classes are supported, too.
# And they are anonymous! (Unless you bind them to a name like in this example.)
# `object` may be omitted 'cause that's the default base class, like in Python.
A = inherit object:

    a = 1
    b = 2

    __init__ self =

        # Does not work yet 'cause there is no __class__ free variable.
        #:(:super).__init__
        :(super A self).__init__

        print "Created an instance of A"

print $ isinstance (:A) A  # True, obviously.

# Items and attiributes work!
a = :dict
b = :(inherit ())

a !! 'b' = 'c'
b.c = 'd'

print (a !! 'b') b.c  # c d
```

