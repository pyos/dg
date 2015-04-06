#!/usr/bin/env python3
from distutils.core import setup

setup(
    name='dg',
    version='1.0.0+git',
    description='A programming language for the CPython VM',
    author='pyos',
    author_email='pyos100500@gmail.com',
    url='https://github.com/pyos/dg.git',
    packages=['dg'],
    package_dir={'dg': '.'},
    package_data={'dg': ['*.dg', '*/*.dg', '*/*.dgbundle']}
)
