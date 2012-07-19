r.builtins !! 'inherit' = (self, *stuff) ->

  *args, block = stuff
  
  mcode = codegen.MutableCode: True args: ('__locals__',) cell: self.code
  mcode.cellnames.add: '__class__'
  mcode.append: 'LOAD_FAST'  '__locals__' delta: 1
  mcode.append: 'STORE_LOCALS'            delta: (-1)
  mcode.append: 'LOAD_NAME'  '__name__'   delta: 1
  mcode.append: 'STORE_NAME' '__module__' delta: (-1)
  mcode.f_hook = code -> code.freevars.append: '__class__'
  
  self.compile: block into: mcode name: '<lambda>'
  
  # Return the empty __class__ cell.
  mcode.bytecode.pop:
  mcode.append: 'POP_TOP'  # Replacing RETURN_VALUE with POP_TOP yields delta 0
  mcode.append: 'LOAD_CLOSURE' '__class__' delta: 1
  mcode.append: 'RETURN_VALUE'             delta: (-1)
  code = mcode.compile:
  
  self.opcode: 'LOAD_BUILD_CLASS' delta: 1
  self.opcode: (preload_free: self code) code arg: 0 delta: (1 - bool: code.co_freevars)
  self.call: None '<class>' (*): args preloaded: 1
