## Conditionals

`or` and `and` can be treated as conditionals, in addition to being Boolean
operators. `a or b` means `a if a else b`, and `a and b` means
`b if a else a` (of course, they only evaluate `a` once.)

```dg
True or  print 1 #=> True (does not print anything)
True and print 1 #=> None (also prints 1)
```

"if-else" can be used in its infix form.
Note that `if` and `else` have really low priority — you will
probably want to wrap them in parentheses. "else" clause can be omitted.

```dg
'ok' if 2 < 5 else 'wat' #=> 'ok'
```

The most powerful, and the simpliest, conditional is `switch`, which
is actually not "switch-case", but "if-else if".

```dg
factorial = n -> switch
```

`switch` only accepts expressions in form `condition = value` as its *arguments*
(remember to use the line continuation!) The first value assigned to a true
condition is evaluated.

```dg
  n < 0 = raise $ ValueError 'n >= 0'
  n < 2 = 1
```

Conditions don't have to reference the same variable; they may be completely
arbitrary. Make use of the fact that `True` is always true to do something
if everything else fails.

```dg
  True  = n * factorial (n - 1)
```
