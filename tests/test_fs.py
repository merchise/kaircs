#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# test_fs
# ---------------------------------------------------------------------
# Copyright (c) 2017 Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2017-10-24


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import pytest

from kaircs.service.fs import FileSystem, ROOT
from hypothesis import given, strategies as s, settings


@s.composite
def path_components(draw, from_=s.text(alphabet='abcdxyz', min_size=1)):
    return draw(from_)


@s.composite
def paths(draw, min_size=1, max_size=3, components=path_components()):
    res = draw(s.lists(components, min_size=min_size, max_size=max_size))
    return '/' + '/'.join(res)


def test_root_exists():
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'test_root_exists', dir_bucket_type='maps')
    assert fs.exists(ROOT) and fs.isdir(ROOT)
    fs.close()


@given(paths())
@settings(max_examples=10)
def test_traverse_mkdir(path):
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'test_traverse_mkdir', dir_bucket_type='maps')
    fs.mkdir(path, exists_ok=True)
    assert fs.isdir(path) and fs.exists(path)
    fs._rmall()
    fs.close()


@given(paths(min_size=3, max_size=6))
@settings(max_examples=10)
def test_non_traverse_mkdir(path):
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'test_non_traverse_mkdir', dir_bucket_type='maps')
    with pytest.raises(EnvironmentError) as excinfo:
        fs.mkdir(path, traverse=False)
    assert 'No such file or directory' in str(excinfo.value)
    assert not fs.exists(path)
    fs._rmall()
    fs.close()


@given(paths())
@settings(max_examples=10)
def test_already_exists_mkdir(path):
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'test_already_exists_mkdir', dir_bucket_type='maps')
    fs.mkdir(path, exists_ok=True)
    with pytest.raises(EnvironmentError) as excinfo:
        fs.mkdir(path)
    assert 'already exists' in str(excinfo.value)
    assert fs.exists(path)
    fs._rmall()
    fs.close()


@given(paths())
@settings(max_examples=10)
def test_rm_dir(path):
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'test_rm_dir', dir_bucket_type='maps')
    fs.mkdir(path, exists_ok=True)
    fs.rm(path, recursive=True)
    assert not fs.exists(path)
    fs._rmall()
    fs.close()


@given(paths())
@settings(max_examples=10)
def test_rm_file(path):
    import os
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'test_rm_file', dir_bucket_type='maps')
    fs.mkdir(path, exists_ok=True)
    content = b'x' * 200
    fpath = os.path.join(path, 'x')
    with fs.open(fpath, 'w') as f:
        f.write(content)
    fs.rm(fpath)
    assert not fs.exists(fpath)
    fs._rmall()
    fs.close()


@given(paths())
@settings(max_examples=10)
def test_open(path):
    import os
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'test_open', dir_bucket_type='maps')
    fs.mkdir(path, exists_ok=True)
    content = b'x' * 200
    fpath = os.path.join(path, 'x')
    with fs.open(fpath, 'w') as f:
        f.write(content)
    assert fs.cat(fpath) == content
    fs._rmall()
    fs.close()


@given(paths(min_size=2))
@settings(max_examples=10)
def test_put(path):
    import os.path
    filename = os.path.join(os.path.dirname(__file__), 'blob')
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'test_put', dir_bucket_type='maps')
    fs.put(filename, name=path)
    with open(filename, 'rb') as f:
        contents = f.read()
    assert fs.cat(path) == contents
    fs._rmall()
    fs.close()


@given(paths())
@settings(max_examples=10)
def test_concurrent_read(path):
    import os
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'test_concurrent_read', dir_bucket_type='maps')
    fs.mkdir(path, exists_ok=True)
    content = b'x' * 200
    fpath = os.path.join(path, 'x')
    with fs.open(fpath, 'w') as f:
        f.write(content)

    with fs.open(fpath, 'r') as f:
        with fs.open(fpath, 'r') as j:
            c1 = c2 = b''
            fc1 = f.read(10)
            fc2 = j.read(10)
            while fc1 or fc2:
                c1 += fc1
                c2 += fc2
                fc1 = f.read(10)
                fc2 = j.read(10)
            assert c1 == c2
    fs._rmall()
    fs.close()
