varary_cond = (jmp, p: x -> x) -> (self, *xs, n: () -> 0) ->

  *bs, a = p: xs
  ps = list $ map: b -> (self.opcode: jmp b delta: 0) bs
  self.load: a
  # No runtime operators are defined yet,
  # so `map: (:) ps` is not allowed.
  list $ map: p -> (p:) ps


r.builtins !! 'or'     = varary_cond: 'JUMP_IF_TRUE_OR_POP'
r.builtins !! 'and'    = varary_cond: 'JUMP_IF_FALSE_OR_POP'
r.builtins !! 'if'     = varary_cond: 'JUMP_IF_FALSE_OR_POP' reversed
r.builtins !! 'unless' = varary_cond: 'JUMP_IF_TRUE_OR_POP'  reversed
