## Operators

Time for an implementation detail; function call is actually an operator.

```dg
print 'Hello' 'print' sep: ', ' end: '!\n'
#    ^-------^-------^---------^--- it's right here

print 'Hello' 'print' sep: ', ' end: '!\n'
#                        ^---------^--- another one, this time a colon
```

The "colon operator" is preferred over all others, excluding the dot.
"Empty operator" comes close, but still has lower priority.

```dg
3 +  print 'Hello' 'print'  sep: ', '   end: '!\n'
3 + (print 'Hello' 'print' (sep: ', ') (end: '!\n'))
```

Most of the operators don't require great detail. The only ones not found
in Python are:

```dg
# op    #=> `Python equivalent`
a!      #=> `a()`
a!.b    #=> `a().b`
a..b    #=> `range(a, b)`
a.~b    #=> `del a.b`
a !! b  #=> `a[b]`
a :: b  #=> `isinstance(a, b)`
a !!= b #=> `a = a[b]`
a !!~ b #=> `del a[b]`
```

Any function which is defined in the local/global scope can be used
as an operator; simply wrap its name in backticks, like in Haskell:

```dg
1 `max` 5 #=> 5
10 `divmod` 3 #=> (3, 1)
```

Some operators are [first-class](http://en.wikipedia.org/wiki/First-class_function).
The list is too long to write it here, so either use common sense (if an operator
doesn't have any fancy syntactic restrictions, then it's probably first-class)
or read the [source code](https://github.com/pyos/dg/blob/master/core/11.runtime.dg).

```dg
f = (+)
f 1 2 #=> 3
```

Any infix operator can be [partially bound](http://docs.python.org/dev/library/functools.html#functools.partial)
by omitting either of its sides. An exception to this is `-`, which behaves
as an unary `-` if the left side is missing.

```dg
f = (2 *)  #=> x -> 2 * x
f 10       #=> 20

g = in (1..5)  #=> x -> x in range 1 5
g  4           #=> True
g -2           #=> False

h = (- 5)  #=> negative five
```

This partial binding is the reason why singleton tuples can't be written as `(a,)`:

```dg
h = (1,) # x -> (1, x)
h 'this is not a singleton!' #=> (1, 'this is not a singleton!')
```
