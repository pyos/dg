## Modules

As stated earlier, dg can import any Python module you have, but the syntax is a bit different. All module names are POSIX paths rather than identifiers:

```dg
import '/sys'  # => import sys
```

Module names are relative by default, unless explicitly made absolute as shown above:

```dg
import 'asd'            # => from . import asd
import '../asd'         # => from .. import asd
import '../../asd'      # => from ... import asd
import '../../asd/qwe'  # => from ...asd import qwe
```

`import` behaves as Python's `from ... import ...` by default; this can be averted by adding the `qualified` keyword after the module name:

```dg
import '/os/path'            # => from os import path
import '/os/path' qualified  # => import os.path
```

Note that all paths are normalized automatically.

```dg
import '/asd/../sys'  # => import sys
```

You can't do `import .asd` in Python; likewise, you can't use `qualified` when performing relative imports in dg.

```dg
import '../asd' qualified  # => syntax error
```

`import` returns the object it has imported.

```dg
import '/os' == os
```
