## Modules

*(The current import function is not very good; it will probably be changed later.)*

`import` is an alias to [importlib.import_module](http://docs.python.org/dev/library/importlib.html#importlib.import_module).

```dg
module    = import 'os'
submodule = import '.submodule' package: __package__
```

As a special case, when `import` is called without any arguments, dg will
attempt to infer the module name from the variable name. In that case
a variable name can be a dotted path, prefixed by any number of dots:

```dg
os  = import!
sys = import!

importlib.util = import!

.submodule = import!
```
