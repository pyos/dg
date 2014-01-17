## Objects and types

`subclass` duplicates the current local namespace as a type.

```dg
__init__ = self name ->
  self.name = name
  # __init__ must always return None.
  None

Animal = subclass object
```

It accepts any number of base classes, as well as keyword arguments.

```dg
# Make sure to clean the local namespace before running this.
# Don't worry, you'll only have to do that once more
# before you'll see a better way of defining attributes.
move = self distance ->
  # Inches? Feet? Miles? Nah.
  '{} moved {} meters.'.format self.name distance

Movable = subclass object
```

```dg
gallop = property $ self ->
  self.move 10

Horse = subclass Movable Animal metaclass: type
```

Instantiating a class is done by calling it, as in Python.

```dg
sam = Horse 'Sam'
sam.gallop
```

Now, it is not very easy to reset the namespace every time you need
to create a class. That is why there is

### Local name binding

Also known among Python devs as ["given" clause](http://www.python.org/dev/peps/pep-3150/).

In simplier terms, writing `a where b` evaluates `a` in a new local namespace
defined only by `b`.

```dg
Frog = subclass Movable Animal where
  # None of the crap we defined above will make it into this class.
  leap = property $ self ->
    self.move 20
```

It also works with...well, anything.

```dg
print a where
  b = 1
  print 'calculating a'
  a = b + 2
#=> calculating a
#=> 3
print a
#=> OH GOD NAMEERROR
```

Also, for those who like Ruby syntax, there are

### Fancy aliases

`@attribute` is an alias for `self.attribute`.

```dg
Movable.move = self distance -> '{} moved {} meters.'.format @name distance
Frog.leap = property $ self -> @move 20
```

`~>` is a method constructor. It works the same way as `->`, but inserts `self`
into the argument list in addition to doing the generic function creation stuff.
If there are no other arguments, the created method is automatically
transformed into a property.

```dg
Movable.move = distance ~> '{} moved {} meters.'.format @name distance
Frog.leap = ~> @move 20
```
