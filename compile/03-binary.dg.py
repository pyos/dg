..compile      = import
..parse.tree   = import
..parse.syntax = import


varary = (multiple, self, a, *bs, arg: 0, inplace: False, single: None) ->
  '''
    If there is one argument, feed to it an opcode; otherwise,
    do the same thing as `foldl`, but with an opcode instead of a function.

    Examples::

      >>> (varary: 'BINARY_STUFF' single: 'UNARY_STUFF'): compiler a
        1 LOAD   a
        2 UNARY_STUFF

      >>> (varary: 'BINARY_STUFF' single: 'UNARY_STUFF'): compiler a b c
        1 LOAD   a
        2 LOAD   b
        3 BINARY_STUFF
        4 LOAD   c
        5 BINARY_STUFF

     >>> (varary: 'BINARY_STUFF' inplace: True): compiler a b
        1 LOAD   a
        2 LOAD   b
        3 BINARY_STUFF
        4 STORE  a

    :param multiple: the opcode to use as a folding function.

    :param arg: the argument to pass to all opcodes (a constant!)

    :param inplace: whether to assign the result of that expression
      to the first argument.

    :param single: the opcode to insert if there is only one argument.
      The default value, None, will raise an exception.

  '''

  self.load: a
  ps = list: (map: b -> (self.opcode: multiple b arg: arg delta: 0) bs)
  self.opcode: single arg: arg delta: 0 unless ps
  self.store_top: (*): (parse.syntax.assignment_target: a) if inplace

# `.`, ``, `:`, `->`, and `=` are already defined.
compile.r.builtins !! '$' = (self, a, *bs) -> self.call: a (parse.tree.Closure: bs)
compile.r.builtins !! ',' = (self, a, *bs) ->
  self.opcode: 'BUILD_TUPLE' (*): (parse.syntax.tuple_: a (*): bs) delta: 1

# FIXME `a < b < c` <=> `a < b and b < c`, not `(a < b) < c`.
compile.r.builtins !! '<'   = varary ~: 'COMPARE_OP' ~: arg: '<'
compile.r.builtins !! '<='  = varary ~: 'COMPARE_OP' ~: arg: '<='
compile.r.builtins !! '=='  = varary ~: 'COMPARE_OP' ~: arg: '=='
compile.r.builtins !! '!='  = varary ~: 'COMPARE_OP' ~: arg: '!='
compile.r.builtins !! '>'   = varary ~: 'COMPARE_OP' ~: arg: '>'
compile.r.builtins !! '>='  = varary ~: 'COMPARE_OP' ~: arg: '>='
compile.r.builtins !! 'is'  = varary ~: 'COMPARE_OP' ~: arg: 'is'
compile.r.builtins !! 'in'  = varary ~: 'COMPARE_OP' ~: arg: 'in'

compile.r.builtins !! '!!'  = varary ~: 'BINARY_SUBSCR'
compile.r.builtins !! '+'   = varary ~: 'BINARY_ADD'      ~: single: 'UNARY_POSITIVE'
compile.r.builtins !! '-'   = varary ~: 'BINARY_SUBTRACT' ~: single: 'UNARY_NEGATIVE'
compile.r.builtins !! '*'   = varary ~: 'BINARY_MULTIPLY'
compile.r.builtins !! '**'  = varary ~: 'BINARY_POWER'
compile.r.builtins !! '/'   = varary ~: 'BINARY_TRUE_DIVIDE'
compile.r.builtins !! '//'  = varary ~: 'BINARY_FLOOR_DIVIDE'
compile.r.builtins !! '%'   = varary ~: 'BINARY_MODULO'
compile.r.builtins !! '&'   = varary ~: 'BINARY_AND'
compile.r.builtins !! '^'   = varary ~: 'BINARY_XOR'
compile.r.builtins !! '|'   = varary ~: 'BINARY_OR'
compile.r.builtins !! '<<'  = varary ~: 'BINARY_LSHIFT'
compile.r.builtins !! '>>'  = varary ~: 'BINARY_RSHIFT'

compile.r.builtins !! '!!=' = varary ~: 'BINARY_SUBSCR'        ~: inplace: True
compile.r.builtins !! '+='  = varary ~: 'INPLACE_ADD'          ~: inplace: True
compile.r.builtins !! '-='  = varary ~: 'INPLACE_SUBTRACT'     ~: inplace: True
compile.r.builtins !! '*='  = varary ~: 'INPLACE_MULTIPLY'     ~: inplace: True
compile.r.builtins !! '**=' = varary ~: 'INPLACE_POWER'        ~: inplace: True
compile.r.builtins !! '/='  = varary ~: 'INPLACE_TRUE_DIVIDE'  ~: inplace: True
compile.r.builtins !! '//=' = varary ~: 'INPLACE_FLOOR_DIVIDE' ~: inplace: True
compile.r.builtins !! '%='  = varary ~: 'INPLACE_MODULO'       ~: inplace: True
compile.r.builtins !! '&='  = varary ~: 'INPLACE_AND'          ~: inplace: True
compile.r.builtins !! '^='  = varary ~: 'INPLACE_XOR'          ~: inplace: True
compile.r.builtins !! '|='  = varary ~: 'INPLACE_OR'           ~: inplace: True
compile.r.builtins !! '<<=' = varary ~: 'INPLACE_LSHIFT'       ~: inplace: True
compile.r.builtins !! '>>=' = varary ~: 'INPLACE_RSHIFT'       ~: inplace: True

compile.r.builtins !! '.~'  = (self, a, b) -> self.opcode: 'DELETE_ATTR'   None a arg: b delta: 1
compile.r.builtins !! '!!~' = (self, a, b) -> self.opcode: 'DELETE_SUBSCR' None a      b delta: 1
compile.r.builtins !! ':.'  = (self, a, b) ->
  '''a:.b <=> (a:).b'''
  self.call: a
  self.opcode: 'LOAD_ATTR' arg: b delta: 0
