import re
import os
import glob

import dg
import dmark

from . import __path__


for f in glob.glob(os.path.join(__path__[0], '*.html')):
  source = open(f)
  target = open(os.path.join(os.path.dirname(f), os.pardir, os.path.basename(f)), 'w', newline='\n')
  target.write(re.sub(
    r'@@([\w\.]+)',
    lambda m: dmark.parse(open(os.path.join(__path__[0], m.group(1) + '.md')).read()),
    source.read()))
