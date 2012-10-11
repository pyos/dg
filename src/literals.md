## Literals

Compile-time constants:

```dg
42                      # `int` (of arbitrary length)
0b01010111              # `int` (in base 2)
0o755                   # `int` (in base 8)
0xDEADF00D              # `int` (in base 16; may be lowercase, too)
3.14159265358979323865  # `float`
6.959500E+9             # `float` (in scientific notation)
1j                      # Imaginary number (of type `complex`)

'A string!'
"It may be double-quoted, too."
'Any of these
can have line breaks in them, as well as\n escapes and Unicode characters ☺'

r'raw strings preserve \backslashes, but do not support escapes'
b'binary strings represent non-string data, and can only contain ASCII'
rb'guess what raw binary strings do'

'''More quotes is always better.'''
"""Am I right?"""
```

Runtime constants:

```dg
True   # Tautology
False  # Contradiction
None   # The only instance of the unit type, NoneType
```

Tuples are ordered immutable collections:

```dg
2, True, 'this tuple contains random stuff'
```

Empty tuple does not have a special syntax.

```dg
tuple! # this one is empty
```

Note that using `tuple'` is the only way to create
a singleton tuple. Why would you want to do that? Use lists.

```dg
tuple' "Fine, have your singleton."
```

There is no special syntax for lists, either. Call `list` to make a list
out of another collection, or `list'` to create one from distinct elements:

```dg
list  (0..5)
list'  0 1 2 3 4
```

Same thing applies to sets...

```dg
set  'abcdabc'
set' 'a' 'd' 'c' b'
```

...and dictionaries, aka hashmaps. The latter require an iterable of *pairs*,
(i.e. 2-tuples,) though.

```dg
dict $ list' ('a', 1) ('b', 2)
dict'        ('a', 1) ('b', 2)
```

There's a shorthand notation for dictionaries with identifier keys:

```dg
dict  a: 1 b: 2
dict' a: 1 b: 2
```

And don't forget about line continuation:

```dg
dict'
  'a', 1
  'b', 2
```
