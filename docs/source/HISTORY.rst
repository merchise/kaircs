============
 Change log
============

0.x series
==========

These are the first releases.  Expected unstable API and lots of bug.  Put it
on production at your own risk.


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
