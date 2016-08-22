===============================================
 KairCS - Small File Cloud System over Riak KV
===============================================

KairCS allows to put mostly immutable files (written once, updated mostly
never) on a Riak KV store, that are read sequentially (no random access to a
file is supported).

This project is not meant to be a substitute of Riak CS:

- There's a single file space in KairCS.  No butcket, no users.  It's almost a
  file-system you can write to, that expects your files don't change much.

- No encryption of data.

- No security.


Architecture
============

KairCS is split in two main components:

- `The KairCS Very Simple Blob Store`_
- `The KairCS Service`_


KairCS Very Simple Blob Store (VSBS)
------------------------------------

It's responsible to actually manage the storage of blobs.  It DOES NOT keep
any notion of directories so there's no way to list all the blobs in the
store.  In fact, this layer support only two operations:

- Write a blob
- Read a blob from begin to end

The `KiarCS Service`_ leverage these function to provide *some* support for
listing and deletion.

When storing a blob, you must provide a name is used to create a *master key*
of the blob.  The master key is actually a SHA256 of the blob name.

The blob is divided in chunks of 1 MB.  Each chunk is stored individually
under a automatically generated key composed by the blob's *master key* and a
counter.

The first chunk contains both metadata and data.  The metadata record is like
this::

  record metadata {

      uint8 metadata_size;
      # The size of the metadata excluding this byte.  Currently this
      # is 1 + 8 bytes.

      uint64 size_of_the_blob;
  }

The maximum size of the first chunk is thus 1 MB plus 9 bytes. Other chunks
are just data and the size of the chunk is the size of the data.

To write a blob you need the name and the size. To read a blob you just need
the name.

VSBS store the chunks in Riak KV.


KiarCS Service
--------------

This is higher level component.  It exposes a REST API over HTTP/1.1:

``GET /path/to/x``

  Read the file or directory under the given path.  It may return 404 if the
  file is not found.

  .. todo:: If path is a directory, reply with a 300 Multiple Choices ?


``PUT /path/to/a/file``

  Create or replace the file under the given path.

  If the given path exists and points to a directory, reply with a 400 Bad
  request.

  This method creates the directories as needed.

  Trying to upload large files may fail if the client does not support chunked
  transfer.

  The Content-Length header MUST be sent

  .. todo:: Chunked response replies.


``DELETE /path/to/a/file``

  Remove the file.  Deleting a directory is not supported.  If by removing a
  file a directory becomes empty further requests for the directory MAY get
  404 responses.


Contents
========

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
