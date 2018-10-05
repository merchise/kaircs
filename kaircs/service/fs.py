#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)
import os
from xoutil.eight.string import force as safestr

from kaircs.vsbs import BlobStore

ROOT = '/'


class FileSystem(object):
    '''A file system over Riak-KV.

    :param nodes: A list of Riak KV nodes to connect to. See the `nodes`
                  argument of `<RiakClient>`:class:..

    :param dir_bucket_type: The name of the bucket type to use for the
                            store. If None raise `<RiakError>`:class:..

    '''
    def __init__(self, nodes, name, store_options=None,
                 dir_bucket_type=None):
        from riak import RiakClient
        self.riak = RiakClient(nodes=nodes)
        name = safestr(name)
        files_store_name = '%s-files' % name
        dirs_store_name = '%s-dirs' % name
        self.files = BlobStore(
            self.riak,
            files_store_name,
            **(store_options or {})
        )
        dir_bucket_type = self.riak.bucket_type(dir_bucket_type)
        self.dirs = dir_bucket_type.bucket(dirs_store_name)
        # Create root if it doesn't exists
        self.mkdir(ROOT, exists_ok=True)
        self.root = Directory(ROOT, self)

    def close(self):
        self.files.close()
        self.riak.close()

    def __del__(self):
        self.close()

    def mkdir(self, name, traverse=True, *args, **kwargs):
        '''Create directory under `name`.

        If `traverse` is True create the structure as needed.

        If `exist_ok` is True don't fail if the directory already exists.
        If `exist_ok` is False and the directory exists, raise an
        EnvironmentError.

        .. versionchanged:: 0.3.0 The argument `exists_ok` is renamed to
           `exist_ok` (so that it's similar to the standard library).  We keep
           `exists_ok`, but it will be removed in a future release.

        '''
        from xoutil.params import ParamManager
        pm = ParamManager(args, kwargs)
        exist_ok = pm(0, 'exist_ok', 'exists_ok', default=False)

        def _mkdir(name, traverse, exists_ok):
            if not name.startswith(ROOT):
                raise ValueError('Cannot create relative path "%s"' % name)
            directory = Directory(name, self)
            if not self.exists(directory.name):
                parent = directory.parent
                if traverse and directory != self.root:
                    parent = _mkdir(
                        parent.name,
                        traverse=traverse,
                        exists_ok=True
                    )
                if self.exists(parent.name):
                    base = basename(name)
                    parent[base] = directory
                else:
                    raise EnvironmentError(
                        '"%s": No such file or directory' % parent.name
                    )
            else:
                if not self.isdir(directory.name):
                    raise EnvironmentError('File "%s" already exists' % name)
                elif not exists_ok:
                    raise EnvironmentError('Entry "%s" already exists' % name)
            return directory

        _mkdir(name=name, traverse=traverse, exists_ok=exist_ok)

    def put(self, filename, name=None):
        from ..vsbs import Blob
        if not name:
            name = filename
        blocksize = 4*Blob.CHUNK_SIZE
        with open(filename, 'rb') as file:
            parent = dirname(name)
            self.mkdir(parent, traverse=True, exist_ok=True)
            with self.open(name, 'w') as write:
                chunk = file.read(blocksize)
                while len(chunk) == blocksize:
                    write(chunk)
                    chunk = file.read(blocksize)
                if len(chunk):
                    write(chunk)

    def exists(self, path):
        '''Test if a path exists.

        '''
        if path == ROOT:
            return True
        dirname, base = split(path)
        dir = Directory(dirname, self)
        return base in dir and self.exists(dir.name)

    def isdir(self, path):
        '''Test if a path is a directory.

        Raise `EnvironmentError`:class:. if path does not exists.
        '''
        if path == ROOT:
            return True
        if not self.exists(path):
            raise EnvironmentError('%s: No such file or directory' % path)
        dirname, base = split(path)
        dir = Directory(dirname, self)
        return isinstance(dir[base], Directory)

    def cat(self, path):
        if self.isdir(path):
            raise EnvironmentError('Error processing "%s".'
                                   'Cannot cat a directory' % path)
        _file = File(path, self)
        return self.files.read(_file.name)

    def rm(self, path, recursive=False):
        '''Remove entries under path.

        Raise `EnvironmentError`:class:. if trying to delete a directory
        without recursive=True.
        '''
        if path == ROOT:
            raise ValueError('Cannot remove /')
        if self.isdir(path) and not recursive:
            raise EnvironmentError('Recursive must be True to'
                                   'remove a directory')
        else:
            l = self.ls(path, recursive=recursive)  # noqa
            # ls return top down so we revert it to go up.
            l.reverse()
            for p in l:
                if not self.isdir(p):
                    self.files.delete(p)
                parent = self.dirs.get(
                    Directory(dirname(p), self).hash
                )
                del parent.registers[basename(p)]
                parent.store()

    def ls(self, path, recursive=False):
        '''List entries under path.

        Return a list of entry names. If `path` points to a file, return a
        list with a single entry.  If `path` does not exist raise
        `EnvironmentError`:class:.
        '''
        res = [path]
        if self.isdir(path):
            for child in Directory(path, self).children:
                child_path = os.path.join(path, child)
                if not recursive:
                    res.append(child_path)
                else:
                    res += self.ls(child_path, recursive=True)
        return res

    def open(self, path, mode='r'):
        '''Open file to read or write.

        Raise `EnvironmentError`:class:. if trying to open a directory, if
        parent directory does not exists or if `path` does not exists and file
        is trying to be open for reading.
        '''
        parent = dirname(path)
        if not self.isdir(parent):
            raise EnvironmentError('%s: No such file or directory.' % parent)
        if mode == 'r' and not self.exists(path):
            raise EnvironmentError('%s: No such file or directory.' % path)
        if self.exists(path) and self.isdir(path):
            raise EnvironmentError('%s: Is a directory.' % path)
        _file = File(path, self)
        if mode == 'w':
            base = basename(path)
            Directory(parent, self)[base] = _file
        return self.files.open(_file.name, mode)

    def link(self, name, refer, symlink=False):
        pass


class Path(object):
    '''A path data descriptor.

    Automatically `normalizes <normalize>`:func: paths.

    '''
    def __init__(self, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is not None:
            return instance.__dict__[self.name]
        else:
            return self

    def __set__(self, instance, value):
        instance.__dict__[self.name] = normalize(value)

    def __delete__(self, instance):
        del instance.__dict__[self.name]


class Entry(object):
    name = Path('name')

    def __init__(self, name, fs):
        self.name = name
        self.fs = fs

    def __eq__(self, other):
        if isinstance(other, Entry):
            return self.fs == other.fs and self.hash == other.hash
        else:
            return NotImplemented

    def __ne__(self, other):
        return not self == other

    @property
    def hash(self):
        return '%s::%s' % (self.namespace, self.name)

    @classmethod
    def from_hash(cls, hash, fs):
        ns, path = hash.split('::')
        return cls.find_subclass(ns)(path, fs)

    @classmethod
    def find_subclass(cls, ns):
        return next(
            subclass
            for subclass in Entry.__subclasses__()
            if subclass.namespace == ns
        )


class Directory(Entry):
    namespace = 'dir'

    def __init__(self, path, fs):
        '''A set that contains entries.

        '''
        super(Directory, self).__init__(path, fs)
        self.registers = fs.dirs.get(self.hash).registers

    def __contains__(self, item):
        if not isinstance(item, Entry):
            item = Entry(item, self.fs)
        return basename(item.name) in self.children

    def __setitem__(self, key, value):
        if isinstance(key, Entry):
            dirname, basename = split(key.name)
            assert dirname == self.name
        else:
            basename = key
        assert safestr(os.path.sep) not in basename
        assert isinstance(value, Entry)
        self.registers[basename].assign(value.hash)
        self.registers.map.store()

    def __getitem__(self, key):
        hash = self.registers[key].value
        if not hash:
            raise KeyError(key)
        return self.from_hash(hash, self.fs)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        else:
            return super(Directory, self).__eq__(other)

    def __ne__(self, other):
        if isinstance(other, str):
            return self.name != other
        else:
            return super(Directory, self).__ne__(other)

    @property
    def parent(self):
        if self.name == ROOT:
            return ROOT
        else:
            return Directory(dirname(self.name), self.fs)

    @property
    def children(self):
        '''Names of entries.

        '''
        return self.registers.keys()


class Link(Entry):
    namespace = 'link'
    pass


class File(Entry):
    namespace = 'file'


def dirname(path):
    '''Return the dirname of `path` after `normalization <normalize>`:func:.

    '''
    return os.path.dirname(normalize(path))


def split(path):
    return os.path.split(normalize(path))


def basename(path):
    return os.path.basename(normalize(path))


def normalize(path):
    '''Normalize a `path` to the canonical form.

    - Removes trailing slashes.
    - Remove duplicated consecutive slashes (even at the beginning).

    '''
    from os.path import realpath, normpath
    return safestr(realpath(normpath(path)))
