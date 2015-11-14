```dg
>>> import '/dg/Compiler'
>>>
>>> (Compiler.prefix !! 'such_if' =
...  Compiler.prefix !! 'if')
>>> Compiler.constnames !! 'much_else' = True
>>>
>>> such_if
...   'wow'     => 'doge'
...   much_else => 'lang'
...
'doge'
```
