[dg](https://github.com/pyos/dg)
is a ~~simple-as-in-LISP~~ functional/object-oriented language that compiles to
[CPython](http://python.org/) [bytecode](http://docs.python.org/dev/library/dis.html).

```dg
hello = print <- 'Hello, {}!'.format
hello 'dg'
```

Since it runs on the same VM, it can fully interoperate with any Python 3
code, from simple modules to stuff full of magic. dg code itself can be imported,
too; just make sure you load the compiler first:

```dg
# my_module.dg
flask = import!

app   = flask.Flask __name__
hello = (app.route '/') (-> 'Hello World!')

app.run! if __name__ == '__main__'
```

```python
# __main__.py
import dg
import my_module

my_module.app.run()
```

Unlike Python, dg does not attempt to be an "interpreted pseudocode";
instead, it follows the "learn more, do less" principle.
