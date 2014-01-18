## dg

A (technically) simple language that compiles to CPython bytecode.

### Requirements

CPython 3.3 or 3.4 or any other Python VM with equivalent bytecode
(i.e. PyPy, although it does not implement Python 3.3 yet.)

#### Why not Python 3.2?

dg can be modified to support 3.2, but what's the point? If there was
a JIT-enabled PyPy 3.2 that could be a possibility, though.

Anyway, a list of differences:

  * 3.2's `runpy` cannot use module loaders to import __main__. Therefore, a __main__.py is needed; it should remove `dg.__main__` from `sys.modules`, then reimport it.
  * 3.2 does not have a `FileFinder` in its importlib; a simple meta path finder is required. Also, `importlib.machinery.SourceFileLoader` is `importlib._bootstrap._SourceFileLoader`.
  * `__qualname__` wasn't introduced until 3.3. In 3.2, `MAKE_CLOSURE` takes one less item from the stack.
  * `sys.implementation.cache_tag` did not exist, either. `platform.python_implementation().lower() + '-32'` may be used for something similar.

### Installation

```sh
git clone https://github.com/pyos/dg.git
```

Then move the `dg` directory wherever Python looks for modules (site-packages,
`$PYTHONPATH`, a virtual environment, the current working directory, etc.)

### Usage

```sh
# Start the REPL
python -m dg
# Run a script
python -m dg file.dg argument1 argument2
# Run a single command
python -m dg <<< stuff
# Run a package, assuming there is an "import dg" in its __init__.py
python -m package_name

# Recompile the bundle for your interpreter
python -m dg --build
# Recompile the bundle for a specific target
# (NOTE: it's not recommended to use new versions of Python to compile bundles
#  for old ones. In particular, Python 3.4 has a new marshalling protocol that
#  Python 3.3 does not support. Also, run `-m dg --build` with no arguments
#  using that version of Python afterwards to make sure the bundle
#  is as optimized as it can be: bundles created with Python 3.4, for example,
#  are about 30% smaller than ones created with Python 3.3.)
python -m dg --build cpython-34,0x03040000
```

### Hello, World!

```dg
print "Hello, World!"
print (str.capitalize "hello") "world".capitalize! sep: ", " end: "!\n"
```

### More complex stuff

[http://pyos.github.io/dg/](http://pyos.github.io/dg/)
