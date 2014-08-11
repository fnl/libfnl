"""
.. py:module:: fnl.text.text
   :synopsis: A data type to annotate strings.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from bisect import insort

from .segment import segment
from .token_new import token


class text(str):

    """
    Tag strings with offset-based **segments** and **tokens**, collectively called **tags**.

    Segments are named tuples with four values::

        s = segment( text, offset, namespace, identifier )

    Segments be "real" segements or just **annotations** (segments that cannot contain
    other segments).
    Unlike markup language elements, segments contained by the same parent can be *overlapping*::

        <s1>abc<s2>def</s1>ghi</s2>

    Segment **offsets** are tuples of 1 or 2n integers with n > 0::

        offset = ( begin, [[pos, pos]... end] )

    A single (begin) offset annotates **between** characters;
    I.e. the offset ``(0,)`` annotates the position before the first character.
    The offset ``(3,)`` annotates the position between character 3 and 4.
    *Tokens* are named tuples with several values::

        t = tuple( text, offset, stem, ... )

    Tokens may neither overlap nor can they "contain" other tokens.
    Token offsets always must be ``( begin, end )`` tuples.
    """

    KEY = lambda tag: (tag.offset[0], -tag.offset[-1], tag)
    """
    Ordering of tags in forward offset order (lowest begin, highest end).
    """

    REVERSE_KEY = lambda tag: (-tag.offset[-1], tag.offset[0], tag)
    """
    Sort key for tags in reverse offset order (highest end, lowest begin).

    Not used anywhere, but provided for convenience, especially for
    :meth:`.Text.tags`.

    .. note::

        The reversed offset order is not the same as reversing the list
        offset-ordered tags -- i.e.::

            reversed(sorted(tags, key=text.KEY)) != sorted(tags, key=text.REVERSE_KEY)
    """

    def __new__(cls, string, *args, **kwds):
        return str.__new__(cls, string)

    def __init__(self, string, uid=None, segments=None, tokens=None):
        """
        Constructing a `text` instance might raise any exception that
        :meth:`.add` might raise.

        :param string: The string to annotate or another `text` instance to copy.
        :param uid:
        :param segments: A list of segment annotations; Ignored if `string` is a
            `text` instance.
        :param tokens: A list of token annotations; Ignored if `string` is a
            `text` instance.
        :raise TypeError: If *string* is neither a `str` or a `text` instance.
        """
        super(text, self).__init__()

        if isinstance(string, text):
            # deep copy the text
            self.__copy(string)
        elif isinstance(string, str):
            # create a new instance
            self.__make(uid, segments, tokens)
        else:
            raise TypeError("string neither a str or text instance")

    def __copy(self, other):
        """Deepcopy helper."""
        copy = lambda items: [i.Update(text=self) for i in items]
        self._digest = other._digest
        self.uid = other.uid
        self._segments = {
            ns: copy(segments) for ns, segments in other._segments.items()
        }
        self._tokens = {
            ns: copy(tokens) for ns, tokens in other._tokens.items()
        }

    def __make(self, uid, segments, tokens):
        """Instantiation helper."""
        self.uid = uid
        self._digest = None
        self._segments = {}
        self._tokens = {}

        if segments is not None:
            self.AddSegments(segments)

        if tokens is not None:
            self.AddTokens(tokens)

    def AddSegments(self, segments):
        """
        Add one or more segments.

        Segments are always maintained in order with respect to their namespace.
        """
        text._Add(segments, self._segments, segment)

    def AddTokens(self, tokens):
        """
        Add one or more tokens.

        Tokens are always maintained in order with respect to their namespace.
        """
        text._Add(tokens, self._tokens, token)

    @staticmethod
    def _Add(items, collection, item_type):
        """Add tokens or segments to their dictionaries."""
        if isinstance(items, item_type):
            items = [items]

        novel = text._InsortOrCollect(items, collection)

        for namespace, values in novel.items():
            collection[namespace] = sorted(values)

    @staticmethod
    def _InsortOrCollect(items, collection) -> dict:
        """Insort tokens/segments for existing namespaces and return items for new namespaces."""
        tmp = {}

        for i in items:
            if i.namespace in collection:
                insort(collection[i.namespace], i)
            elif i.namespace in tmp:
                tmp[i.namespace].append(i)
            else:
                tmp[i.namespace] = [i]

        return tmp

    # def __contains__(self, tag) -> bool:
        #"""Check if that *tag* is annotated on this text."""
        # if isinstance(tag, segment):
        # return self._segments \
        # and tag.ns in self._segments \
        # and tag in self._segments[tag.ns]
        # elif isinstance(tag, token):
        # return tag in self._tokens

        # return False

    # def __delitem__(self, idx):
        #"""
        # Delete all **tokens** at *idx* in text (optionally, a slice, too).

        # If the slice' step evaluates to ``True``, only tags that are
        # completely contained in the slice are deleted.
        #"""
        #tokens = self.__GetTokens(idx)
        # self.remove(tokens)

    # def __eq__(self, other) -> bool:
        #"""
        # Compare two text instances at the level of its **string** and **tags**.

        # To ensure text1 **is** text2, use `is`, not ``==``.
        #"""
        # if isinstance(other, text) \
        # and self._string == other._string \
        # and self._tokens == other._tokens \
        # and self._semgents == other._segments:
        # return True

        # return False

    # def __iter__(self) -> iter:
        #"""Iterate over all **tokens**."""
        # return iter(self._tokens)

    # def __getitem__(self, idx) -> iter:
        #"""
        # Get all **tokens** at a character position in text; optionally, a slice.

        # If the slice step evaluates to ``True``, only tokens that are
        # completely contained in the slice are fetched.
        #"""
        # return sorted(self.__GetTokens(idx))

    # def __GetTokens(self, idx):
        # if isinstance(idx, slice):
        #start, stop, inside = self.__unslice(idx)
        # else:
        # if idx < 0:
        #idx += len(self._string)

        #start, stop, inside = idx, idx + 1, False

        # if inside:
        #in_range = lambda t: t.offset[0] >= start and t.offset[-1] <= stop
        # else:
        #in_range = lambda t: t.offset[0] < stop and t.offset[-1] > start

        # for tok in filter(in_range, self._tokens):
        # yield tok

    # def __len__(self) -> int:
        #"""The text length."""
        # return len(self._string)

    # def __repr__(self) -> str:
        #"""The text representation."""
        # return repr(self._string)

    # def __reversed__(self) -> iter:
        #"""Ensure using ``reversed()`` does not produce unexpected results."""
        # return iter(self)

    # def __setitem__(self, key, values):
        #"""Set a tag on a position, span, or offset tuple."""
        ## text[10] = 'ns', 'id'
        ## text[10:20] = 'ns', 'id'
        ## text[10:20] = 'ns', 'id', {'attr': 'value'}
        ## text[(10,15,18,20)] = 'ns', 'id'
        # Note: The key may contain additional colon characters.
        # Note: Slice step values are ignored.
        # Note: A rather inefficient way to add tags!
        # if isinstance(key, slice):
        #start, stop, _ = self.__unslice(key)
        #offset = (start, stop)
        # elif isinstance(key, tuple):
        #offset = key
        # else:
        #offset = (int(key),)

        # if len(values) == len(segment._fields) - 2:
        #s = segment(text, offset, *values)

        # if s.ns in self._segments:
        #insort(s, self._segments[s.ns])
        # else:
        #self._segments[s.ns] = [s]
        # elif len(values) == len(token._fields) - 2:
        #insort(token(text, offset, *values), self._tokens)
        # else:
        #raise ValueError('values %r not a tag' % repr(values))

    # def __str__(self) -> str:
        # return self._string

    # def __unslice(self, s):
        #"""Decompose a slice into start, stop, step."""
        #l = len(self._string)

        # if not s.start:
        #start = 0
        # elif s.start < 0:
        #start = l + s.start
        # else:
        #start = s.start

        # if start < 0:
        #start = 0

        # if s.stop is None:
        #stop = l
        # elif s.stop < 0:
        #stop = l + s.stop
        # else:
        #stop = s.stop

        # if stop > l:
        #stop = l

        # return start, stop, s.step

    # Segment Methods

    # def get(self, namespace=None) -> iter:
        #"""
        # An iterator over the segments annotated on this text, optionally only for one namespace.

        #:param namespace: only segments for that namespace
        #:raise KeyError: If the *namespace* does not exist.
        #"""
        # if namespace:
        # return iter(self._segments[namespace])
        # else:
        # return sorted(chain(*self._segments.values()))

    #@property
    # def namespaces(self) -> iter:
        #"""An iterator over all namespace strings of all segments."""
        # return self._segments.keys()

    # def remove(self, tokens=None, segments=None, namespace=None):
        #"""Remove one or more *tags* or an entire `namespace` of segments."""
        # if tokens:
        # if isinstance(tokens, token):
        #tokens = [tokens]

        # for tok in tokens:
        # self._tokens.remove(tok)

        # if segments:
        # if isinstance(segments, segment):
        #segments = [segments]

        # for seg in segments:
        # self._segments[seg.ns].remove(seg)

        # if len(self._segments[seg.ns]) == 0:
        #del self._segments[seg.ns]

        # if namespace is not None:
        #del self._segments[namespace]

    # def tags(self, key=Key) -> list:
        #"""
        # Return a list of **all** tags (without attributes), sorted by *key*.

        #:param key: By default, uses :obj:`.Text.Key` order.
        #"""
        # return sorted(self, key=key)

    # def tagsAsDict(self) -> dict:
        #"""
        # Return **all** tags and attributes as a dictionary that can be used to
        # serialize the annotations.

        # An example:

        #>>> from fnl.text.text import Text
        #>>> text = Text('example')
        #>>> text[2] = 'ns1', 'id1', {'a': 'v'}
        #>>> text[(1,3,4,6)] = 'ns1', 'id1'
        #>>> text.tagsAsDict()
        #{'ns1': {'id1': {'1.3.4.6': None, '2': {'a': 'v'}}}}

        #:return: A `dict` of all tags and attributes, grouped by namespace,
        # ID, (string) offsets (offset integers, joined with dots (``.``)).
        #"""
        #tags = dict()

        # for ns in self.namespaces:
        #attributes = self.attributes[ns]
        #ns_dict = tags[ns] = dict()

        # for tag in self._tags[ns]:
        #id_dict = ns_dict.setdefault(tag[1], {})
        #offsets = '.'.join(map(str, tag[2]))
        #attrs = attributes.get(tag)

        # if attrs:
        # assert all(map(lambda key: isinstance(key, str), attrs)), \
        #'key not a string: {}'.format(list(attrs.keys()))

        #id_dict[offsets] = attrs

        # return tags

    # def update(self, text):
        #"""
        # Update with tags and attributes from another `Text` instance that has
        # the same underlying string.

        # If you really need to update from another text with a different digest
        # and underlying string, you could simply use::

        # text.add(other.get())

        #.. seealso:: :meth:`.Text.add`

        #:param text: A `Text` instance.
        #:raise ValueError: If *text* is a `Text` instance, but the digests do
        # not match.
        #:raise TypeError: If *text* is not a `Text` instance.
        #"""
        # try:
        # if self.digest != text.digest:
        #raise ValueError('the two texts mismatch')
        # except AttributeError:
        #raise TypeError('{} not a Text instance'.format(repr(text)))

        # for ns in text.namespaces:
        #self._add(ns, text.get(ns))

    # String methods

    #@property
    # def base64digest(self) -> str:
        #"""
        # The base64-encoded ASCII string of the :attr:`.digest` without the
        # redundant ``=`` padding characters (read-only).
        #"""
        # return b2a_base64(self.digest)[:-3].decode('ASCII')

    #@property
    # def digest(self) -> bytes:
        #"""
        # The MD5 digest of the UTF-8 encoded text (read-only).
        #"""
        # if not self._digest:
        #self._digest = hashlib.md5(self.encode()).digest()

        # return self._digest

    # def encode(self, encoding: str='utf-8', errors: str='strict') -> bytes:
        #"""
        # Return the encoded text string.
        #"""
        # return self._TEXT.encode(encoding, errors)

    # def iter(self, namespace: str) -> iter:
        #"""
        # Iterate over the string tokens of all tags in a given *namespace*.

        # Tokens are named tuples to represent token strings for a given tag.
        # The tuple consists of an *id* string (the tag ID), *text* (the string),
        # and an *attributes* dictionary (as set on the tag; possibly ``None``).

        #:param namespace: The namespace to iterate over
        #:return: Named tuples of ``(id, text, attributes)`` values.
        #"""
        #attributes = self.attributes[namespace]

        # for t in self._tags[namespace]:
        #off = t[2]

        # if len(off) > 2:
        # text = ''.join(self._FIX[off[i]:off[i + 1]]
        # for i in range(0, len(off), 2))
        # else:
        #text = self._FIX[off[0]:off[-1]]

        # yield Text._Token(t[1], text, attributes.get(t))

    #@property
    # def string(self) -> str:
        #"""
        # This is a special (read-only) property that should be used when taking
        #**slices** or retrieving individual characters of the text's string.

        # This property is provided to circumvent the problem of wrong offset
        # counts when using narrow Python builds where Unicode is based on
        # UTF-16 characters, and Surrogate Pairs normally are counted as length
        # 2::

        #.. doctest::

        #>>> from fnl.text.text import Text
        #>>> text = Text('abc\U0010ABCDabc')
        # >>> text.string[3] # SP \udbea\udfcd of length 2 on narrow builds
        #'\\U0010abcd'
        #>>> text.string[2:5]
        #'c\\U0010abcda'
        #>>> for char in text.string:
        #...     print(char)
        # a
        # b
        # c
        #\U0010ABCD
        # a
        # b
        # c
        #>>> len(text.string)
        # 7
        #>>> text.string
        #'abc\\U0010abcdabc'
        #>>> isinstance(text.string, str)
        # True

        #.. note::

        # If you wish to access the entire string, you can also just use
        #``str(text)``.
        #"""
        # return self._FIX

    # Byte Offset Maps

    #@property
    # def utf8(self) -> tuple:
        #"""
        # A tuple of byte-offsets of each character in UTF-8 encoding
        #(read-only).

        # The tuple is one element longer than the text characters, with the
        # last element representing the total length of the encoded string.
        # The first element starts at 0 bytes (the possible, but unusual 3 byte
        # UTF-8 BOM should never be counted).
        #"""
        # return self._utf('_utf8')

    # def _utf8(self):
        #offset = 0

        # for c in self.string:
        # yield offset
        #o = ord(c)
        # if o < 0x80:
        #offset += 1
        # elif o < 0x800:
        #offset += 2
        # elif o < 0x1000:
        #offset += 3
        # else:
        #offset += 4

        # yield offset

    #@property
    # def utf16(self) -> tuple:
        #"""
        # A tuple of byte-offsets of each character in UTF-16 encoding
        #(read-only).

        # The tuple is one element longer than the text characters, with the
        # last element representing the total length of the encoded string.
        # The first element starts at 2 bytes because of the 2 byte long Byte
        # Order Mark (BOM) in UTF-16 strings before the first character byte.
        #"""
        # return self._utf('_utf16')

    # def _utf16(self):
        # offset = 2  # 2 byte BOM

        # for c in self.string:
        # yield offset
        # if ord(c) > 0xFFFF:
        #offset += 4
        # else:
        #offset += 2

        # yield offset

    # def _utf(self, name: str) -> tuple:
        # if self._maps.get(name) is not None:
        #m = self._maps[name]
        # else:
        #m = tuple(getattr(self, name)())
        #self._maps[name] = m

        # return m

    # Text serialization

    #@classmethod
    # def fromJson(cls, json: dict):
        #"""
        # Create a `Text` instance without annotations, deserialized from a JSON
        # dictionary with the same keys as mentioned in :meth:`.toJson`.

        # Raises any exception that the `Text` constructor might.

        #:raise ValueError: If the JSON dictionary has no text or checksum,
        # or if the checksum match test fails for any reason.
        #"""
        # Create the text instance:
        # try:
        #text = cls(json['text'], **json.get('maps', {}))
        # except KeyError:
        #raise ValueError('text not present in raw JSON')

        # Ensure the checksum is correct:
        # try:
        #hex = None
        # checksum = {k.lower().replace('-', ''): v
        # for k, v in json['checksum'].items()}
        #encoding = checksum['encoding'].lower().replace('-', '')
        # except KeyError:
        #raise ValueError('checksum in raw JSON missing or malformed')
        # except AttributeError:
        #raise ValueError('checksum in raw JSON malformed')

        # if 'md5' in checksum:
        #hex = checksum['md5']

        # if encoding == 'utf8':
        #text_digest = text.digest
        # else:
        #text_digest = hashlib.md5(str(text).encode(encoding)).digest()
        # else:
        #hash_function = None

        # for hash_type in checksum:
        # try:
        #hash_function = getattr(hashlib, hash_type)
        #hex = checksum[hash_type]
        # except (NameError, AttributeError):
        # pass
        # else:
        # break

        # if hash_function is None:
        # msg = 'no known hash types ({})'.format(
        #', '.join(k for k in checksum.keys() if k != 'encoding')
        #)
        #raise ValueError(msg)

        #text_digest = hash_function(str(text).encode(encoding)).digest()

        # if text_digest != bytes(int(hex[i:i + 2], 16)
        # for i in range(0, len(hex), 2)):
        #raise ValueError('text and checksum mismatch')

        # return text

    # def toJson(self) -> dict:
        #"""
        # Serialize the text to a dictionary that can be encoded as a JSON
        # string.

        # Sets the following keys on the dictionary:

        #* text
        #* checksum
        #* maps
        #"""
        # return {
        #'text': self._TEXT,
        #'checksum': {
        #'encoding': 'utf8',
        #'md5': ''.join('{:x}'.format(b) for b in self.digest)
        #},
        #'maps': {
        #'utf8': self.utf8,
        #'utf16': self.utf16
        #}
        #}
