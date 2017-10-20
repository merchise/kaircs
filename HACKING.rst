To run tests you should download the basho/riak-kv docker image.  We keep a
copy in ``docker.lahavane.com:5000/riak-kv``::

  $ docker pull docker.lahavane.com:5000/riak-kv

If you can, pull it from Internet::

  $ docker pull basho/riak-kv

Before running tests, create and start the services::

  $ docker-compose -f tests/docker-compose.yml up -d

Then, wait till the Riak KV cluster is up and running and the run the tests
with tox::

  $ tox
