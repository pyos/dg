..compile = import


varary_cond = (jump, argparse: xs -> xs) -> (self, *xs) ->
  '''
    Intersperse arguments with jump instructions, then point them
    at the next opcode. The jump instruction is assumed to either jump
    or pop the topmost item off the stack.

    Example::

      >>> (varary_cond: 'MY_JUMP'): compiler a b c
        1 LOAD    a
        2 MY_JUMP 6
        3 LOAD    b
        4 MY_JUMP 6
        5 LOAD    c
      > 6 <out of scope of this function>

    :param jump: a jump instruction to insert between arguments.

    :param argparse: a function that preprocesses all arguments at once.

  '''

  *as, b = argparse: xs
  # There is no `$` operator yet.
  ps = list: (map: a -> (self.opcode: jump a delta: 0) as)
  self.load: b
  # No runtime operators are defined yet, so `map: (:) ps` is not allowed.
  list: (map: p -> (p:) ps)


compile.r.builtins !! 'or'     = varary_cond: 'JUMP_IF_TRUE_OR_POP'
compile.r.builtins !! 'and'    = varary_cond: 'JUMP_IF_FALSE_OR_POP'
compile.r.builtins !! 'if'     = varary_cond: 'JUMP_IF_FALSE_OR_POP' reversed
compile.r.builtins !! 'unless' = varary_cond: 'JUMP_IF_TRUE_OR_POP'  reversed
