## Installation

Freaking easy:

1. [download the compiler](https://github.com/pyos/dg/zipball/master) OR fetch it with git: `git clone https://github.com/pyos/dg.git`;
2. put the "dg" directory somewhere in `$PYTHONPATH`, or `/usr/lib/python3.*/site-packages/`, or a virtual environment. In fact, if you don't want to install it system-wide, just leave it alone: Python always scans the current working directory for modules.

### Usage

Even easier.

```bash
# Start the REPL (supports $PYTHONSTARTUP
# in case you want to customize the prompt or whatever):
python3 [VM options] -m dg
# Execute a script:
python3 [VM options] -m dg file.dg [arguments]
# Execute "some code":
python3 [VM options] -m dg <<< "some code"
python3 [VM options] -m dg <<EOF
some code
EOF
```

### Writing runnable packages in dg

If you wish to [make your package runnable](http://docs.python.org/dev/using/cmdline.html#cmdoption-m),
simply import `dg` somewhere in `__init__.py` of that package and add
a `__main__.dg`. Python's import machinery will do the rest.
