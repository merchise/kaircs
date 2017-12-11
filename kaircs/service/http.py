#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

'''This is higher level component. It exposes a REST API over HTTP/1.1:

'''
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import operator
from functools import partial
from flask import Flask, request

from werkzeug.wrappers import Response
from werkzeug.exceptions import NotFound, BadRequest

from xoutil.future.codecs import safe_encode
from xoutil.fp.tools import compose

from .fs import FileSystem, basename, dirname


def with_normal_path(f):
    def funnel(path=b''):
        return path
    return compose(f, partial(operator.add, b'/'), safe_encode, funnel)


class KairCSApplication(Flask):
    def __init__(self, fs):
        super(KairCSApplication, self).__init__(__name__)
        self.add_url_rule('/', 'root', with_normal_path(self.GET), methods=['GET'])
        self.add_url_rule('/<path:path>', 'get', with_normal_path(self.GET), methods=['GET'])
        self.add_url_rule('/<path:path>', 'put', with_normal_path(self.PUT), methods=['PUT'])
        self.add_url_rule('/<path:path>', 'del', with_normal_path(self.DELETE), methods=['DELETE'])
        self.exists = fs.exists
        self.isdir = fs.isdir
        self.open = fs.open
        self.mkdir = fs.mkdir
        self.ls = fs.ls
        self.rm = fs.rm

    def GET(self, path=b''):
        if not self.exists(path):
            raise NotFound
        if self.isdir(path):
            return DirectoryStream(self, path)
        else:
            return FileStream(self, path)

    def PUT(self, path):
        dir = dirname(path)
        if self.exists(path) and self.isdir(path):
            raise BadRequest
        self.mkdir(dir, exist_ok=True)
        with self.open(path, 'w') as file:
            chunk_size = 4096  # FIXME: this should be a configuration option
            chunk = request.stream.read(chunk_size)
            while len(chunk) != 0:
                file.write(chunk)
                chunk = request.stream.read(chunk_size)
        return Response(
            status=201
        )

    def DELETE(self, path):
        '''Perform the DELETE of `path`.

        .. warning:: You should not reimplement this method to do an off-load
           of the deletion, instead override `rm`.

        '''
        if not self.exists(path):
            raise NotFound
        self.rm(path, recursive=True)
        return Response(status=202)


class Resource(object):
    path = ''

    def __init__(self, app, path):
        self.app = app
        self.path = path

    def exists(self, path):
        return self.app.exists(path)

    def __call__(self, environ, start_response):
        return Response(
            self.contents,
            **self.headers
        )(environ, start_response)

    @property
    def headers(self):
        return {}


class FileStream(Resource):
    '''Response object used to stream files

    '''
    @property
    def contents(self):
        with self.app.open(self.path, 'r') as f:
            res = f.read()
            while res:
                tmp = res
                res = f.read()
                yield(tmp)


class DirectoryStream(Resource):
    '''Response object used to stream directory contents

    '''
    link_tpl = '<a href="./%s">%s</a><br/>'

    @property
    def headers(self):
        return {'mimetype': 'text/html'}

    @property
    def contents(self):
        response = ''
        for i in self.app.ls(self.path):
            if i == self.path:
                response += '<a href="..">..</a><br/>'
            else:
                name = basename(i)
                if self.app.isdir(i):
                    name += '/'
                response += self.link_tpl % (name, name)
        return response


def main():
    fs = FileSystem([{'host': '127.0.0.1', 'http_port': 8098}],
                    'store', dir_bucket_type='maps')
    app = KairCSApplication(fs)
    app.run(host="0.0.0.0")


if __name__ == '__main__':
    main()
