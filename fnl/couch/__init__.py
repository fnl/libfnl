"""
.. py:module:: couch
   :synopsis: A CouchDB client for Python 3000.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
"""

from fnl.couch.broker import COUCHDB_URL, Database, Document, Server
from fnl.couch.network import HTTPError, PreconditionFailed, \
        RedirectLimitExceeded, ResourceConflict, ResourceNotFound, \
        ServerError, Unauthorized
