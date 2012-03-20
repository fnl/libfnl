"""
.. py:module:: json
   :synopsis: JSON data serializer.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)

Thin configuration layer over the json package in the standard library
with settings optimized for speed.
"""

from json.encoder import JSONEncoder
from json.decoder import JSONDecoder

from binascii import a2b_base64, b2a_base64

SAFE = bytearray(range(256))
SAFE[ord('+')] = ord('-')
SAFE[ord('-')] = ord('+')
SAFE[ord('/')] = ord('.')
SAFE[ord('.')] = ord('/')

__all__ = ['b64decode', 'b64encode', 'Decode', 'Encode']

def b64encode(b:bytes, charmap:bytes=SAFE) -> bytes:
    """
    A **CouchDB-URL**\ -safe version of the base64 encoding.

    After regular base64 encoding, any ``+`` is translated to ``-``, and ``/``
    to ``.`` (just as the base64 encoding for XML name tokens), not ``_`` (as
    URL-safe base64 encoding would do).

    If desired, the translation can be changed any time by providing a
    different character map (as a `bytearray` or `bytes` object of length 256,
    with the remapping of any characters as preferred).
    """
    return b2a_base64(b)[:-1].translate(charmap)

def b64decode(b:bytes, charmap:bytes=SAFE):
    """
    A **CouchDB-URL**\ -safe version of the base64 decoding.

    See :func:`.b64encode` for details.
    """
    return a2b_base64(b.translate(charmap))

def IsoformatSerializer(obj):
    """
    Serialization of any object that has a `isoformat()` method to JSON,
    particularly for date and time objects.
    """
    if isinstance(obj, set):
        return repr(list(obj))
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        raise TypeError(repr(obj) + " is not JSON serializable")


# Pre-load encoder/decoder instances with the fastest possible performance and
# most compact encoding. The decoder default is pretty much it; for the
# encoder, the extra whitespaces have been eliminated and the circular
# reference check deactivated. Finally, datetime objects are serialized, too.
DECODER = JSONDecoder()

ENCODER = JSONEncoder(check_circular=False, separators=(',', ':'),
                      allow_nan=False, default=IsoformatSerializer)


def Decode(string:str) -> object:
    """
    Decode a JSON *string* to a Python object.

    Contrary to :func:`.Encode`, it does not de-serialize date and time strings
    to `datetime` objects.
    """
    return DECODER.decode(string)


def Encode(obj:object) -> str:
    """
    Encode basic Python objects as the most compact JSON strings.

    In particular, the encoder also iso-formats date and time objects
    according to `ISO 8601 <http://en.wikipedia.org/wiki/ISO_8601>`_. Note
    that the circular reference check for lists and dictionaries has been
    deactivated.
    """
    return ENCODER.encode(obj)
