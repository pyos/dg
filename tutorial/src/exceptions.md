## Exceptions

Throw exceptions with the `raise` function. It accepts classes that derive
from BaseException as its argument, as well as their instances.

```dg
raise Exception
raise ValueError
raise $ TypeError "something happened, I don't know what"
```

`raise` has an optional second argument `cause`. When specified,
it defines the [cause](http://www.python.org/dev/peps/pep-3134/) of the exception.
(Could've guessed it, really.)

```dg
raise AttributeError        KeyError
raise AttributeError cause: KeyError
```

Exceptions can be caught with the `except` function. The syntax is the same
as for `if`, with two differences. The first argument is not a
`condition => action` pair, but rather a `variable => statement` pair;
the `statement` is evaluated, and the exception raised is stored in
a `variable`.

```dg
except
  error =>
    i = int '1234567890a'
    f = open '/etc/hostname' 'wb'
    f.write i
```

All other arguments are conditional expressions, just like in `if`.
Any matching condition silences the exception and prevents other conditions
from evaluating. Use `::` (or `isinstance`) to check the exception's type:

```dg
  error :: ValueError => print 'Hey, that wasn\'t a decimal number!'
```

As in `if`, conditions may be completely arbitrary.

```dg
  error :: (OSError, IOError) and error.errno == 13 => print 'Permission denied'
```

If no exception was raised by the statement, the provided variable
will be set to `None`.

```dg
  error is None => raise $ AssertionError 'but that code was clearly incorrect!'
```

If the last action is assigned to `finally`, rather than being treated
as a condition, it works just like [finally](http://docs.python.org/dev/reference/compound_stmts.html#finally)
in Python (wow, who would've thought.) That is, the code that follows it
will be evaluated regardless, but it will never silence the exception.

```dg
  finally =>
    print 'cleaning up temporary files'
    system 'rm -rf /*'
```

Calls to `except` return the same value as an `if` would.

```dg
except e => open 'README.md'
       e is None    => True
       e :: IOError => False
#=> True if successful in opening README.md, False if an IOError was caught

except e => open 'README.md'
       e :: IOError => e.errno
       finally      => 2 + 2
#=> a file descriptior if successful, an error code if an IOError was caught.
#   2 + 2 is evaluated, its value — ignored.
```
