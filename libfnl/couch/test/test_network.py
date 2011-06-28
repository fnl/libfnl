"""
Mostly equal to the original code by Christopher Lenz for CouchDB-Python.
"""
import os

import socket
from tempfile import TemporaryFile
import time
import unittest

from libfnl.couch import network
from libfnl.couch import testutil


class SessionTestCase(testutil.TempDatabaseMixin, unittest.TestCase):

    def test_timeout(self):
        dbname, db = self.temp_db()
        timeout = 1
        session = network.Session(timeout=timeout)
        start = time.time()
        response = session.request('GET', db.resource.url + '/_changes?feed=longpoll&since=1000&timeout=%s' % (timeout*2*1000,), chunked_response=True)
        self.assertRaises(socket.timeout, response.data.read)
        self.failUnless(time.time() - start < timeout * 1.3)


if __name__ == '__main__':
    unittest.main()