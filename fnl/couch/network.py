"""
.. py:module:: network
   :synopsis: CouchDB HTTP communication layer.

.. moduleauthor:: Christopher Lenz
.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)


This module provides the actual HTTP connectivity.

The module constitutes a comprehensive rewrite from the original code in
``http.py`` by Christopher Lenz for CouchDB-Python to adapt it to Python 3000,
except for the underlying :class:`.Resource` class.
"""
from base64 import b64encode
from collections import defaultdict, namedtuple
from datetime import datetime
import errno
from functools import partial
from http import client
from io import RawIOBase, StringIO
import logging
from os import strerror
import socket
from threading import Lock
import time
from urllib.parse import urlsplit, urlunsplit, urlencode, unquote, quote

from fnl.couch.serializer import Decode as DecodeJson, \
                                    Encode as EncodeJson

__all__ = ['HTTPError', 'PreconditionFailed', 'ResourceNotFound',
           'ResourceConflict', 'ServerError', 'Unauthorized',
           'RedirectLimitExceeded',
           'Session', 'Resource']

USER_AGENT = "couch.py3/1.0"
"""
The User-Agent header to use in requests.
"""

RETRYABLE_ERRORS = frozenset([
    errno.EPIPE, errno.ETIMEDOUT,
    errno.ECONNRESET, errno.ECONNREFUSED, errno.ECONNABORTED,
    errno.EHOSTDOWN, errno.EHOSTUNREACH,
    errno.ENETRESET, errno.ENETUNREACH, errno.ENETDOWN
])
"""
A set of error numbers that, when they happen, should immediately trigger
another attempt at the HTTP request.
"""

Response = namedtuple("Response", "status headers charset data")
"""
A named tuple representing the result from a request.

.. attribute:: status

    An `int` representing the response status value.

.. attribute:: headers

    A dict-like object representing the response headers
    (:class:`http.client.HTTPMessage`).

.. attribute:: charset

    A string defining the encoding of the response or ``None``.

.. attribute:: data

    The response data, one of:

        * A `bytes` (binary data) object.
        * A :class:`.ResponseStream` object if the response is chunked.
        * A Python object decoded from a JSON response, if a JSON
          :class:`.Resource` was requested and the response is not chunked.
"""

quoteall = partial(quote, safe='')


def ExtractCredentials(url:str) -> (str, (str, str)):
    """
    Extract authentication (username and password) credentials from the
    given URL, returning the cleaned URL and a (un, pw) tuple (or None if
    not credentials are found).

    >>> ExtractCredentials('http://localhost:5984/_config/')
    ('http://localhost:5984/_config/', None)
    >>> ExtractCredentials('http://joe:secret@localhost:5984/_config/')
    ('http://localhost:5984/_config/', ('joe', 'secret'))
    >>> ExtractCredentials('http://joe%40example.com:secret@localhost:5984/')
    ('http://localhost:5984/', ('joe@example.com', 'secret'))
    """
    credentials = None
    parts = urlsplit(url)

    if '@' in parts.netloc:
        creds, netloc = parts.netloc.split('@')
        credentials = tuple(unquote(i) for i in creds.split(':'))
        parts = list(parts)
        parts[1] = netloc
        url = urlunsplit(parts)

    return url, credentials


def UrlJoin(base:str, segments:[str], **query:{str:object}) -> str:
    """
    Assemble a URL based on a base segment, any number of path segments, and
    query parameters.

    >>> UrlJoin('http://example.org', ['_all_dbs'])
    'http://example.org/_all_dbs'

    A trailing slash on the URL *base* is handled gracefully:

    >>> UrlJoin('http://example.org/', ['_all_dbs'])
    'http://example.org/_all_dbs'

    And multiple segments become path parts:

    >>> UrlJoin('http://example.org/', ['foo', 'bar'])
    'http://example.org/foo/bar'

    All slashes within a segment are escaped:

    >>> UrlJoin('http://example.org/', ['foo/bar'])
    'http://example.org/foo%2Fbar'
    >>> UrlJoin('http://example.org/', ['foo', '/bar/'])
    'http://example.org/foo/%2Fbar%2F'

    If there are no segments, join with the empty list:

    >>> UrlJoin('http://example.org/', [])
    'http://example.org/'

    It is not allowed to use ``None``:

    >>> UrlJoin('http://example.org/', None)
    Traceback (most recent call last):
        ...
    ValueError: no segments to join
    """
    path = [base]

    # escape and add the segments
    if segments:
        root = "{}" if base.endswith('/') else "/{}"
        path.append(root.format('/'.join( quoteall(s) for s in segments )))
    elif segments is None:
        raise ValueError("segments cannot be None")

    # build the query string
    params = []

    for name, value in query.items():
        if type(value) in (list, tuple):
            params.extend(( name, i ) for i in value if i is not None)
        elif value is not None:
            if value is True: value = 'true'
            elif value is False: value = 'false'
            params.append(( name, value ))

    if params: path.extend([ '?', urlencode(params, doseq=True) ])
    return ''.join(path)


class HTTPError(client.HTTPException):
    """
    Base class for errors based on HTTP status codes >= 400 and redirection.
    """


class PreconditionFailed(HTTPError):
    """
    Exception raised when a 412 HTTP error is received in response to a
    request.
    """


class RedirectLimitExceeded(HTTPError):
    """Exception raised when a request is redirected more often than allowed
    by the maximum number of redirections.
    """

class ResourceConflict(HTTPError):
    """
    Exception raised when a 409 HTTP error is received in response to a
    request.

    Usually the case when trying to update a document with mismatching
    ``_rev`` values (eg., because another thread updated the same document
    a moment earlier).
    """


class ResourceNotFound(HTTPError):
    """
    Exception raised when a 404 HTTP error is received in response to a
    request.
    """


class Unauthorized(HTTPError):
    """
    Exception raised when the server requires authentication credentials
    but either none are provided, or they are incorrect (HTTP 401).
    """


class ServerError(client.HTTPException):
    """
    Exception raised when an unexpected HTTP error is received in response
    to a request.
    """


class Headers(dict):
    """
    A simple dict implementation that ensures header names (the dict's keys)
    are always stored as lower-case, but usually returned in their correct
    capitalized format from an iterator or methods that return keys.
    """

    @staticmethod
    def _format(key:str) -> str:
        items = list(part.capitalize() for part in key.split('-'))

        for name in ('Md5', 'Te', 'P3p', 'Www'):
            if name in items:
                items[items.index(name)] = name.upper()

        if 'Etag' in items:
            items[items.index('Etag')] = 'ETag'

        return "-".join(items)

    def __getitem__(self, key:str) -> object:
        return dict.__getitem__(self, key.lower())

    def __setitem__(self, key:str, value:object):
        return dict.__setitem__(self, key.lower(), value)

    def __contains__(self, key:str) -> bool:
        return dict.__contains__(self, key.lower())

    def __delitem__(self, key:str):
        #return dict.__delattr__(self, key.lower())
        return dict.__delitem__(self, key.lower())

    def __iter__(self) -> iter:
        return self.keys()

    def copy(self):
        return Headers(dict.copy(self))

    def get(self, key:str, default:object=None) -> object:
        return dict.get(self, key.lower(), default)

    def items(self) -> iter([(str, object)]):
        for k, v in dict.items(self):
            yield Headers._format(k), v

    def keys(self) -> iter:
        for k in dict.keys(self):
            yield Headers._format(k)

    def pop(self, key:str, default:object=None) -> object:
        return dict.pop(self, key.lower(), default)

    def setdefault(self, key:str, default:object=None) -> object:
        return dict.setdefault(self, key.lower(), default)


class ResponseStream(client.HTTPResponse):
    """
    A :class:`http.client.HTTPResponse` extended with stream iteration and
    string casting.

    If the stream has a charset - ie., that attribute has been set - instances
    of this class can be converted to strings by casting to `str`, but this
    consumes the entire stream. Otherwise, if the stream is treated as an
    iterator, the decoded (byte!) lines are yielded, by reading small amounts
    of bytes off the stream at a time.
    """

    # Changes to the original implementation by Christopher Lenz:
    # No mangling with the http.client API to stay conform with what is
    # provided. Less headaches, less problems, and mostly just as elegant...
    # Data is read using read, but only fetched in small chunks at a time
    # and the iterator can be used even if this is not a chunked response!

    __CHUNK_SIZE = 0xFF
    # byte-size of chunks we read off the stream

    def __init__(self, *args, **kwds):
        client.HTTPResponse.__init__(self, *args, **kwds)
        assert not hasattr(self, 'charset'),\
            'http.client API change: charset attribute added'
        self.charset = None

    def __str__(self):
        if not self.charset: # also raises if charset should be just empty
            raise TypeError('no charset')

        return self.read().decode(self.charset)

    def __iter__(self):
        last_chunk = b''

        while True:
            chunk = self.read(ResponseStream.__CHUNK_SIZE)
            if last_chunk: chunk = b''.join((last_chunk, chunk))
            lines = chunk.splitlines()
            last_chunk = lines.pop()

            for l in lines:
                # skip empty ("heartbeat") lines
                if l: yield l

            if self.closed: break

        if last_chunk: yield last_chunk


class Request:

    def __init__(self, method:str, url:str, body=None,
                 headers:Headers=None, credentials:tuple([str, str])=None,
                 cached_response=None):
        self.body = body
        self.method = method
        self.split_url = urlsplit(url, scheme='http')
        self.selector = urlunsplit(('', '') + self.split_url[2:4] + ('',))
        self.L = logging.getLogger(
            "Request({} {})".format(method, self.selector)
        )
        self.cached_response = cached_response
        self._headers = headers or Headers()

        self._chunked = False
        self.__received = False
        self.__sent = False
        self._initHeaders(credentials)

    def _initHeaders(self, credentials:(str, str)):
        self._headers.setdefault('Accept', 'application/json')
        self._headers.setdefault('Accept-Encoding', 'utf-8')
        self._headers.setdefault('User-Agent', USER_AGENT)

        if self.cached_response:
            etag = self.cached_response.headers.get('ETag')
            self._headers['If-None-Match'] = etag

        if not self.body:
            self._headers['Content-Length'] = '0'

        if credentials:
            self._headers['Authorization'] = \
                'Basic %s'.format(b64encode('%s:%s' % credentials))

        if self._headers.get('Transfer-Encoding') == 'chunked':
            self._chunked = True

    def setHeader(self, name, value):
        if self.__sent:
            raise RuntimeError("request already being sent")

        self._headers[name] = value

    def setHeaderUnlessExists(self, name, value):
        if self.__sent:
            raise RuntimeError("request already being sent")

        self._headers.setdefault(name, value)

    def send(self, conn:client.HTTPConnection) -> client.HTTPResponse:
        self.__sent = True
        self.L.debug("body=%s\n%s", self.body is not None,
                     '\n'.join(': '.join(h) for h in self._headers.items()))

        try:
            if self._chunked:
                self._sendChunked(conn)
            else:
                if hasattr(self.body, "read"):
                    if not hasattr(self.body, "fileno") or \
                       isinstance(self.body, StringIO):
                        self.body = self.body.read()

                conn.request(self.method, self.selector, self.body,
                             self._headers)

            return conn.getresponse()
        except client.BadStatusLine as e:
            # http raises a BadStatusLine when it cannot read the status
            # line saying, "Presumably, the server closed the connection
            # before sending a valid response."
            # Raise as ECONNRESET to simplify retry logic.
            if e.line == '' or e.line == "''":
                raise socket.error(errno.ECONNRESET)
            else:
                raise

    def _sendChunked(self, conn:client.HTTPConnection):
        conn.putrequest(self.method, self.selector,
                        skip_accept_encoding=True)

        for header, value in self._headers.items():
            conn.putheader(header, value)

        conn.endheaders()

        def send_line(line):
            chunk = line.rstrip()

            if chunk:
                if hasattr(chunk, 'encode'):
                    # http.client API and HTTP spec conform encoding!
                    chunk = chunk.encode('iso-8859-1')

                chunk = (b'%x\r\n' % len(chunk)) + chunk + b'\r\n'
                conn.send(chunk)

        if hasattr(self.body, 'readline'):
            line = self.body.readline()

            while line:
                send_line(line)
                line = self.body.readline()
        else:
            for line in self.body.splitlines():
                send_line(line)


class Session(object):

    CACHE_SIZE = (0xFFFFF, 0xFFFFFF) # 1 MB, 16 MB
    """
    Tuple defining (retain, max) bytes of response data.

    If the *max* cache size is reached or exceeded, all records in the cache
    are dropped until the value is equal or below *retain* again.
    """

    def __init__(self, cache:dict=None, timeout:int=None, max_redirects:int=5,
                 retry_delays:list=None,
                 retryable_errors:set=RETRYABLE_ERRORS):
        """
        Initialize an HTTP client session.

        :param cache: An instance with a dict-like interface or None to allow
                      the session to create a dict for caching, consisting of
                      URL keys and response values.
        :param timeout: Socket timeout in number of seconds, or ``None`` for no
                        timeout.
        :param max_redirects: The max. number of redirects before raising a
                              :exc:`RedirectLimitExceeded` exception.
        :param retry_delays: A list of request retry delays (default: ``[0]``,
                             meaning only one immediate retry).
        :param retryable_errors: A set of :mod:`errno` numbers for the
                                 socket errors that should lead to a retry
                                 of a failed request.
        """
        if cache is None: cache = {}
        self.cache = cache
        self.cache_size = sum(len(r.data) for r in cache.values())
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.retry_delays = list(retry_delays) if retry_delays else [0]
        self.retryable_errors = frozenset(retryable_errors)
        self.perm_redirects = {} # { url: url }
        self.pool = defaultdict(list) # HTTP conn pool by (scheme, netloc)
        self.lock = Lock()

    def _cachedResponse(self, method, url):
        cached_resp = None

        # Add the ETag if we have a cached response for that URL
        if method in ('GET', 'HEAD'):
            cached_resp = self.cache.get(url)

        return cached_resp

    def request(self, method:str, url:str,
                body:object=None,
                headers:Headers=None,
                chunked:bool=False,
                credentials:tuple([str, str])=None,
                num_redirects:int=0) -> (int, client.HTTPMessage, RawIOBase):
        """
        Make a *method* request to *url*.

        This will send a request to a server using the HTTP request *method*
        and the selector *url*. If the *body* argument is present, it should
        be a `str` or `bytes` object of data to send after the headers are
        finished. Strings are encoded as UTF-8. To use other encodings, pass
        a `bytes` object and add the charset value in the header. The
        Content-Length header is set to the length of the string.

        The *body* may also be an open file object, in which case the contents
        of the file is sent; this file object should support `fileno()` and
        `read()` methods. The header Content-Length is automatically set to
        the length of the file as reported by stat.

        The headers argument should be a mapping of extra HTTP headers to
        send with the request.

        :param method: "GET", "POST", "DELETE", or "PUT"
        :param url: The full URL for the request.
        :param body: The body, as `str`, `bytes`, or a file-like object.
        :param headers: The request :class:`.Headers` to use.
        :param chunked: If a chunked response may be passed on or read
            immediately
        :param credentials: A (username, password) tuple or None; credentials
            may not form part of the URL.
        :param num_redirects: The number of times this request has been
            redirected already (counter).
        :return: A tuple of (status, response_message, data).
        :raises TypeError: If a JSON encoding error occurred.
        :raises HttpError: If any of the documented HTTP errors occurred.
        :raises ServerError: If any error with the server response occurred.
        :raises RedirectLimitExceeded: If too many redirects occurred.
        :raises ValueError: If the URL is invalid or the scheme is not
            supported (only http and https are).
        """
        if url in self.perm_redirects: url = self.perm_redirects[url]
        cached_response = self._cachedResponse(method, url)
        request = Request(method, url, body, headers, credentials,
                          cached_response)
        retries = iter(self.retry_delays)
        response = None
        conn = self._getConnection(request.split_url)

        while True:
            try:
                response = request.send(conn)
                break
            except socket.error as e:
                ecode = e.args[0]

                if ecode not in self.retryable_errors:
                    request.L.exception("%s error (%s)",
                                        errno.errorcode[ecode],
                                        strerror(ecode))
                    raise

                try:
                    delay = next(retries)
                except StopIteration:
                    # No more retries, raise last socket error.
                    request.L.error("%s error (%s)", errno.errorcode[ecode],
                                    strerror(ecode))
                    raise e

                conn.close()
                time.sleep(delay) # Wait a bit and get a fresh connection
                conn = self._getConnection(request.split_url)

        L = logging.getLogger("Response({} {})".format(request.method,
                                                       request.selector))
        status = response.status
        L.debug("HTTP %s (%s)\n%s", client.responses[status], status,
                '\n'.join(': '.join(h) for h in response.getheaders()))

        ctype = response.msg.get('Content-Type', 'application/json')
        ccntrl = response.msg.get('Cache-Control')

        # Find the charset (if any)
        charset = 'iso-8859-1'

        if ctype and 'charset' in ctype:
            for content_split in ctype.split(";"):
                if 'charset' in content_split:
                    try:
                        charset = content_split.split('=')[1].strip()
                    except IndexError:
                        L.error("charset not where expected in '%s'", ctype)
                        charset = None
        elif 'application/json' in ctype:
            charset = 'utf-8' # default to UTF-8
        elif not ctype.startswith('text/'):
            charset = None # unset the charset for non-text types

        # Handle errors
        if status >= 400:
            data = response.read()
            response.close()
            self._returnConnection(request.split_url, conn)

            if data and 'application/json' in ctype:
                data = DecodeJson(data.decode(charset))
                error = "{}: {}".format(data.get('error'), data.get('reason'))
            elif data and charset:
                error = data.decode(charset)
            else:
                error = 'unspecified'

            if status == 401:
                #noinspection PyExceptionInherit,PyArgumentList
                raise Unauthorized(error)
            elif status == 404:
                #noinspection PyExceptionInherit,PyArgumentList
                raise ResourceNotFound(error)
            elif status == 409:
                #noinspection PyExceptionInherit,PyArgumentList
                raise ResourceConflict(error)
            elif status == 412:
                #noinspection PyExceptionInherit,PyArgumentList
                raise PreconditionFailed(error)
            else:
                error = "{} ({}): {}".format(client.responses[status],
                                             status, error)
                #noinspection PyExceptionInherit,PyArgumentList
                raise ServerError(error)

        # Handle redirects
        elif status == 303 or \
           method in ('GET', 'HEAD') and status in (301, 302, 307):
            # Read the full response for empty responses so that the connection
            # is in good state for the next request
            response.read()
            response.close()
            self._returnConnection(request.split_url, conn)

            if num_redirects > self.max_redirects:
                #noinspection PyExceptionInherit,PyArgumentList
                raise RedirectLimitExceeded('redirection limit exceeded')

            location = response.getheader('Location')

            if status == 301:
                self.perm_redirects[url] = urlunsplit(urlsplit(location))
            elif status == 303:
                method = 'GET'

            L.debug("%s: redirected to %s", url, location)
            return self.request(method, location, body, headers,
                                num_redirects=num_redirects + 1)

        # ETag: Fetch data from cache (NOT MODIFIED)
        elif status == 304 and cached_response and method in ('GET', 'HEAD') \
             and ccntrl != 'must-revalidate':
            # Read the full response for empty responses so that the connection
            # is in good state for the next request
            response.read()
            response.close()
            self._returnConnection(request.split_url, conn)
            L.debug('using cached response')
            return cached_response

        # Delete the cache, it is invalid
        elif cached_response:
            self.cache_size -= len(self.cache[url].data)
            del self.cache[url]

        # No errors, redirect, or cached response - let's build a real Response
        headers = response.msg
        data = None
        streamed = False

        if method == 'HEAD' or headers.get('Content-Length') == '0' or \
           status < 200 or status in (204, 304):
            # Read the full response for empty responses so that the connection
            # is in good state for the next request
            response.read()
            response.close()
            self._returnConnection(request.split_url, conn)
        elif chunked and headers.get('Transfer-Encoding') == 'chunked':
            L.debug("body: <chunked>")
            streamed = True
            response.charset = charset
            data = response
            # Note: streamed responses cannot re-pool connections
            # as their sockets stay open for an unknown time.
        else:
            data = response.read()
            response.close()
            self._returnConnection(request.split_url, conn)

        result = Response(status, headers, charset, data)

        # Cache non-chunked responses from GET requests that have an ETag header
        if not streamed and method == 'GET' and 'etag' in response.msg and \
           ccntrl != 'no-cache':
            L.debug('caching response')
            if url in self.cache: self.cache_size -= len(self.cache[url].data)
            self.cache[url] = result
            self.cache_size += len(result.data)
            if self.cache_size > Session.CACHE_SIZE[1]: self._cleanCache()

        return result

    def _cleanCache(self):
        def cache_sort(key_val):
            date = key_val[1].headers['Date']
            t = time.mktime(time.strptime(date[5:-4], '%d %b %Y %H:%M:%S'))
            return datetime.fromtimestamp(t)

        for url, response in sorted(self.cache.items(), key=cache_sort):
            del self.cache[url]
            self.cache_size -= len(response.data)
            if self.cache_size < Session.CACHE_SIZE[0]: break

    def _connectTo(self, url:namedtuple) -> client.HTTPConnection:
        if url.scheme == 'http':
            Connection = client.HTTPConnection
        elif url.scheme == 'https':
            Connection = client.HTTPSConnection
        else:
            raise ValueError('scheme %s not supported'.format(url.scheme))

        conn = Connection(url.netloc, timeout=self.timeout)
        conn.response_class = ResponseStream

        #if self.L.isEnabledFor(logging.DEBUG):
        #    conn.set_debuglevel(1)

        conn.connect()
        return conn

    def _getConnection(self, url:namedtuple) -> client.HTTPConnection:
        """
        Return an open connection to the given scheme and netloc in the
        **split** *URL*.

        Returns a :class:`http.client.HTTPSConnection` if `url.scheme` is
        ``'https'``.
        """
        conn = None
        self.lock.acquire()

        try:
            conns = self.pool[(url.scheme, url.netloc)]

            while conns:
                conn = conns.pop()
                if conn.sock: break
                else: conn.close()

            if not (conn and conn.sock):
                conn = self._connectTo(url)
        finally:
            self.lock.release()

        return conn

    def _returnConnection(self, url:namedtuple, conn:client.HTTPConnection):
        self.lock.acquire()

        try:
            self.pool[(url.scheme, url.netloc)].append(conn)
        finally:
            self.lock.release()


class Resource:
    """
    To PUT or POST any data using **chunked Transfer-Encoding**, you must add
    the ``header={'Transfer-Encoding': 'chunked'}`` to the call.
    """

    def __init__(self, url:str, session:Session=None, headers:dict=None):
        """
        Create a new web resource for a fixed base URL.

        :param url: The base URL for this resource.
        :param session: The session object to (re-)use.
        :param headers: A set of constant headers to send.
        """
        if url.endswith('/'): url = url[:-1]
        self.url, self.credentials = ExtractCredentials(url)
        self.session = Session() if session is None else session
        self.headers = Headers() if headers is None else Headers(headers)

    def __call__(self, *segments:[str]):
        """
        Create a new instance from the current one, but append the *path*
        items to the current instance' URL.

        :param segments: One string per path element.
        :return: A new instance.
        :rtype: `Resource`
        """
        obj = type(self)(UrlJoin(self.url, segments),
                         self.session, self.headers)
        obj.credentials = self.credentials
        return obj

    def delete(self, *path:[str], headers:dict=None,
               **params:{str:object}) -> Response:
        """
        Make a DELETE request.

        :param path: The path segments.
        :param headers: Optional headers for the request.
        :param params: Optional query parameters for the URL.
        :return: A `Response` named tuple.
        :rtype: :class:`.Response`
        """
        return self._request('DELETE', path, headers=headers, **params)

    def deleteJson(self, *path:[str], headers:dict=None,
                    **params:{str:object}) -> Response:
        """
        Make a DELETE request, expecting a JSON response.

        :param path: The path segments.
        :param headers: Optional headers for the request.
        :param params: Optional query parameters for the URL.
        :return: A `Response` named tuple.
        :rtype: :class:`.Response`, with the :attr:`Response.data` decoded
                to a Python object.
        :raise TypeError: If the response data is not JSON.
        """
        _, headers = self._prepareJson(None, headers)
        response = self.delete(*path, headers=headers, **params)
        return self._decodeJson(response)

    def get(self, *path:[str], headers:dict=None,
            **params:{str:object}) -> Response:
        """
        Make a GET request.

        :param path: The path segement.
        :param headers: Optional headers for the request.
        :param params: Optional query parameters for the URL.
        :return: A `Response` named tuple.
        :rtype: :class:`.Response`
        """
        return self._request('GET', path, headers=headers, **params)

    def getJson(self, *path:[str], headers:dict=None,
                 **params:{str:object}) -> Response:
        """
        Make a GET request, expecting a JSON response.

        :param path: The path segments.
        :param headers: Optional headers for the request.
        :param params: Optional query parameters for the URL.
        :return: A `Response` named tuple.
        :rtype: :class:`.Response`, with the :attr:`Response.data` decoded
                to a Python object.
        :raise TypeError: If the response data is not JSON.
        """
        _, headers = self._prepareJson(None, headers)
        response = self.get(*path, headers=headers, **params)
        return self._decodeJson(response)

    def head(self, *path:[str], headers:dict=None,
             **params:{str:object}) -> Response:
        """
        Make a HEAD request.

        :param path: The path segements.
        :param headers: Optional headers for the request.
        :param params: Optional query parameters for the URL.
        :return: A `Response` named tuple.
        :rtype: :class:`.Response`
        """
        return self._request('HEAD', path, headers=headers, **params)

    def post(self, *path:[str], body:object=None, headers:dict=None,
             **params:{str:object}) -> Response:
        """
        Make a POST request.

        If body is a string or :class:`io.TextIOBase` object, it it will
        be encoded using Latin-1 by the :class:`http.client.HTTPConnection`.

        :param path: The path segments.
        :param body: A `str`, `bytes` or file-like object.
        :param headers: Optional headers for the request.
        :param params: Optional query parameters for the URL.
        :return: A `Response` named tuple.
        :rtype: :class:`.Response`
        """
        return self._request('POST', path, body, headers, **params)

    def postJson(self, *path:[str], json:object=None, headers:dict=None,
                 **params:{str:object}) -> Response:
        """
        Make a POST request, expecting a JSON response.

        :param path: The path segments.
        :param json: A Python object that can be serialized to JSON.
        :param headers: Optional headers for the request.
        :param params: Optional query parameters for the URL.
        :return: A `Response` named tuple.
        :rtype: :class:`.Response`, with the :attr:`Response.data` decoded
                to a Python object.
        :raise TypeError: If the response data is not JSON.
        """
        json, headers = self._prepareJson(json, headers)
        response = self.post(*path, body=json, headers=headers, **params)
        return self._decodeJson(response)

    def put(self, *path:[str], body:object=None, headers:dict=None,
            **params:{str:object}) -> Response:
        """
        Make a PUT request.

        :param path: The path segments.
        :param body: A `str`, `bytes` or file-like object.
        :param headers: Optional headers for the request.
        :param params: Optional query parameters for the URL.
        :return: A `Response` named tuple.
        :rtype: :class:`.Response`
        """
        return self._request('PUT', path, body, headers, **params)

    def putJson(self, *path:[str], json:object=None, headers:dict=None,
                **params:{str:object}) -> Response:
        """
        Make a PUT request, expecting a JSON response.

        :param path: The path segments.
        :param json: A Python object that can be serialized to JSON.
        :param headers: Optional headers for the request.
        :param params: Optional query parameters for the URL.
        :return: A `Response` named tuple.
        :rtype: :class:`.Response`, with the :attr:`Response.data` decoded
                to a Python object.
        :raise TypeError: If the response data is not JSON.
        """
        json, headers = self._prepareJson(json, headers)
        response = self.put(*path, body=json, headers=headers, **params)
        return self._decodeJson(response)

    @staticmethod
    def _decodeJson(response:Response) -> Response:
        if isinstance(response.data, ResponseStream):
            return response # streamed data... let the receiver decide
        else:
            json = DecodeJson(response.data.decode(response.charset))
            return response._replace(data=json)

    @staticmethod
    def _prepareJson(json:object, headers:dict) -> (bytes, Headers):
        if json is not None: json = EncodeJson(json).encode()
        headers = Headers(headers) if headers else Headers()
        headers.setdefault('Content-Type', 'application/json; charset=utf-8')
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('Accept-Encoding', 'utf-8')
        return json, headers

    def _request(self, method:str, path:list, body:object=None,
                 headers:dict=None, chunked:bool=False,
                 **params:{str: object}) -> Response:
        """
        Make a request to the resource, returning :class:`.Response`.

        :param method: The name of the method (GET, PUT, POST, DELETE, HEAD,
            COPY).
        :param path: The the path to the resource, as segments.
        :param body: The body of the request, if any.
        :param headers: The headers of the request, if any.
        :param chunked: Use ``True`` if a :class:`.ResponseStream` from chunked
            responses is allowed to be returned (instead of forcing the read
            in any case).
        :param params: Additional URL parameters.
        """
        all_headers = self.headers.copy()
        if headers: all_headers.update(headers)
        url = UrlJoin(self.url, path, **params)
        return self.session.request(method, url, body=body,
                                    headers=all_headers,
                                    chunked=chunked,
                                    credentials=self.credentials)


