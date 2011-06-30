#############################
couch -- A CouchDB client API
#############################

A CouchDB_ client API for Python 3000, ported from the Python (2.x) client
code written by **Christopher Lenz**, CouchDB-Python_, but refactored to be
used with Python 3.x interpreters (only).

.. automodule:: libfnl.couch

As the `libfnl.couch` package has been adapted to work with Python 3000, some
parts of the original client API have changed, and only the very essential
parts of Christopher's package (ie., only the `client` (now called `broker`)
and `http` (now `network`)) have been ported. All tools provided in addition
by CouchDB-Python_ are not available and not planned. The http/network
module is substantially different from the original to be useful with Python
3000's modified :mod:`io` and :mod:`http.client` modules , while the
client/broker API itself looks almost maintained "as is" from the
outside except for some renamed methods, but everything that can be streamed
from the CouchDB (``Transfer-Encoding: chunked``) is now by default handed on
as such - eg., :meth:`.couch.broker.Database.list` views return data streams.

All relevant classes and exceptions can be directly imported from the `couch`
module itself::

    from libfnl.couch import *

That statement provides the following classes and exceptions in your namespace:
:class:`.broker.Database`, :class:`.broker.Document`, and
:class:`.broker.Server`, as well as the the exceptions:

 * :exc:`libfnl.couch.network.HTTPError`,
 * :exc:`libfnl.couch.network.PreconditionFailed`,
 * :exc:`libfnl.couch.network.RedirectLimitExceeded`,
 * :exc:`libfnl.couch.network.ResourceConflict`,
 * :exc:`libfnl.couch.network.ResourceNotFound`,
 * :exc:`libfnl.couch.network.ServerError`, and
 * :exc:`libfnl.couch.network.Unauthorized`.

All these errors treat connection, request and response problems as well as
errors reported by CouchDB itself, and are all based on
:exc:`http.client.HTTPException`. Also, string encoding problems are reported
as :exc:`UnicodeError`, JSON encoding problems as :exc:`TypeError`, and bad
method parameters as :exc:`ValueError`. Virtually all methods provided through
the `broker` classes might raise any of them, so if you need strict error
recovery, wrap all calls to this API with `except` clauses for these four
errors.

.. _CouchDB: http://couchdb.apache.org/
.. _CouchDB-Python: http://code.google.com/p/couchdb-python

===================================
broker -- The Couch Database Broker
===================================

.. automodule:: libfnl.couch.broker

.. autodata:: libfnl.couch.broker.COUCHDB_URL

Server
------

.. autoclass:: libfnl.couch.broker.Server
    :members:
    :special-members:

Database
--------

.. autoclass:: libfnl.couch.broker.Database
    :members:
    :special-members:

ViewResults
-----------

.. autoclass:: libfnl.couch.broker.ViewResults
    :members:

Document
--------

.. autoclass:: libfnl.couch.broker.Document
    :members:

Row
---

.. autoclass:: libfnl.couch.broker.Row
    :members:

Attachment
----------

.. autoclass:: libfnl.couch.broker.Attachment

===================================
network -- The Network Access Layer
===================================

.. automodule:: libfnl.couch.network

.. autodata:: libfnl.couch.network.USER_AGENT

Response
--------

.. autoclass:: libfnl.couch.network.Response

ResponseStream
--------------

.. autoclass:: libfnl.couch.network.ResponseStream
    :members:

HTTPError
---------

.. autoclass:: libfnl.couch.network.HTTPError

.. autoclass:: libfnl.couch.network.PreconditionFailed

.. autoclass:: libfnl.couch.network.RedirectLimitExceeded

.. autoclass:: libfnl.couch.network.ResourceNotFound

.. autoclass:: libfnl.couch.network.ResourceConflict

.. autoclass:: libfnl.couch.network.Unauthorized

ServerError
-----------

.. autoclass:: libfnl.couch.network.ServerError



