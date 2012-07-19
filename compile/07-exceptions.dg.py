r.builtins !! 'raise' = r.callable $ (self, exception, caused_by: Ellipsis) ->

  args = (exception,) if caused_by `is` Ellipsis else (exception, caused_by)
  self.opcode: 'RAISE_VARARGS' (*): args delta: 0
  self.load: None  # We've got to return something.


r.builtins !! 'unsafe' = (self, cases) ->

    # http://i2.kym-cdn.com/photos/images/original/000/234/765/b7e.jpg
    # That seems to work, though.
    (name, try), *cases, (has_finally, finally) = syntax.unsafe: cases

    # This will be our return value.
    self.load: None

    to_finally = self.opcode: 'SETUP_FINALLY' delta: 0 if has_finally
    to_except  = self.opcode: 'SETUP_EXCEPT'  delta: 0
    # Replace that None with the value returned by `try_`
    # to fool the POP_BLOCK instruction.
    self.opcode: 'ROT_TWO' try delta: 1
    self.opcode: 'POP_BLOCK'   delta: (-1)
    # Er, so there was no exception, let's store None instead.
    # Since we've already POPped_BLOCK, exceptions occured
    # during this assignment will be ignored.
    store: self name None
    # XXX I don't know why is that needed.
    self.code.cstacksize -= 1

    # Jump over that block if there was no exception.
    # Finishing SETUP_EXCEPT with an exception pushes
    # 3 items onto the stack.
    #
    # Stack:: [try, None] or [None, traceback, value, type]
    #
    to_else = self.opcode: 'JUMP_FORWARD' delta: 3
    to_except:
    self.opcode: 'ROT_TWO' delta: 0
    store_top: self (*): (syntax.assignment_target: name)
    self.opcode: 'ROT_TWO' delta: 0
    to_else:

    # The same `switch` statement...
    jumps = list:

    for cond, case in cases:

        jumps.append $ self.opcode: 'POP_JUMP_IF_FALSE' cond delta: 0
        # FIXME we can't return anything from handlers.
        self.opcode: 'POP_TOP' case delta: 0
        jumps.append $ self.opcode: 'JUMP_FORWARD' delta: 0
        jumps and (jumps.pop: -2):

    # This will re-raise the exception if nothing matched
    # (and there was an exception. And there is no `finally` clause.)
    self.opcode: 'END_FINALLY' delta: (-3)

    # The problem is, now we need to POP_EXCEPT, but only
    # if there was a handled exception.

    # First, jump over this whole part if the exception was not handled.
    unhandled_exception = self.opcode: 'JUMP_FORWARD' delta: 0

    # Second, check if the exception type is None, in which case
    # there was no exception at all.
    list $ map: x -> (x:) jumps
    self.opcode: 'DUP_TOP' delta: 1
    self.opcode: 'COMPARE_OP' None arg: 'is' delta: 0
    # Then skip POP_EXCEPT if that is the case.
    no_exception = self.opcode: 'POP_JUMP_IF_TRUE' delta: (-1)

    self.opcode: 'POP_EXCEPT' delta: 0
    unhandled_exception:
    no_exception:

    switch:
      has_finally =
        # If the interpreter made it here, one of the `except` clauses matched.
        self.opcode: 'POP_BLOCK' delta: (-1)
        self.load: None

        to_finally:
        self.opcode: 'POP_TOP' finally_, delta: 0
        self.opcode: 'END_FINALLY'       delta: 0

    # We should be left with a return value by now.
