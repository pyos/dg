## Imperative constructs

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

`for` [iterates over a collection](http://en.wikipedia.org/wiki/Foreach_loop).

```dg
for a in range 5 =>
  print a

# Anything that can be assigned to is allowed in `for`.
for locals! !! 'a' in range 5 =>
  print a

for (a, b) in zip (1..6) (3..8) =>
  # 1 3
  # ...
  # 5 7
  print a b
```

`with` has the same syntax as the other two, and is used to
enter [contexts](http://www.python.org/dev/peps/pep-0343/).

```dg
with fd = open '__init__.py' =>
  print $ fd.read 5
  #=> first 5 characters of __init__.py

fd.read 5
#=> IOError: fd is closed
```

Note that these names are not keywords; you can still name attributes `for`,
`while`, and `with`:

```dg
A = subclass object
A.for = x ~> print self x

a = A!
a.for 2  #=> <A object at ...> 2
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
