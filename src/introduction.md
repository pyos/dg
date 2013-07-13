## Example-based documentation

### Comments

```dg
# are sh-style.
```

You can also describe functions with docstrings in the same way as in Python.

```dg
function = argument ->
  '''Do something with an argument.

      :param argument: any value.

      :return: something absolutely different.

  '''
  something_absolutely_different
```

### Parentheses

are used to explicitly define the precedence of operators, obviously.

```dg
2 *  2 + 2  == 6
2 * (2 + 2) == 8
```

Indentation can be used for the same thing. Basically, an indented block
is equivalent to a parenthesized expression, with an added bonus of being able
to evaluate multiple statements.

```dg
2 *
  print "calculating 2 + 2"
  2 + 2
# still returns 8, but also logs its activity
```

If an indented block was not preceded by an operator, each statement
is added as an argument to the preceding function call instead.

```dg
# Same damn thing.
print a (b + 1) sep: ';'
print a (b + 1)
  sep: ';'
print
  a
  b + 1
  sep: ';'
```

Unlike Python, an empty pair of parentheses (`()`, that is) evaluates to
`None`, not an empty tuple, and may be used as a NOP (much like `pass` in Python.)

```dg
do_nothing_with_nothing = () -> ()
```

As you have probably noticed, arguments in function calls are separated
by spaces (ML/sh style), not parentheses-and-commas (C/Python style.)

```dg
print (1 + 1) "equals to 2" # Yeah.
```

### Assignment

The usual pythonic `=` is back for another round. Values can be assigned
to variables, attributes, and subitems (including slices.) Also,
iterable values can be [unpacked](http://www.python.org/dev/peps/pep-3132/).

There is no `global` keyword. You can't change global variables.
That was considered harmful. There is no `nonlocal` keyword either.
Every variable from a closure is `nonlocal` by default. Doesn't really matter,
since you'd have to watch out for name collisions either way.

### Referential transparency, laziness, and other buzzwords.

It's not Haskell. dg guarantees neither of these.
