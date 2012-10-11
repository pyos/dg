## Objects

Creating a type is done by calling `inherit` with class body.

```dg
Animal = inherit $
  __init__ = (self name) ->
    super!.__init__!
    self.name = name
    # __init__ must always return None.
    None

Movable = inherit $
  move = (self distance) ->
    # Inches? Feet? Miles? Nah.
    '{} moved {} meters.'.format self.name distance
```

`inherit` also accepts any number of base classes, as well as keyword arguments.

```dg
Horse = inherit Movable Animal metaclass: type $
  gallop = self ->
    self.move 40
```

Instantiating a class is done by calling it.

```dg
sam = Horse 'Sam'
sam.gallop!
```
