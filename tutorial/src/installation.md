## Installation

Freaking easy:

1. download the compiler (why don't you look at the [index page](/) for that?);
2. put the "dg" directory somewhere in `$PYTHONPATH`, or `/usr/lib/python3.*/site-packages/`, or a virtual environment. In fact, if you don't want to install it system-wide, just leave it alone: Python always scans the current working directory for modules.

### Usage

Even easier.

```bash
python3 -m dg  # REPL!
python3 -m dg file.dg --do-something-useful-this-time  # Script!
```

##### Q: How to run some code from a shell?

A: Use your shell's herestring/heredoc.

```bash
python3 -m dg <<< "some code"
```

##### Q: How to run some code from a shell *and* be able to use stdin?

A: ...

## `runpy` support

Fully complete since Python 3.3. Simply import `dg` somewhere in `__init__.py`, and bam,
your package is now runpy-compatible.

##### Q: What's `runpy`?

A: That's the thing you use when you do `python -m`.
