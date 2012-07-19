..compile      = import
..parse.syntax = import


compile.r.builtins !! 'raise' = compile.r.callable $
  (self, exception, caused_by: Ellipsis) ->
    '''
      raise: ExceptionType
      raise: exception_instance
      raise: ... caused_by: another_exception_or_Ellipsis_or_None

      Raise an exception. If the exception is a subclass of BaseException,
      instantiate it beforehand. If the `caused_by` argument is not an
      `Ellipsis`, make it the __cause__ of that exception.

      In CPython 3.3, `raise: exception caused_by: None` silences the context.

    '''

    args = (exception,) if caused_by `is` Ellipsis else (exception, caused_by)
    self.opcode: 'RAISE_VARARGS' (*): args delta: 0
    self.load: None  # We've got to return something.


compile.r.builtins !! 'unsafe' = (self, cases) ->
  '''
    unsafe $
      error = unsafe_code
      condition1 = when_condition1_is_True
      ...
      conditionN = when_conditionN_is_True
      True = finally_clause

    Evaluate `unsafe_code`, storing the whatever exception is raised as
    `error`, then evaluating the first action to be assigned
    to a true condition. If no condition is true, the exception is re-raised.
    If there was no exception, `error` is set to `None`. If the last
    action is assigned to `True`, it is evaluated regardless of whether
    any other condition was True, but it can't silence the exception.

    Returns the value of `unsafe_code` if there was no exception,
    `None` otherwise.

  '''

  # http://i2.kym-cdn.com/photos/images/original/000/234/765/b7e.jpg
  # That seems to work, though.
  (name, try), *cases, (has_finally, finally) = parse.syntax.unsafe: cases

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
  compile.store: self name None
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
  compile.store_top: self (*): (parse.syntax.assignment_target: name)
  self.opcode: 'ROT_TWO' delta: 0
  to_else:

  # The same `switch` statement...
  jumps = list:

  cases.for each: (cond, case) do:
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

  has_finally and
    # If the interpreter made it here, one of the `except` clauses matched.
    self.opcode: 'POP_BLOCK' delta: (-1)
    self.load: None

    to_finally:
    self.opcode: 'POP_TOP' finally delta: 0
    self.opcode: 'END_FINALLY'     delta: 0

  # We should be left with a return value by now.
