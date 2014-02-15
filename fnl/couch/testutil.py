"""
.. py:module:: testutil
   :synopsis: A database mixin for the TestCases.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)

Modified from the original code by Christopher Lenz for CouchDB-Python.
"""
import logging

import random
import sys
from libfnl.couch import broker


class TempDatabaseMixin(object):

    temp_dbs = None
    _db = None

    def setUp(self):
        #logging.basicConfig(level=logging.WARNING)
        self.server = broker.Server(full_commit=True)

    def tearDown(self):
        if self.temp_dbs:
            for name in self.temp_dbs:
                self.server.delete(name)

        prefix = 'couchdb-python/'

        for db in self.server:
            if db.startswith(prefix) and db[len(prefix):].isdigit():
                self.server.delete(db)

    def temp_db(self):
        if self.temp_dbs is None: self.temp_dbs = {}
        # Find an unused database name
        name = None

        while True:
            name = 'couchdb-python/%d' % random.randint(0, sys.maxsize)
            if name not in self.temp_dbs: break

        db = self.server.create(name)
        self.temp_dbs[name] = db
        return name, db

    def del_db(self, name):
        del self.temp_dbs[name]
        self.server.delete(name)

    @property
    def db(self):
        if self._db is None: name, self._db = self.temp_db()
        return self._db
