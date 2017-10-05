#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# fs
# ---------------------------------------------------------------------
# Copyright (c) 2016 Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2016-08-30

'''A file system over VSBS.

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


from xoutil.eight import binary_type

from kaircs.vsbs import BlobStore


class FileSystem(object):
    def __init__(self, store):
        self.store = store

    @classmethod
    def new(cls, *args, **kwargs):
        return cls(BlobStore(*args, **kwargs))

    @staticmethod
    def get_inode(name):
        return b'inode/' + name

    @staticmethod
    def get_dnode(name):
        return b'dnode/' + name
