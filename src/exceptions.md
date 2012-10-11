## Exceptions

Throw exceptions with the `raise` function. It accepts classes that derive
from BaseException as its argument, as well as their instances.

```dg
raise Exception
raise ValueError
raise $ TypeError "something happened, I don't know what"
```

`raise` has an optional second argument `caused_by`. When specified,
it defines the [cause](http://www.python.org/dev/peps/pep-3134/) of the exception.
In Python 3.3, setting the cause also [silences the context](http://www.python.org/dev/peps/pep-0409/).

```dg
raise AttributeError caused_by: KeyError
```

Exceptions can be caught with the `unsafe` function; its syntax is similar
to `switch`. The first argument is in form `name = expression`,
where `expression` is what to evaluate and `name` if where to store
the exception, if any was thrown.

```dg
unsafe
  error =
    i = int '1234567890a'
    f = open '/etc/hostname' 'wb'
    f.write i
```

All other arguments are conditional expressions, just like in switch.
Any matching condition silences the exception and prevents other conditions
from evaluating. Use `::` (or `isinstance`) to check the exception's type:

```dg
  error :: ValueError =
    print 'Hey, that wasn\'t a decimal number!'
```

As in switch, conditions may be of arbitrary complexity and they are not required
to reference the exception at all.

```dg
  error :: (OSError, IOError) and error.errno == 13 =
    print 'Permission denied'
  admin_is_watching =
    # Don't attract his attention with colorful tracebacks.
    print 'Psst, user!' error
```

If no exception was caught, the provided variable will be set to `None`.

```dg
  error is None =
    raise $ AssertionError 'Wait, but that code was obviously incorrect!'
```

If the last action is assigned to `True`, rather than being treated
as a condition, it works just like [finally](http://docs.python.org/dev/reference/compound_stmts.html#finally)
in Python. That is, it will be evaluated even if any other condition matched,
but in any case it won't silence the exception.

```dg
  True =
    print 'Nothing to clean up.'
```

As any other expression, calls to `unsafe` return a value:

  * the value of `expression` if no exception was raised;
  * `None` if an exception was silenced.

(Obviously, it doesn't return if an exception was propagated to the caller.)

```dg
file = unsafe
  e = open 'README.md'
  # Not having a README isn't critical, but `file` will be `None`.
  e :: IOError = print 'Warning: no README.'
```
