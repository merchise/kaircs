#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# test_vsbs
# ---------------------------------------------------------------------
# Copyright (c) 2017 Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2017-10-05

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

from kaircs.vsbs import BlobStore, Blob
from hypothesis import given, example, strategies as s


@given(s.binary(min_size=1), s.binary(min_size=1))
def test_can_write_and_read(name, content):
    store = BlobStore([{'host': '127.0.0.1', 'http_port': 8098}], 'store',
                      bucket_type=None)
    with store.open(name, 'w') as f:
        f.write(content)
    retrieved = store.read(name)
    assert len(retrieved) == len(content)
    assert retrieved == content


@given(s.binary(min_size=1), s.integers(min_value=1, max_value=4))
@example(b'one_chunk', 1)
def test_can_write_and_read_chunks(name, n):
    content = b'x' * Blob.CHUNK_SIZE * n
    store = BlobStore([{'host': '127.0.0.1', 'http_port': 8098}], 'store',
                      bucket_type=None)
    with store.open(name, 'w') as f:
        f.write(content)
    retrieved = store.read(name)
    assert len(retrieved) == len(content)
    assert retrieved == content


@given(s.binary(min_size=1), s.binary(min_size=0))
def test_can_write_and_read_a_large_file(name, padding):
    import os
    with open(os.path.join(os.path.dirname(__file__), 'blob'), 'rb') as f:
        content = f.read() + padding
    store = BlobStore([{'host': '127.0.0.1', 'http_port': 8098}], 'store',
                      bucket_type=None)
    with store.open(name, 'w') as f:
        f.write(content)
    retrieved = store.read(name)
    assert len(retrieved) == len(content)
    assert retrieved == content
