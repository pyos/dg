import re
import os
import glob

from . import __path__

import dg
import dmark


name_of = lambda x: os.path.basename(x)[:-3]  # - '.md'
files   = glob.glob(os.path.join(__path__[0], '*.md'))
data    = {name_of(x): dmark.parse(open(x).read()) for x in files}

for f in glob.glob(os.path.join(__path__[0], '*.html')):

    src = open(f)
    tgt = open(os.path.join(os.path.dirname(f), os.pardir, os.path.basename(f)), 'w', newline='\n')
    tgt.write(re.sub(r'@@(\w+)', lambda m: data[m.group(1)], src.read()))
