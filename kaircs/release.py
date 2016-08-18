#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------
# kaircs.release
# -----------------------------------------------------------------------
# Copyright (c) 2016 Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2016-08-17


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)


VERSION = '0.1.0'


def dev_tag_installed():
    import pkg_resources
    try:
        dist = pkg_resources.get_distribution('kaircs')
        full_version = dist.version
        # FIX: Below line is not working anymore
        base = dist.parsed_version.base_version
        return full_version[len(base):]
    except:
        return None


RELEASE_TAG = dev_tag_installed() or ''


def safe_int(x):
    try:
        return int(x)
    except ValueError:
        return x

# I won't put the release tag in the version_info tuple.  Since PEP440 is on
# the way.
VERSION_INFO = tuple(safe_int(x) for x in VERSION.split('.'))


del safe_int
