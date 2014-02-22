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
Subclass `WithHistory` instead to enable arrow-based history navigation.

```dg
MyReadline = subclass readline.WithHistory where
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

#### Example: autocompletion

```dg
    @bindings !! readline.Key.TAB = @complete
    None  # __init__ must always return None

  complete = state ~>
    # NOTE: get_word_at and get_completions_for_word
    #  must be implemented manually.
    word, start_position = get_word_at state.buffer state.position
    cmps = get_completions_for word
    if
      len cmps == 1 =>
        # If you wish to insert the completion,
        # use `state.erase` and `state.insert`.
        state = state.erase  start_position (len word)
        state = state.insert start_position (head cmps)
      otherwise =>
        # If you wish to print something, finalize the old prompt first!
        # Also, keep in mind that the terminal is in raw mode now, so use
        # '\r\n' or '\n\r', not '\n'.
        state = @finalize state
        print *: cmps sep: '\r\n' end: '\r\n'
    # The prompt will be automatically re-displayed.
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
