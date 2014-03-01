```dg
import '/sys/stdin'

IOTools = subclass object where
  #: Compute the average line length of a file.
  #:
  #: avglen :: TextIOBase -> NoneType
  #:
  avglen = staticmethod $ fd ->
    lengths = list $ map len fd
    count   = len lengths
    total   = sum lengths
    print 'Average line length:' $ if
      count > 0 => total / count
      otherwise => 0

IOTools.avglen stdin
```
