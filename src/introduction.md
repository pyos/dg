## Tutorial
### Parentheses and indentation

mean the same thing: they explicitly define the precedence of operators.

```dg
a, b, c = 1, 2, 3

# The following expressions are identical.
a * (b + c)
a *
  b + c
```

To find out whether you need to use parentheses, see
[the operator precedence table](#operator-table) below.

The indentation, however, has one more effect.
Aside from grouping expressions on the right side of an operator,
it also serves as a line continuation. When used straight after a function call
(or a function name), each line of the indented block is a separate argument.

```dg
print a b sep: ';'
print
  a
  b
  sep: ';'
```

Unlike Python, an empty pair of parentheses (`()`, that is) evaluates to
`None`, not an empty tuple, and should be used as an empty placeholder block.

Note that dg doesn't require you to use parentheses when calling
functions, nor does it support that at all. The contents of the parentheses
will be treated as if that was an object:

```dg
print()  # print None
print(1) # print 1
print(1).bit_length! # print (1.bit_length!)
```

### Comments

```dg
# are sh-style up to the end of the line
```

There are no docstrings in dg. In fact, there aren't any in Python, too;
paradoxically, these facts together mean that you *can* use them:

```dg
f = () ->
  '''
    I hear you asking "WTF?"
    In Python, "docstring" is simply the first constant used in a function...

    ...if it's a string. `None` otherwise.

  '''
  # Unless the next line is present, calling `f` will return its docstring.
  None
```

By the way, creating strings that aren't used anywhere is another,
though not recommended, way of writing comments.


### Assignment

is done the usual way. Where's the catch?

1. no `global` keyword — don't change global variables from inside functions. "It would work faster that way" is not an excuse.
2. no `nonlocal` keyword — if a variable is created in a closure, it's `nonlocal` by default.

```dg
my_type   = inherit object ()
my_dict   = dict!
my_object = my_type!

my_variable = 'oh hi'
my_dict !! 'my_key' = 'my_dict["my_key"] = ...'
my_object.my_attribute = 12345

the, *world, (is_, mine) = 'but', '"is"', 'is', 'a', ('reserved', 'name')
the   == 'but'
world == list' '"is"' 'is' 'a'
is_   == 'reserved'
mine  == 'name'
```

Oh, you can also assign to values. If both sides of an assignment are equal, nothing will happen; otherwise, a `PatternMatchError` will be raised.

```dg
1 = 1  # ok
4 / 2 = 1  # PatternMatchError(received=1, expected=2.0)
```

### Referential transparency, laziness, and other buzzwords.

There aren't any of these in dg. As in pure Python, the code is as side effect
free as you write it, and all expressions are evaluated eagerly.

But there *is* one trendy feature: everything is an expression! That means
it is possible to create multi-line anonymous functions (aka "lambdas"),
anonymous classes, and even catch exceptions while calling a function.
(That doesn't mean that everything returns a value that makes sense, though.)
