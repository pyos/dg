r.builtins !! 'else' = (self, cond, otherwise) ->

  is_if, (then, cond) = syntax.else_: cond

  # Sadly, `if-else` is not available until we define this function.
  code = is_if and 'POP_JUMP_IF_TRUE' or 'POP_JUMP_IF_FALSE'
  ptr  = self.opcode: code           cond delta: 0
  jmp  = self.opcode: 'JUMP_FORWARD' then delta: 0
  ptr:
  self.load: otherwise
  jmp:


r.builtins !! 'switch' = (self, cases) ->

  jumps = list:
  func  = (c) ->
  
    cond, action = c
    jumps.append $ self.opcode: 'POP_JUMP_IF_FALSE' cond delta: 0
    jumps.append $ self.opcode: 'JUMP_FORWARD'    action delta: 0
    jumps and (jumps.pop: -2):

  list $ map: func $ syntax.switch: cases

  self.load: None  # in case nothing matched
  list $ map: x -> (x:) jumps
