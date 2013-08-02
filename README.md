## dg

A (technically) simple language that compiles to CPython bytecode.

### Requirements

CPython 3.3 or 3.4 or any other Python VM with equivalent bytecode
(never seen them, except for maybe PyPy, although it does not
implement Python 3.3 yet, so can't confirm that.)

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
python -m dg --rebuild
# Recompile the bundle for a specific target
# (NOTE: it's not recommended to use new versions of Python to compile bundles
#  for old ones. In particular, Python 3.4 has a new marshalling protocol that
#  Python 3.3 does not support. Also, run `-m dg --build` with no arguments
#  using that version of Python afterwards to make sure the bundle
#  is as optimized as it can be: bundles created with Python 3.4, for example,
#  are about 30% smaller than ones created with Python 3.3.)
python -m dg --rebuild --version 0x03040000 --tag cpython-34
```

### Hello, World!

```dg
print "Hello, World!"
print (str.capitalize "hello") "world".capitalize! sep: ", " end: "!\n"
```

### More complex stuff

[http://pyos.github.io/dg/](http://pyos.github.io/dg/)
