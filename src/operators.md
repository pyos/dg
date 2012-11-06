## Operators

Time for an implementation detail; function call is actually an operator.

```dg
doubleIf (== 2) 2
#       ^------^--- it's right here

doubleIf (== 2) x: 2
#                ^-- another one, this time a colon
```

The "colon operator" is preferred over all others, excluding the dot.
"Empty operator" comes close, but still has lower priority.

```dg
3 +  doubleIf  x: 2  (== 2)
3 + (doubleIf (x: 2) (== 2))
```

Most of the operators don't require great detail. The only ones not found
in Python are:

```dg
# op    #=> `Python equivalent`
a!      #=> `a()`
!a      #=> `not a` (not recommended, use `not` instead)
a!.b    #=> `a().b`
a.~b    #=> `del a.b`
a !! b  #=> `a[b]`
a !!= b #=> `a = a[b]`
a !!~ b #=> `del a[b]`
```

Any function which is defined in the local/global scope can be used
as an operator; simply wrap its name in backticks, like in Haskell:

```dg
1 `max` 5 #=> 5
10 `divmod` 3 #=> (3, 1)
```

Operators marked as "available at runtime" are [first-class](http://en.wikipedia.org/wiki/First-class_function);
most of these are imported from the [operator](http://docs.python.org/dev/library/operator.html)
module.

```dg
f = (+)
f 1 2 #=> 3
```

One special feature of first-class operators is the ability to *partially bind* them.

```dg
f = (2 *)  # x -> 2 * x
f 10       #=> 20

g = in (1..5)  # x -> x in (1..5)
g  4  #=> True
g -2  #=> False
```

This partial binding is the reason why singleton tuples can't be written as `(a,)`:

```dg
h = (1,) # x -> (1, x)
h 'this is not a singleton!' #=> (1, 'this is not a singleton!')
```

It is possible to define new operators if their names conform to 2 rules:

  * it must consist of characters in `!$%&*+-./:<=>?@\^|~` or commas (**not both** at the same time — `$,` is invalid;) and
  * it must not start with one or more asterisks followed by a colon (`***:!` is not valid, but `:***:!` is.)

```dg
(<>) = (x y) -> (x ** 2 + y ** 2) ** 0.5
3 <> 4 #=> 5.0
```
