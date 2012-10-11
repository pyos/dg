## Installation

Since dg is a Python 3 module, barely any installation is required.
Simply [download the compiler](https://github.com/pyos/dg/zipball/master)
(or fetch it using git: `git clone https://github.com/pyos/dg.git`) and extract
the archive in a directory somewhere in your `$PYTHONPATH`
(e.g. `/usr/lib/python3.2/site-packages/`).

After installing, simply run dg as a module (i.e. with `-m`):

```bash
python3 [VM options] -m dg  # starts the REPL
python3 [VM options] -m dg file.dg [arguments]  # executes a file as a script
python3 [VM options] -m dg <<< "some code"  # this is a bash-specific syntax, called a "herestring"
```
