### What's this?

A basic GNU readline-like library. It provides a navigation-enabled equivalent
to `input()` with customizable key bindings.

### Requirements

 * A UNIX-like OS
 * An XTerm-compatible terminal emulator

### Nothing says "UI" like a picture!

![A demo](http://i.imgur.com/VbUwvuh.png)

### Usage

```dg
import '/sys'
import '/dg/addon/readline'


MyReadline = subclass readline.Readline where
  # Disable SIGINT on Control+C and SIGSTOP on Control+Z. This allows to bind
  # other stuff on these keys instead.
  enable_jobs = False

  # Enable XOFF and XON on Control+S and Control+Q, respectively.
  # I don't know what these do.
  enable_flowctl = True

  # Colorize or do other stuff to the buffer before displaying it in the terminal.
  # **THIS METHOD MUST PRESERVE THE APPARENT LENGTH OF THE TEXT,**
  # which means it should take up the same amount of space
  # as the original after printing. Adding colors is fine, substituting
  # "aa" for "a" is not. Moving the cursor is fine as long as you put
  # it back, but this is really discouraged.
  preprocess = text ~>
    # As an example: this will display "big" in BIG RED LETTERS.
    text.replace "big" "\033[31mBIG\033[39m"

  __init__ = tty ~>
    readline.Readline.__init__ self tty
    # Now, the most important part: keybindings.
    # They're stored in a dict which maps keys to
    # (ReadlineState -> ReadlineState) functions.
    @bindings = dict @bindings
    # Keys may be specified as symbols or ANSI escapes.
    # Note that different terminals may use different escapes for the same key;
    # notable offenders are Home, End, Delete, and Backspace.
    @bindings !! 'x' = state -> state.insert state.position 'y'  # ha-ha
    # Oh, and there are several predefined constants for keys, too.
    @bindings !! readline.Key.TAB = @complete

  complete = state ~>
    # Note that completion and history must be implemented manually.
    # Say, you want to print a list of completions.
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


# To fetch a line, create an instance of the config.
# But first, a TTY must be created from input-output streams.
rl = MyReadline $ readline.Teletype sys.stdin sys.stdout
# Then call its `input` method with a prompt. Note that the prompt may be colored;
# the library will detect ANSI sequences automatically. You don't even need to wrap them
# in `\001` and `\002`, as is the case with GNU readline!
txt = rl.input '\033[32mYay!\033[39m \033[37m(try writing "big")\033[39m > '
print "Here's txt:" txt
# The prompt may be a function, in which case it accepts a
# ReadlineState as its argument and returns the string to use.
# Note that it shouldn't change the state.
txt = rl.input $ st -> if
  st.buffer => 'now press enter: '
  otherwise => 'write something: '
print "This is what you wrote:" txt
```
