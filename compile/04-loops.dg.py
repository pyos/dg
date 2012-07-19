..compile      = import
..parse.syntax = import


compile.r.fake_methods !! 'while' = (self, cond, block) ->
  '''
    cond.while: block

    Evaluate `block` until `cond` becomes False.
    `block` is evaluated in the same namespace (it would be useless otherwise.)

  '''

  self.load: None
  exit_ptr = self.opcode: 'SETUP_LOOP'             delta: 0
  cond_ptr = self.opcode: 'JUMP_ABSOLUTE'  arg: -1 delta: 0
  else_ptr = self.opcode: 'POP_JUMP_IF_FALSE' cond delta: 0
  self.opcode: 'ROT_TWO' block delta:  1
  self.opcode: 'POP_TOP'       delta: -1
  cond_ptr:
  else_ptr:
  self.opcode: 'POP_BLOCK' delta: 0
  exit_ptr:


compile.r.fake_methods !! 'for' = compile.callable $ (self, iterable, each, do) ->
  '''
    iterable.for: item block
    iterable.for: item do: block
    iterable.for: each: item do: block

    A simple for-each loop.
    `item` may be anything that can be assigned to with `=`.
    `block` is evaluated in the same namespace; use `map` if that's not
    desired behavior.

  '''

  self.load: None  # This will be replaced with the return value.
  self.opcode: 'GET_ITER' iterable delta: 1

  loop_ptr = self.opcode: 'JUMP_ABSOLUTE' arg: -1 delta: 0
  end_ptr  = self.opcode: 'FOR_ITER' delta: 1

  self.store_top: (*): (parse.syntax.assignment_target: each) dup: False
  self.load: do
  self.opcode: 'ROT_THREE' delta: 0
  self.opcode: 'ROT_TWO'   delta: 0
  self.opcode: 'POP_TOP'   delta: (-1)

  loop_ptr:
  end_ptr:

  # FOR_ITER popped `iterable` off the stack.
  self.code.cstacksize -= 1
