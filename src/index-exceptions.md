```dg
f = x -> raise if
  x :: int  => IndexError x
  otherwise => ValueError x

g = x -> except
  err => f x
  err :: IndexError => 0

except
  err => g 0
  err :: ValueError => 1
```
