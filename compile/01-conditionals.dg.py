..compile = import


varary_cond = (instruction, argparse: xs -> xs) -> (self, *xs) ->

  *as, b = argparse: xs
  ps = list $ map: a -> (self.opcode: instruction a delta: 0) as
  self.load: b
  # No runtime operators are defined yet,
  # so `map: (:) ps` is not allowed.
  list $ map: p -> (p:) ps


compile.r.builtins !! 'or'     = varary_cond: 'JUMP_IF_TRUE_OR_POP'
compile.r.builtins !! 'and'    = varary_cond: 'JUMP_IF_FALSE_OR_POP'
compile.r.builtins !! 'if'     = varary_cond: 'JUMP_IF_FALSE_OR_POP' reversed
compile.r.builtins !! 'unless' = varary_cond: 'JUMP_IF_TRUE_OR_POP'  reversed
