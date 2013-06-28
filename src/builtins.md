## New built-ins

Since dg is clearly more oriented towards functional programming,
some of the combinators were moved to the built-in namespace and modified
to look more haskellish.

`foldl` is almost like `functools.reduce`:

```dg
sum = xs -> foldl (+) 0 xs
sum (list' 1 2 3)  #=> 6
```

`foldl1` is the same thing, but without a starting value:

```dg
# Unlike `sum`, this one does not work on an empty list.
sum1 = xs -> foldl1 (+) xs
sum1 (list' 1 2 3)  #=> 6
```

`scanl` and `scanl1` are similar, but also yield intermediate values.

```dg
accumulate = xs -> scanl1 (+) xs
accumulate (list' 1 2 3)  #=> 1, 3, 6
```

`bind` is `functools.partial`:

```dg
greet = bind print 'Hello' sep: ', ' end: '!\n'
greet 'World'
```

`flip` swaps the order of arguments of a binary function:

```dg
contains = flip (in)
(0..10) `contains` 3 #=> 3 in (0..10)
```

`<-` is a function composition operator:

```dg
dot_product = sum <- bind map (*)  #=> xs -> sum $ map (*) xs
dot_product (list' 1 3 5) (list' 2 4 6)  #=> 44
```

`takewhile` and `dropwhile` are imported from `itertools`:

```dg
until_zero = bind takewhile (0 !=)
until_zero $ list' 1 2 3 4 0 5 6 #=> 1, 2, 3, 4
```

`take` returns the first N items, and `drop` returns the rest:

```dg
take 5 (0..10) #=> 0, 1, 2, 3, 4
drop 5 (0..10) #=> 5, 6, 7, 8, 9
```

`iterate` repeatedly applies a function to some value:

```dg
count = x -> iterate (+ 1) x
count 5 #=> 5, 6, 7, 8, ...
```

`head`, `tail`, `fst`, `snd`, `init`, and `last` work like their Haskell
versions, but on all iterables (except for `init` and `last` — they only work
on collections that support slicing.)

```
       tail
    /--------\
[0, 1, 2, 3, 4]
 ^-- head

    init
 /--------\
[5, 6, 7, 8, 9]
             ^-- last

    ('a', 'b')
fst --^    ^-- snd
```
