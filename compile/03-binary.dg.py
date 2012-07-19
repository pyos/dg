# `.`, ``, `:` and `$` are already defined

varary = (multiple, arg: 0, inplace: False, single: None) -> (self, a, *bs) ->

  self.load: a
  ps = list $ map: b -> (self.opcode: multiple b arg: arg delta: 0) bs
  self.opcode: single arg: arg delta: 0 unless ps
  store_top: self (*): (syntax.assignment_target: a) if inplace

# FIXME `a < b < c` <=> `a < b and b < c`, not `(a < b) < c`.
r.builtins !! '<'   = varary: 'COMPARE_OP' '<'
r.builtins !! '<='  = varary: 'COMPARE_OP' '<='
r.builtins !! '=='  = varary: 'COMPARE_OP' '=='
r.builtins !! '!='  = varary: 'COMPARE_OP' '!='
r.builtins !! '>'   = varary: 'COMPARE_OP' '>'
r.builtins !! '>='  = varary: 'COMPARE_OP' '>='
r.builtins !! 'is'  = varary: 'COMPARE_OP' 'is'
r.builtins !! 'in'  = varary: 'COMPARE_OP' 'in'

r.builtins !! '!!'  = varary: 'BINARY_SUBSCR'
r.builtins !! '+'   = varary: 'BINARY_ADD'      single: 'UNARY_POSITIVE'
r.builtins !! '-'   = varary: 'BINARY_SUBTRACT' single: 'UNARY_NEGATIVE'
r.builtins !! '*'   = varary: 'BINARY_MULTIPLY'
r.builtins !! '**'  = varary: 'BINARY_POWER'
r.builtins !! '/'   = varary: 'BINARY_TRUE_DIVIDE'
r.builtins !! '//'  = varary: 'BINARY_FLOOR_DIVIDE'
r.builtins !! '%'   = varary: 'BINARY_MODULO'
r.builtins !! '&'   = varary: 'BINARY_AND'
r.builtins !! '^'   = varary: 'BINARY_XOR'
r.builtins !! '|'   = varary: 'BINARY_OR'
r.builtins !! '<<'  = varary: 'BINARY_LSHIFT'
r.builtins !! '>>'  = varary: 'BINARY_RSHIFT'

r.builtins !! '!!=' = varary: 'BINARY_SUBSCR'        inplace: True
r.builtins !! '+='  = varary: 'INPLACE_ADD'          inplace: True
r.builtins !! '-='  = varary: 'INPLACE_SUBTRACT'     inplace: True
r.builtins !! '*='  = varary: 'INPLACE_MULTIPLY'     inplace: True
r.builtins !! '**=' = varary: 'INPLACE_POWER'        inplace: True
r.builtins !! '/='  = varary: 'INPLACE_TRUE_DIVIDE'  inplace: True
r.builtins !! '//=' = varary: 'INPLACE_FLOOR_DIVIDE' inplace: True
r.builtins !! '%='  = varary: 'INPLACE_MODULO'       inplace: True
r.builtins !! '&='  = varary: 'INPLACE_AND'          inplace: True
r.builtins !! '^='  = varary: 'INPLACE_XOR'          inplace: True
r.builtins !! '|='  = varary: 'INPLACE_OR'           inplace: True
r.builtins !! '<<=' = varary: 'INPLACE_LSHIFT'       inplace: True
r.builtins !! '>>=' = varary: 'INPLACE_RSHIFT'       inplace: True

r.builtins !! ':.' = (self, a, b) -> (self.call: a, self.opcode: 'LOAD_ATTR' arg: b delta: 0)
r.builtins !! '.~'  = (self, a, b) -> self.opcode: 'DELETE_ATTR'   None a arg: b delta: 1
r.builtins !! '!!~' = (self, a, b) -> self.opcode: 'DELETE_SUBSCR' None a      b delta: 1
