## dg

A (technically) simple language that compiles to CPython bytecode.

### Requirements

CPython 3.4 or any other Python VM with equivalent bytecode
(i.e. PyPy, although it does not implement Python 3.4 yet.)

### Installation

```sh
pip3 install git+https://github.com/pyos/dg
```

### Usage

```sh
python -m dg
python -m dg file.dg argument1 argument2
python -m dg <<< "print 'Hello, World!'"
```

### More complex stuff

[http://pyos.github.io/dg/](http://pyos.github.io/dg/)

### Text editor support

 * [Sublime Text and TextMate bundle](https://github.com/pyos/dg-textmate)
 * [GEdit/GtkSourceView syntax definition](https://github.com/pyos/dg-gedit)
 * [vim plugin](https://github.com/rubik/vim-dg) (courtesy of [Michele Lacchia](https://github.com/rubik))
 * [Atom syntax](https://atom.io/packages/language-dg) (by [Ale](https://github.com/iamale))

### To-do

 * String interpolation: `i"{expression #flags}"` == `"{:flags}".format expression`
 * Tools for easy AST manipulation.
 * Compiler extension API.
 * Some of the more obscure Python features: exception causes, function annotations.
