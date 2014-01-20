## dg

A (technically) simple language that compiles to CPython bytecode.

### Requirements

CPython 3.3 or 3.4 or any other Python VM with equivalent bytecode
(i.e. PyPy, although it does not implement Python 3.3 yet.)

### Installation

```sh
git clone https://github.com/pyos/dg.git
```

Then move the `dg` directory wherever Python looks for modules (site-packages,
`$PYTHONPATH`, a virtual environment, the current working directory, etc.)

### Usage

```sh
python -m dg
python -m dg file.dg argument1 argument2
python -m dg <<< "print 'Hello, World!'"
```

### More complex stuff

[http://pyos.github.io/dg/](http://pyos.github.io/dg/)
