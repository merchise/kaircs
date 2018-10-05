============
 Change log
============

0.x series
==========

These are the first releases.  Expected unstable API and lots of bug.  Put it
on production at your own risk.

2018-10-05.  Release 0.4.0
--------------------------

- Support for Python 2.7, Python 3.6 and Python 3.7 has been added.

  .. warning:: The last published version of `riak
     <https://pypi.org/project/riak>`__ in the PyPI doesn't work in Python 3;
     so we embed the latest `development
     <https://github.com/basho/riak-python-client>`__ in this package.  This
     means you cannot install this alongside the riak package.


2017-12-08. Release 0.3.0
-------------------------

- Fix bug in `FileSytem.mkdir`: If exist_ok was True, it didn't check that the
  path was actually a directory.

  Also the argument `exists_ok` is now deprecated in favor of `exist_ok`.

- Add `FileSystem.put` to put a file from the local file system to the KairCS
  FS.


2017-12-07. Release 0.2.0
-------------------------

- Implement BlobReader and BlobWriter as context managers (e.g don't use
  `contextlib.closing`).


2017-11-22. Release 0.1.0
-------------------------

- First release.  The vsbs, the fs and the http service are fully implemented.
