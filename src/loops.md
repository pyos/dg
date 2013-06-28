## Imperative looping constructs

If there is a good imperative-style code, nobody can object to the fact that
it would probably contain some loops. That's why there are two kinds of these
in dg. Both are pretty simple, though.

`while` loops while a condition is satisfied, and returns the value
of its last iteration.

```dg
a = 0

while a < 5 =>
  print a
  a += 1
#=> Prints out 0, 1, 2, 3, 4; returns 5.
```

`for`, given a boolean expression, attempts to determine all possible
combinations of values that make that expression true, then evaluates
the body of a loop one time per each combination.

```dg
for a in range 5 =>
  print a

for a in range 5 and b in range 10 =>
  # Same as a `for b in range 10` inside `for a in range 5`.
  # AKA a cartesian product of `range 5` and `range 10`.
  print a b

for a and b =>
  # Prints out a single line, `True True`.
  print a b
```

Not actually a construct, but still pretty much imperative,
`exhaust` is a function that takes an iterable, evaluates each of its items,
and returns an empty deque.

```dg
# Does not do a damn thing.
it = map print (0..5)

# Prints out five lines.
exhaust it
```
