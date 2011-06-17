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
        response = session.request('GET', db.resource.url + '/_changes?feed=longpoll&since=1000&timeout=%s' % (timeout*2*1000,))
        self.assertRaises(socket.timeout, response.data.read)
        self.failUnless(time.time() - start < timeout * 1.3)


class ResponseStreamTestCase(unittest.TestCase):

    def test_double_iteration_over_same_response_body(self):

        class ChunkedHttpResponse:

            msg = network.Headers({'transfer-encoding': 'CHUNKED'})

            def __init__(self, fp):
                self.fp = fp

            @property
            def closed(self):
                return self.fp.tell() == os.fstat(self.fp.fileno()).st_size

        data = 'foobarbaz'.encode('latin-1')
        data = b'\r\n'.join([("%x" % len(data)).encode('latin-1'), data])
        fp = TemporaryFile()
        fp.write(data)
        fp.seek(0)
        response = network.ResponseStream(ChunkedHttpResponse(fp), 'latin-1')
        self.assertEqual(list(response), ['foobarbaz'])
        self.assertEqual(list(response), [])

if __name__ == '__main__':
    unittest.main()