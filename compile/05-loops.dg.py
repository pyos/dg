r.fake_methods !! 'while' = (self, cond, block) ->

  self.load: None
  exit_ptr = self.opcode: 'SETUP_LOOP' delta: 0
  cond_ptr = self.opcode: 'JUMP_ABSOLUTE' arg: (-1) delta: 0
  else_ptr = self.opcode: 'POP_JUMP_IF_FALSE' cond delta: 0
  self.opcode: 'ROT_TWO' block delta: 1
  self.opcode: 'POP_TOP' delta: (-1)
  cond_ptr:
  else_ptr:
  self.opcode: 'POP_BLOCK' delta: 0
  exit_ptr:


r.fake_methods !! 'for' = r.callable $ (self, iterable, each, do) ->

  self.opcode: 'GET_ITER' None iterable delta: 2

  loop_ptr = self.opcode: 'JUMP_ABSOLUTE' arg: (-1) delta: 0
  end_ptr  = self.opcode: 'FOR_ITER' delta: 1

  store_top: self (*): (syntax.assignment_target: each) dup: False
  self.load: do
  self.opcode: 'ROT_THREE' delta: 0
  self.opcode: 'ROT_TWO'   delta: 0
  self.opcode: 'POP_TOP'   delta: (-1)

  loop_ptr:
  end_ptr:

  # FOR_ITER popped `iterable` off the stack.
  self.code.cstacksize -= 1
