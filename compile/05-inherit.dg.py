..compile = import


compile.r.builtins !! 'inherit' = (self, *stuff) ->
  '''
    inherit: ... block

    Create a class with `block` as its body.
    All arguments but the last one are passed straight to the `__build_class__`
    function.
  '''

  *args, block = stuff

  # __build_class__ will also need a `dict -> cell` function.
  mcode = compile.codegen.MutableCode: True args: ('__locals__',) cell: self.code
  mcode.cellnames.add: '__class__'
  # The argument, __locals__, is what we need to write attributes to.
  mcode.append: 'LOAD_FAST'  '__locals__' delta: 1
  mcode.append: 'STORE_LOCALS'            delta: (-1)
  mcode.append: 'LOAD_NAME'  '__name__'   delta: 1
  mcode.append: 'STORE_NAME' '__module__' delta: (-1)
  mcode.f_hook = code -> code.freevars.append: '__class__'
  
  self.compile: block into: mcode name: '<lambda>'
  
  # The return value is a __class__ cell, if any.
  # Python compiler returns None instead if there are no instance methods.
  # That's not really necessary, though.
  mcode.bytecode.pop:
  mcode.append: 'POP_TOP'  # Replacing RETURN_VALUE with POP_TOP yields delta 0
  mcode.append: 'LOAD_CLOSURE' '__class__' delta: 1
  mcode.append: 'RETURN_VALUE'             delta: (-1)
  code = mcode.compile:
  
  self.opcode: 'LOAD_BUILD_CLASS' delta: 1
  self.opcode: (compile.preload_free: self code) code arg: 0 delta: (1 - bool: code.co_freevars)
  self.call: None '<class>' (*): args preloaded: 1
