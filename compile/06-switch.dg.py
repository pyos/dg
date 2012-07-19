..compile      = import
..parse.syntax = import


compile.r.builtins !! 'else' = (self, cond, otherwise) ->
  '''
    a if b else c
    a unless b else c

    Ternary conditional.

  '''

  is_if, (then, cond) = parse.syntax.else_: cond
  ptr = self.opcode: 'POP_JUMP_IF_FALSE' cond delta: 0 if     is_if
  ptr = self.opcode: 'POP_JUMP_IF_TRUE'  cond delta: 0 unless is_if
  jmp = self.opcode: 'JUMP_FORWARD'      then delta: 0

  ptr:
  self.load: otherwise
  jmp:


compile.r.builtins !! 'switch' = (self, cases) ->
  '''
    switch $
      condition1 = when_condition1_is_true
      ...
      conditionN = when_conditionN_is_true

    Evaluate the first action assigned to a true condition.
    `if-elif` is probably a better equivalent than `switch-case`.

  '''

  jumps = list $ map: c -> (
    cond, action = c
    next = self.opcode: 'POP_JUMP_IF_FALSE' cond delta: 0
    end  = self.opcode: 'JUMP_FORWARD'    action delta: 0
    next:
    end
  ) $ parse.syntax.switch: cases

  self.load: None  # in case nothing matched
  list $ map: x -> (x:) jumps
