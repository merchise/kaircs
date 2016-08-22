#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# vsbs
# ---------------------------------------------------------------------
# Copyright (c) 2016 Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2016-08-17

'''The KairCS Very Simple Blob Store.

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import math
import hashlib
import struct
import contextlib

from xoutil.eight import binary_type


class BlobStore(object):
    def __init__(self, nodes, name, bucket_type='vsbs'):
        '''A Very Simple Blob Store.

        :param nodes: A list of Riak KV nodes to connect to.  See the `nodes`
                      argument of RiakClient.

        '''
        from riak import RiakClient
        self.riak = riak = RiakClient(nodes=nodes)
        bucket_type = riak.bucket_type(bucket_type)
        self.bucket = bucket_type.bucket(name)

    def open(self, name, mode='r'):
        '''Open a Blob within the store to either write or read.

        The returned object will have only a `read` or `write` method.


        '''
        if not isinstance(name, binary_type):
            raise TypeError('Blob names must be bytes')
        blob = Blob(name, self)
        if mode == 'r':
            return contextlib.closing(BlobReader(blob))
        elif mode == 'w':
            return contextlib.closing(BlobWriter(blob))
        else:
            raise ValueError('mode must be r or w')

    def put(self, filename, name=None):
        '''Put a file in the blob store.

        '''
        blocksize = 4*Blob.CHUNK_SIZE
        with open(filename, 'rb') as file:
            with self.open(name or filename, 'w') as write:
                chunk = file.read(blocksize)
                while len(chunk) == blocksize:
                    write(chunk)
                    chunk = file.read(blocksize)
                if len(chunk):
                    write(chunk)

    def read(self, filename):
        '''Read a file in the blob store.

        Only do this for small files, since the entire contents of the file is
        loaded in memory.

        Return the contents of the file.

        '''
        result = []
        with self.open(filename, 'r') as blob:
            for chunk in blob:
                result.append(chunk)
        return b''.join(result)

    def write(self, filename, contents):
        assert isinstance(contents, binary_type)
        with self.open(filename, 'w') as write:
            write(contents)

    def delete(self, name):
        Blob(name, self).delete()


class Blob(object):
    CHUNK_SIZE = int(1.05 * 1024 * 1024)

    def __init__(self, name, store):
        assert isinstance(name, binary_type)
        self.name = name
        self.store = store
        self.metadata = BlobMetadata()

    @property
    def length(self):
        '''Equal to the amount of chunks needed to store the blob.'''
        meta = self.metadata
        return int(math.ceil((self.size + meta.metadata_size) / self.CHUNK_SIZE))

    @property
    def size(self):
        return self.metadata.size

    @property
    def master_key(self):
        return hashlib.sha256(self.name).hexdigest()

    def delete(self):
        # DELETION IS TOUGH: Since writing a large file requires several
        # writes (chunks), a file may be partially written but yet
        # inaccessible (the first chunk is the last to be written).  So this
        # method simply removes the first chunk of the file.  To actually
        # reclaim space more information is needed.
        BlobChunk(self, 0).delete()


class BlobReader(object):
    def __init__(self, blob):
        self.blob = blob
        self.chunk = BlobChunk(blob, 0)

    def __iter__(self):
        yield self.chunk.content
        i, length = 1, self.blob.length
        while i < length:
            chunk = BlobChunk(self.blob, i)
            yield chunk.content
            i += 1

    def close(self):
        self.chunk = None


class BlobWriter(object):
    def __init__(self, blob):
        self.blob = blob
        self.metadata = blob.metadata
        self.written = 0
        self.chunk = self.first_chunk = BlobChunk(blob, 0)
        self.chunk_size = 0

    def write(self, data):
        # write to the current chunk until it fills, when the chunk is full
        # write it to the Riak KV backend, and create another chunk to be
        # filled.  Stop when all data is writen.
        chunk = self.chunk
        wr, size = 0, len(data)
        while wr < size:
            needed = Blob.CHUNK_SIZE - self.chunk_size
            chunk_data = data[wr: wr + needed]
            wr += len(chunk_data)
            chunk.data += chunk_data
            self.chunk_size += len(chunk_data)
            assert self.chunk_size <= Blob.CHUNK_SIZE
            if self.chunk_size == Blob.CHUNK_SIZE:
                if chunk.index:
                    # Notice that the first chunk (with index 0) won't be
                    # written until the whole blob is written.  This is
                    # because we need to append the blob's metadata which
                    # includes the size of the blob, and we don't know that
                    # until the end of the write.
                    chunk.store()
                self.chunk = chunk = BlobChunk(self.blob, chunk.index + 1)
                self.chunk_size = 0
        self.written += size

    __call__ = write

    def close(self):
        # At this point we know the size the of the blob so we can complete
        # the data of the first chunk and write it.
        if self.chunk_size < Blob.CHUNK_SIZE:
            # The last chunk is still be partially filled, we have to write it
            # now.
            self.chunk.store()

        chunk = self.first_chunk
        meta = chunk.metadata
        meta.size = self.written
        chunk.store()
        self.chunk = None  # avoid more writing


class BlobMetadata(object):
    HEADER_FMT = '<BQ'
    HEADER_SIZE = struct.calcsize(HEADER_FMT)

    def __init__(self):
        self.metadata_size = None
        self.size = None

    @property
    def header(self):
        return struct.pack(self.HEADER_FMT, self.HEADER_SIZE, self.size)

    def extract(self, rawdata):
        assert len(rawdata) >= self.HEADER_SIZE
        header, data = rawdata[:self.HEADER_SIZE], rawdata[self.HEADER_SIZE:]
        msize, size = struct.unpack(self.HEADER_FMT, header)
        self.metadata_size = msize
        self.size = size
        if msize > self.HEADER_SIZE:
            metadata, data = rawdata[:msize], rawdata[msize:]
        else:
            assert msize == self.HEADER_SIZE
            metadata = header
        # We can assert for equality: this is just one chunk of the blob.
        assert size >= len(data)
        return metadata, data


class BlobChunk(object):
    def __init__(self, blob, index):
        self.blob = blob
        self.index = index
        self.riak = blob.store.riak
        self.bucket = blob.store.bucket
        self.data = b''
        self.metadata = self.blob.metadata
        self.master_key = self.blob.master_key

    def put(self, data, **kwargs):
        self.data = data
        self.store(**kwargs)

    def store(self, **kwargs):
        assert self.data
        robj = self.riak_obj
        robj.content_type = 'application/octet-stream'
        if self.index:
            robj.encoded_data = self.data
        else:
            robj.encoded_data = self.metadata.header + self.data
        robj.store(**kwargs)

    def get(self):
        robj = self.riak_obj
        if not robj.exists:
            raise KeyError(self.chunk_key)
        if self.index:
            # Any chunk but the first one will have only data
            data = robj.encoded_data
        else:
            _, data = self.metadata.extract(robj.encoded_data)
        return data

    def delete(self):
        self.riak_obj.delete()

    @property
    def riak_obj(self):
        return self.bucket.get(self.chunk_key)

    @property
    def content(self):
        if not self.data:
            self.data = self.get()
        return self.data

    @property
    def chunk_key(self):
        return '{}/{}'.format(self.master_key, self.index)
