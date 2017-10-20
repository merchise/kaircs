#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# vsbs
# ---------------------------------------------------------------------
# Copyright (c) 2016, 2017 Merchise Autrement [~º/~] and Contributors
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

        :param bucket_type: The name of the bucket type to use for the
                            store. If None we don't use bucket types.

        '''
        from riak import RiakClient
        self.riak = riak = RiakClient(nodes=nodes)
        if bucket_type:
            bucket_type = riak.bucket_type(bucket_type)
            self.bucket = bucket_type.bucket(name)
        else:
            self.bucket = riak.bucket(name)

    def open(self, name, mode='r'):
        '''Open a Blob within the store to either write or read.

        The returned object will have only a `read` or `write` method.

        :param name: The name of the blob.  It cannot be empty.
        :type name: bytes

        '''
        if not isinstance(name, binary_type):
            raise TypeError('Blob names must be bytes')
        if not name:
            raise ValueError('Blob name cannot be empty')
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
            return write.first_chunk.blob

    def read(self, filename):
        '''Read a file in the blob store.

        Only do this for small files, since the entire contents of the file is
        loaded in memory.

        Return the contents of the file.

        '''
        result = []
        with self.open(filename, 'r') as blob:
            # I really expect to have less than 20 chunks if you're using this
            # method... If your files are large and you still use this method,
            # you're not your friend!
            chunk = blob.read(20 * Blob.CHUNK_SIZE)
            while chunk:
                result.append(chunk)
                chunk = blob.read(20 * Blob.CHUNK_SIZE)
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
        # inaccessible (the first chunk is the last to be written).  We assume
        # that you delete a file after it's completely written.
        for i in range(self.lenght):
            BlobChunk(self, i).delete()


class BlobReader(object):
    def __init__(self, blob):
        self.blob = blob
        # Force the first chunk to be read so that metadata is loaded, this
        # also ensures we can't open a non-existing blob.
        chunk = BlobChunk(blob, 0)
        self.current = 0
        self.chunk_data = chunk.content
        self.chunk_position = 0
        self.consumed = 0
        self.length = blob.length

    def read(self, size=None):
        '''Read up-to `size` bytes from the Blob.

        If size is None, negative or zero, default to CHUNK_SIZE.

        The return value may have less than `size` bytes when the end of the
        blob is reached.  Trying to read once the blob has been fully
        consumed will return ``b''``.

        '''
        if self.consumed >= self.blob.metadata.size:
            return b''
        consumed = 0
        size = Blob.CHUNK_SIZE if size is None or size <= 0 else size
        result = []

        def get():
            if consumed < size:
                request = size - consumed
                data = self.read_current(request)
                if request and len(data) < request:
                    # we requested more than what we got, this means the
                    # current chunk is depleted, so move on to the next one.
                    self.advance()
                return data
            else:
                return b''

        data = get()
        while data:
            result.append(data)
            consumed += len(data)
            data = get()

        # The previous loop may end up at the very end of the current chunk,
        # no more data to read from it, but more chunks after it; however
        # since `get()` only advances when during true consumption, this would
        # make the next call to read to return b'', so we need to force an
        # advance in such a case.
        if self.chunk_position >= len(self.chunk_data):
            self.advance()

        self.consumed += consumed
        return b''.join(result)

    def read_current(self, size=None):
        '''Read from the current chunk in the reader.

        If the current chunk is exhausted, return ``b''``.  This won't advance
        the current chunk.

        '''
        size = Blob.CHUNK_SIZE if size is None else size
        if not size:
            return b''
        pos = self.chunk_position
        res = self.chunk_data[pos:pos + size]
        self.chunk_position += len(res)
        return res

    def advance(self):
        '''Go to the next chunk if possible.

        If there's no next chunk, return False.  If there's a next chunk,
        advance the readers position to it and return True.

        '''
        self.current += 1
        if self.current < self.length:
            self.chunk_data = BlobChunk(self.blob, self.current).content
            self.chunk_position = 0
            return True
        else:
            return False

    def close(self, **options):
        self.chunk = None


class BlobWriter(object):
    def __init__(self, blob, options=None):
        self.blob = blob
        self.metadata = blob.metadata
        self.written = 0
        self.chunk = self.first_chunk = BlobChunk(blob, 0)
        self.chunk_size = 0
        self.options = dict(options or {})

    def write(self, data, **options):
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
                    chunk.store(**dict(self.options, **options))
                self.chunk = chunk = BlobChunk(self.blob, chunk.index + 1)
                self.chunk_size = 0
        self.written += size

    __call__ = write

    def close(self, **options):
        # At this point we know the size the of the blob so we can complete
        # the data of the first chunk and write it.
        chunk = self.first_chunk
        meta = chunk.metadata
        meta.size = self.written
        assert self.chunk_size != Blob.CHUNK_SIZE
        if 0 < self.chunk_size < Blob.CHUNK_SIZE:
            # The last chunk is still partially filled, we have to write it
            # now.
            self.chunk.store(**dict(self.options, **options))
        if chunk is not self.chunk:
            chunk.store(**dict(self.options, **options))
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
        # We can't assert for equality: this is just one chunk of the blob.
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
        # If the 'vsbs' butcket type is a write-once w=1 should be redundant,
        # but let's be explicit in this case: We expect that that a chunk does
        # not get written often, in fact, we HIGHLY expect a single write
        # under normal (non failure) operations.  Setting w=1 allows to have
        # lower latency even if write-once is not set.  At the same time, we
        # will allow other values for 'w' if needed by the client.
        kwargs.setdefault('w', 1)
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
        return self.bucket.get(self.chunk_key, r=1)

    @property
    def content(self):
        if not self.data:
            self.data = self.get()
        return self.data

    @property
    def chunk_key(self):
        return '{}/{}'.format(self.master_key, self.index)
