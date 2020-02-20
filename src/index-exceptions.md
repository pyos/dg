```dg
f = x -> raise if
  x :: int  => IndexError x
  otherwise => ValueError x

g = x -> except
  grr => f x
  grr :: IndexError => 0

except
  grr => g 0
  grr :: ValueError => 1
```
