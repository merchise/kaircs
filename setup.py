#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

from __future__ import (division as _py3_division,
                        print_function as _py3_print)

# XXX: Don't put absolute imports in setup.py

import sys
import os
from setuptools import setup, find_packages

# Import the version from the release module
project_name = str('kaircs')
_current_dir = os.path.dirname(os.path.abspath(__file__))
VERSION = '0.3.0'


install_requires = [
    'xoutil>=1.8.0,<1.9',
    'flask>=0.12.2',
    'six>=1.8.0',
    'basho_erlastic>=2.1.1'
]
requires = [
    'xoutil(>=1.8.0, <1.9)',
    'flask(>=0.12.2)',
    'six(>=1.8.0)',
    'basho_erlastic(>= 2.1.1)'
]

if sys.version_info[:3] <= (2, 7, 9):
    install_requires.append("pyOpenSSL >= 0.14")
    requires.append("pyOpenSSL(>=0.14)")

if sys.version_info[:3] <= (3, 0, 0):
    install_requires.append('protobuf >=2.4.1, <2.7.0')
    requires.append('protobuf(>=2.4.1, <2.7.0)')
else:
    install_requires.append('python3_protobuf >=2.4.1, <2.6.0')
    requires.append('python3_protobuf(>=2.4.1, <2.6.0)')


setup(
    name=project_name,
    version=VERSION,
    description="A small File Cloud Storage over Riak KV",
    long_description=open(
        os.path.join(_current_dir, 'README.rst')).read(),
    # Get more strings from
    # http://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Programming Language :: Python",
    ],
    keywords=[''],
    author='Merchise Autrement [~º/~]',
    author_email='',
    url='http://www.merchise.org/',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    requires=requires,
    install_requires=install_requires,
)
