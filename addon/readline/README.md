### What's this?

A basic GNU readline-like library. It provides a navigation-enabled equivalent
to `input()` with customizable key bindings.

### Requirements

 * A UNIX-like OS
 * An XTerm-compatible terminal emulator

### Usage

#### Basic

 1. Create a `Teletype`.
 2. Create a `Readline`.
 3. Call its `input` method with a prompt.

```dg
import '/sys'
import '/dg/addon/readline'

console = readline.Teletype sys.stdin sys.stdout
reader  = readline.Readline console
reader.input 'enter stuff here: '
```

#### Change some settings

`Readline` has several methods and attributes that may be overriden.
Add the `History` mix-in to enable arrow-based history navigation.

```dg
MyReadline = subclass readline.History readline.Readline where
```

#### Turn system task control on/off

```dg
  # Disable SIGINT on Control+C and SIGSTOP on Control+Z. This allows to bind
  # other stuff on these keys instead.
  enable_jobs = False

  # Enable XOFF and XON on Control+S and Control+Q, respectively.
  # I don't know what these do.
  enable_flowctl = True
```

#### Display entered data in a different fashion

The `preprocess` method is called before displaying the buffer.
It can change the appearence of entered text, though it should not change
its apparent length (i.e. it must occupy the same amount of space after preprocessing.)
Changes introduced by this method do not carry over to the return value of `input`.

```dg
  preprocess = text ~>
    # As an example: this will display "big" in BIG RED LETTERS.
    text.replace "big" "\033[31mBIG\033[39m"
```

#### Add some keybindings

The `bingings` instance attribute is a mapping of keys to state modifiers.

```dg
  __init__ = tty ~>
    (super MyReadline self).__init__ tty
    @bindings = dict @bindings
```

A state modifier is a function that accepts a `ReadlineState` and returns another
`ReadlineState`.

```dg
    # Insert 'y' at caret position on X
    @bindings !! 'x' = state -> state.insert state.position 'y'  # ha-ha
```

A `ReadlineState` has the following attributes:

 * `prompt`: the prompt string/function passed to `input`.
 * `buffer`: current line contents.
 * `position`: the index of the caret, from 0 to `len state.buffer`.
 * `cache`: a dictionary for misc. data. Its contents are the same within one `input`.

...and these methods:

 * `erase I N`: remove N characters starting at index I.
 * `insert I S`: insert the string S at index I.
 * `left N`: move the caret left by N characters.
 * `right N`: move the caret right by N characters.

There's also a `Key` object that provides some known key values.

```dg
    # Erase 2 symbols at the start of the line on Ctrl+G
    @bindings !! readline.Key.CONTROL_G = state -> state.erase 0 2
```

#### Displaying stuff between prompts

 1. Finalize the old state.
 2. Print something (note that the terminal is in raw mode; use `\r\n`.)
 3. Return the new state.

```dg
    @bindings !! readline.Key.CONTROL_F = state ->
      @finalize state
      print 'Search is not supported.' end: '\r\n'
      # The prompt will be re-displayed automatically.
      state
```

#### Context-aware prompts

The prompt may be a function, in which case it accepts a
`ReadlineState` as its argument and returns the string to use.
Note that it shouldn't change the state.

```dg
reader = MyReadline console
reader.input $ state -> if
  state.buffer => 'now press enter: '
  otherwise    => 'write something: '
```

#### Autocompletion

Add the `Completion` mix-in to enable autocompletion.

```dg
MyReadline2 = subclass readline.Completion MyReadline where
```

`Tab` triggers completion by default. Override the `completion_keys` set
to change that.

```dg
  completion_keys = set' readline.Key.TAB readline.Key.CONTROL_T
```

The default completion logic is to split the input into words (chunks matched with
`completion_regex`, which defaults to `\w+`)...

```dg
  completion_regex = re.compile r'[\w\.]+'
```

...find the word the caret's pointing at, call `complete_word`...

```dg
  complete_word = word ~> list $ filter (x -> x.startswith word) globals!
```

...then either put the result into the input, or print a list of completions
with `display_completions`.

```dg
  display_completions = cmps ~> print *: cmps sep: '\r\n' end: '\r\n'
```

This logic could be modified by overriding the `complete_buffer` method, which
receives a string buffer and the caret position and should return
an `(offset, length, completions)` tuple, where `offset` and `length` point to the word
that is being completed.

#### Syntax highlighting with Pygments

 1. Enable the `Pygments` mix-in.
 2. Set `pygments_lexer` to the name of the preferred lexer.

```dg
MyReadline3 = subclass readline.Pygments MyReadline2 where
  pygments_lexer = 'dg'
```
