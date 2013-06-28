## Conditionals

`or` and `and` can be used as conditionals, in addition to being Boolean
operators. `a or b` means `a if a else b`, and `a and b` means
`b if a else a` (of course, they only evaluate `a` once.)

```dg
True or  print 1 #=> True (does not print anything)
True and print 1 #=> None (also prints 1)
```

`=>` is an alias for `and`. It may seem the same, but it's semantically different.
While `and` is used in boolean expressions, `=>` is used in imperative code
in place of a single-clause `if`.

```dg
print 1

input 'did you see that? ' == 'no' =>
  print 'i said,' 1
```

The only other conditional is `if`. Each of its arguments should be in
`condition => action` form. The first action mapped to a true condition is
evaluated, the rest is ignored. Conditions may be completely arbitrary.

```dg
factorial = n -> if
  n < 0     => raise $ ValueError 'n >= 0'
  n < 2     => 1
  otherwise => n * factorial (n - 1)
```

(`otherwise` is just an alias for `True`, not a keyword.)

The first condition may be placed on the same line as `if`. That doesn't work
in the REPL, though, as it assumes you're done entering a command.

```dg
fibonacchi = n -> if n < 0     => raise $ ValueError 'n >= 0'
                     n < 2     => n
                     otherwise => fibonacchi (n - 1) + fibonacchi (n - 2)
```

In fact, it is completely possible to place all conditions on one line.
Each must be wrapped in parentheses, though.

```dg
abs = x -> if (x >= 0 => x) (otherwise => -x)
```

Be ware, though, that `if` always consumes everything until the end of the
line/block. Once you write it, there's no going back.

```dg
1 +  if (x >= 0 => x) (otherwise => -x)  + 2  # syntax error
1 + (if (x >= 0 => x) (otherwise => -x)) + 2  # correct version
```
