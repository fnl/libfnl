"""
.. py:module:: text
   :synopsis: Data types to annotate text.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import hashlib
from operator import itemgetter
from bintrees import FastRBTree as RBTree
from libfnl import PyUTF16
from libfnl.couch.serializer import b64encode

class Text:
    """
    Annotate strings with character-offset based :class:`.Text.Tag`\ s.

    Counting character offset for strings with Supplementary Multilingual
    Plane (SMP) codepoints works even on narrow Python builds, via a special
    fix for strings containing surrogate pairs.

    Tags retrieved from the subscript accessor (``__getitem__`` aka.
    ``text[<slice or idx>]``) and iterators are sorted by the lowest offset
    start, highest offset end. The `reversed` iteration of tags (ie.,
    ``reversed(text)``) starts with the highest offset end, lowest offset
    start.

    .. note::

        The reversed list is not always the same order as reversing the list
        of ``iter(text)`` -- ie., ``reversed(iter(text)) != reversed(text)``
        if there are nested tags.
    """

    class Tag(tuple):
        """
        A hashable annotation container for offset-based :class:`.Text` tags.

        Just as a named tuple, but with the ability to cast it to a string
        of the form ``<ns>:<id>:<o>`` (where ``<o>`` is a dot (.) separated
        list of offsets, to be XML-conform) and a pure `tuple`\ -representation
        (instead of the regular, but verbose `collections.namedtuple`
        representation).
        """

        __slots__ = ()

        _fields = ('ns', 'id', 'offsets')

        #noinspection PyInitNewSignature
        def __new__(cls, ns, id, offsets):
            return tuple.__new__(cls, (ns, id, offsets))

        #noinspection PyMethodOverriding
        def __getnewargs__(self):
            # Return self as a plain tuple. Used by copy and pickle.
            return tuple(self)

        def __repr__(self):
            return tuple.__repr__(self)

        def __str__(self):
            return '{}:{}:{}'.format(self.ns, self.id,
                                     '.'.join(map(str, self.offsets)))

        def _asdict(self):
            """
            Return a `dict` which maps field names to their values.
            """
            return dict(zip(self._fields, self))

        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            """
            Make a new :class:`.Text.Tag` object from a sequence or iterable.
            """
            result = new(cls, iterable)
            if len(result) != 3:
                raise TypeError('Expected 3 arguments, got %d' % len(result))
            return result

        def _replace(self, **kwds):
            """
            Return a new Tag object replacing specified fields with new values.
            """
            result = self._make(map(kwds.pop, ('ns', 'id', 'offsets'), self))

            if kwds:
                raise ValueError('unexpected field names: %r' % kwds.keys())

            return result

        ns = property(itemgetter(0), doc='The namespace of this tag.\n\n'
             'Should not contain colon (:) characters and; otherwise conform '
             'with XML element name specifications.'
        )
        id = property(itemgetter(1), doc='The ID of this tag.\n\n'
            'May contain any characters that are allowed for; XML element '
            'names.'
        )
        offsets = property(itemgetter(2), doc='A tuple of integers.\n\n'
            'Should consist of 1 or 2n integers where n > 0. If n > 1, it is '
            'a multi-span annotation.'
        )

    class StringFix:
        # A fix for offset problems in strings containing SMP characters on
        # narrow Python builds.

        def __init__(self, fixed:tuple):
            # *Fixed* is a tuple of codepoint-grouped strings where surrogate
            # pairs are represented as a single tuple element to duck-type the
            # same behaviour of strings on both Python builds.
            self.__fixed = tuple(fixed)
            self.__len = len(self.__fixed)

        def __getitem__(self, idx) -> str:
            return ''.join(self.__fixed[idx])

        def __iter__(self) -> iter:
            return iter(self.__fixed)

        def __len__(self) -> int:
            return self.__len

        def __str__(self) -> str:
            return ''.join(self.__fixed)

    def __init__(self, text, tags:iter=None, **utf_maps):
        """
        Constructing a `Text` instance might raise any exception that
        :meth:`.add` might raise in addition to those listed.

        :param text: The string to annotate or another `Text` instance to copy.
        :param tags: The tags holding the annotations; Ignored if *text* is a
            `Text` instance. May be an iterator of :class:`.Text.Tag`-like
            tuples or a dictionary consisting of those tags as keys and an
            attribute dictionary as value for each tag, adding additional
            metadata to a specific tag.
            To supply attributes only to a subset of the tags, any ``None``
            value in the *tags* dictionary is ignored.
        :param utf_maps: Provide pre-calculated maps for ``utf8``, ``utf16``,
            and ``utf32``. Normally, you should not supply them yourself, this
            parameter is used when creating `Text` instances from a
            deserializer and maps are dropped silently if they are incorrect.
        :raise TypeError: If *text* is neither a string or a `Text` instance.
        """
        if isinstance(text, Text): # deep copy from that instance
            self._TEXT = text._TEXT
            self._FIX = text._FIX
            self._digest = text._digest
            self._maps = dict(text._maps)
            self._keys = { ns: { key: set(leaf) for key, leaf in node.items()}
                           for ns, node in text._keys.items() }
            #noinspection PyArgumentList
            self._offsets = RBTree({start: RBTree({stop: set(tags) for
                                                  stop, tags in tree.items()})
                                    for start, tree in text._offsets.items()})
            self.attributes = { tag: dict(attrs) for tag, attrs in
                                text.attributes.items() }
        elif isinstance(text, str): # create a new instance
            self._TEXT = text # NB: immuteable!
            self._maps = dict()
            self._digest = None

            if PyUTF16:
                self._FIX = Text.StringFix(Text.__chars(text))
                # But only use this fix if there are SMP codepoints!
                if len(self._FIX) == len(self._TEXT): self._FIX = self._TEXT
            else:
                self._FIX = self._TEXT

            self.tags = list() if tags is None else tags

            if utf_maps:
                for name in ('utf8', 'utf16', 'utf32'):
                    if name in utf_maps:
                        try:
                            self._maps['_' + name] = \
                                self.__checkMap(utf_maps[name])
                        except TypeError:
                            pass # silently drop bad maps
                        except ValueError:
                            pass # silently drop bad maps
        else:
            raise TypeError('text not a Text or string')

    # Special and Private Methods

    def __add(self, tag:Tag, leaf:set):
        # Add tag to the _tagtree leaf and to _offsets.
        leaf.add(tag)
        start, stop = tag.offsets[0], -tag.offsets[-1]
        tree = self._offsets.setdefault(start, RBTree())
        if stop in tree: tree[stop].add(tag)
        else: tree[stop] = {tag}

    @staticmethod
    def __chars(text:str) -> iter:
        # For character count problems with narrow Python builds: an iterator
        # of real characters, joining surrogate pairs as one.
        char_iter = iter(text)

        while True:
            c = next(char_iter)

            if '\ud800' <= c < '\udc00':
                c += next(char_iter)
                assert '\udc00' <= c[1] < '\ue000'

            yield c

    def __checkMap(self, map:iter) -> tuple:
        map = tuple(int(i) for i in map)
        textlen = len(self)

        if textlen != len(map): # must be as long as the text has characters
            raise ValueError('map length != text length')

        if not textlen: # if the text has no characters, we are fine already
            return map

        if map[0]: # if the first offset isn't 0, this map is wrong
            raise ValueError('initial map offset != 0')

        if map[-1] > textlen * 4: # if the max offset is 4x the text length
            # or more, the offsets cannot be right - none of the encodings
            # leads to more than 4x as many bytes as characters, so the last
            # offset must be lower than that value
            raise ValueError('map offsets too large')

        if not all(map[i - 1] < map[i] for i in range(1, textlen)):
            # all offsets must be consecutive, otherwise the map is wrong
            raise ValueError('map offsets not consecutive')

        return map

    def __contains__(self, tag) -> bool:
        # Check if this *tag* is annotated on the text.
        if self._keys and isinstance(tag, tuple) and len(tag) == 3:
            try:
                return tag in self._keys[tag[0]][tag[1]]
            except (KeyError, TypeError):
                pass

        return False

    def __delitem__(self, idx):
        # Delete all tags at *idx* in text (optionally, a slice, too).
        # If the slice step evaluates to ``True``, only tags that are
        # completely contained in the slice are deleted.
        tags = self.__getitemHelper(idx)
        self.remove(tags)

    def __eq__(self, other) -> bool:
        # Compare two text instances at the level of text and tags.
        # Note: The two texts may differ in their attributes.
        # To ensure text1 **is** text2, use `is`, not ``==``.
        if isinstance(other, Text):
            if self._TEXT == other._TEXT:
                if self._keys == other._keys:
                    return True

        return False

    def __iter__(self) -> iter:
        # Iterate over all tags, yielding them with their attributes.
        for tag in self.__iterHelper():
            yield tag, self.attributes.get(tag, None)

    def __iterHelper(self) -> iter:
        # Iterate over all tags, yielding them in offset order.
        for tree in self._offsets.values():
            for tags in tree.values():
                for tag in tags:
                    yield tag

    def __getitem__(self, idx:int) -> list:
        # Get all tags at a character position in text; optionally, a slice.
        # Note: The list is always ordered by offsets.
        # If the slice step evaluates to ``True``, only tags that are
        # completely contained in the slice are fetched.
        return list(self.__getitemHelper(idx))

    def __getitemHelper(self, idx):
        begin, end = 0, len(self)

        if isinstance(idx, slice):
            start, stop, inclusive = self.__unslice(idx)
            if inclusive: begin, end = start, stop
        else:
            if idx < 0: idx += end
            start, stop = idx, idx + 1

        tags = list()

        for tree in self._offsets.valueslice(begin, stop):
            for tagset in tree.valueslice(-end, -start):
                    tags.extend(tagset)

        return tags

    def __len__(self) -> int:
        # The number of characters in the list, ie., counting surrogate pairs
        # in narrow Python builds as one.
        return len(self._FIX)

    def __repr__(self) -> str:
#        return repr(self._TEXT)
        return '<{} {}@{}>'.format(self.__class__.__name__,
                                   id(self), self.base64digest)

    @staticmethod
    def __remove(container:dict, subset:set, key, subkey):
        # Clean up any containers in _keys and _offsets that have been emptied.
        if not subset:
            del container[key][subkey]

            if not container[key]:
                del container[key]

    def __reversed__(self):
        # Iterate over all tags, yielding them in a special reverse order.
        for tag in sorted(self.tags,
                          key=lambda tag: (-tag.offsets[-1], tag.offsets[0])):
            yield tag, self.attributes.get(tag, None)

    def __setitem__(self, key, value):
        # Set a tag on a character, span, or offsets tuple:
        # text[10] = 'ns:key'
        # text[10:20] = 'ns:key'
        # text[10:20] = 'ns:key', {'attr': 'value'}
        # text[(10,15,18,20)] = 'ns:key'
        # Note: the key may contain additional colon characters.
        # Slice step values are ignored.
        if isinstance(key, slice):
            start, stop, _ = self.__unslice(key)
            offsets = (start, stop)
        elif isinstance(key, tuple):
            offsets = key
        else:
            offsets = (int(key),)

        if isinstance(value, tuple):
            value, attributes = value[0], value[1]
        else:
            attributes = None

        ns, tag_id = value.split(':', 1)
        if __debug__: Text._checkOffsets(offsets, len(self))

        try:
            node = self._keys[ns]
        except KeyError:
            node = self._keys[ns] = dict()

        try:
            leaf = node[tag_id]
        except KeyError:
            leaf = node[tag_id] = set()

        tag = Text.Tag(ns, tag_id, offsets)
        if attributes: self.attributes[tag] = dict(attributes)
        if tag not in leaf: self.__add(tag, leaf)

    def __str__(self) -> str:
        # The underlying string of this text.
        return self._TEXT

    def __unslice(self, s):
        # Decompose a slice into start, stop, step.
        l = len(self)

        if not s.start: start = 0
        elif s.start < 0: start = l + s.start
        else: start = s.start

        if start < 0: start = 0

        if s.stop is None: stop = l
        elif s.stop < 0: stop = l + s.stop
        else: stop = s.stop

        if stop > l: stop = l

        return start, stop, s.step

    # Tag Properties and Methods

    @property
    def tags(self) -> iter:
        """
        An iterator over the list of (unique) :class:`.Text.Tag`\ s annotated
        on this text, ordered by their offsets.

        This is nearly the same as ``iter(text)``, except that only the tags
        are returned instead of ``(tag, attributes)`` tuples.

        By setting this property, the annotations on this text are all erased
        and replaced with the list or dictionary of tags -- an iterable of
        :class:`.Text.Tag`\ -like tuples, possibly a dictionary with tag tuples
        as keys and attribute dictionaries as values; any ``None`` (attribute)
        value is ignored. Setting the tags can raise the same errors as
        :meth:`.add`.
        """
        return self.__iterHelper()

    @tags.setter
    def tags(self, tags:iter):
        self._keys = dict()
        self._offsets = RBTree()
        self.attributes = dict()
        self.add(tags)

    @property
    def offsets(self) -> dict:
        """
        Get **a fresh copy of** a dictionary of (unique) :class:`.Text.Tag`\ s
        grouped by their first offset, then last offset value::

            {
                1: {
                    4: [
                        Tag(ns='nsX', id='idA', offsets=(1,2,3,4)), ...
                    ], ...
                },
                2: {
                    2: [
                        Tag(ns='nsY', id='idB', offsets=(2,)), ...
                    ], ...
                }, ...
            }
        """
        return { start: { -stop: list(tags) for stop, tags in tree.items() }
                 for start, tree in self._offsets.items() }

    @property
    def tagtree(self) -> dict:
        """
        Get **a fresh copy of** the (unique) :class:`.Text.Tag`\ s annotated
        on this text, grouped into a dictionary tree::

            {
                'nsX' : {
                    'idY': [
                        Tag(ns='nsX', id='idY', offsets=(1,2,3,4)),
                        ...
                    ], ...
                }, ...
            }

        The tags in the list are guaranteed to be unique, but are not ordered.
        """
        return { ns: { key: list(tags) for key, tags in node.items() }
                 for ns, node in self._keys.items() }

    def add(self, tags:iter):
        """
        Add several tags at once.

        Note that this has a far better insert performance than, for example::

            for offsets, attributes in some_iterable:
                text[offsets] = 'ns:id', attributes

        :param tags: An iterable of tags. If *tags* is a dictionary, the keys
            should be the tags, the values a dictionary of the tag's
            attributes; any ``None`` (attribute) value is ignored. An existing
            attribute dictionary for a tag is replaced.
        :raise TypeError: If the tag is not a tuple of three elements with the
            last element another tuple (of offsets) itself. If *tags* is a
            dictionary, but any value that is not ``None`` cannot be iterated.
        :raise ValueError: If a tag's offsets are malformed, illegal or
            unordered. If *tags* is a dictionary, but any iterable value can
            not be coerced to a dictionary.
        """
        last_ns, last_id, last_node, last_leaf = None, None, None, None
        textlen = len(self)

        if isinstance(tags, dict):
            for tag, attr in tags.items():
                if attr is not None:
                    self.attributes[tag] = dict(attr)

        for tag in sorted(tags):
            tag = Text.Tag(*tag)
            if __debug__: Text._checkOffsets(tag.offsets, textlen)

            if tag.ns != last_ns:
                last_ns = tag.ns
                last_node = self._keys.setdefault(last_ns, dict())

            if tag.id != last_id:
                last_id = tag.id
                last_leaf = last_node.setdefault(last_id, set())

            if tag in last_leaf: continue
            self.__add(tag, last_leaf)

    def get(self, namespace:str, key:str=None) -> list:
        """
        Get a list of all tags in a given *namespace* [and *key*] in no
        particular order, but grouped keys (if *key* is ``None``).

        :param namespace: The namespace to use.
        :param key: The key to use or all for the *namespace* if ``None``.
        :raise KeyError: If the *namespace* [or *key*] does not exist.
        """
        if key is None:
            tags = list()

            for leaf in self._keys[namespace].values():
                tags.extend(leaf)
        else:
            tags = list(self._keys[namespace][key])

        return tags

    def remove(self, tags:iter):
        """
        Remove several tags at once.

        :param tags: An iterable of tags.
        :raise KeyError: If any tag's namespace or ID do not exist.
        :raise ValueError: If any tag does not exist in that namespace and ID.
        """
        last_ns, last_id, last_node, last_leaf = None, None, None, None

        for tag in sorted(tags):
            tag = Text.Tag(*tag)

            if tag.ns != last_ns:
                last_ns = tag.ns
                last_node = self._keys[last_ns]

            if tag.id != last_id:
                last_id = tag.id
                last_leaf = last_node[last_id]

            start, stop = tag.offsets[0], tag.offsets[-1]
            starts = self._offsets[start][-stop]
            last_leaf.remove(tag)
            starts.remove(tag)
            Text.__remove(self._keys, last_leaf, last_ns, last_id)
            Text.__remove(self._offsets, starts, start, -stop)

    def update(self, other):
        """
        Update this instance with tags and attributes from another `Text`.

        Existing attribute dictionaries are updated, ie., if they have the
        same keys, such attributes are overwritten.

        :param other: A `Text` instance.
        :raise TypeError: If *other* is not a `Text` instance.
        :raise ValueError: If the annotated strings do not match.
        """
        if not isinstance(other, Text):
            raise TypeError('can only update from other Text objects')

        if self.digest != other.digest:
            raise ValueError('texts mismatch')

        self.add(other.tags)

        for tag, attrs in other.attributes.items():
            if tag in self.attributes:
                self.attributes[tag].update(attrs)
            else:
                self.attributes[tag] = dict(attrs)

    @staticmethod
    def _checkOffsets(offsets:tuple, textlen:int):
        """
        Ensure the offsets are conforming or raise exceptions if not.

        Raise a :exc:`ValueError` if the length of the offsets is not a
        multiple of 2 and larger than 2 (aka. "malformed"), the first offset
        isn't ``>= 0``, the last offset isn't ``<= textlen`` (aka. "illegal"),
        or the offsets are not consecutive (aka. "unordered").
        """
        len_offsets = len(offsets)

        if len_offsets < 1 or (len_offsets != 1 and len_offsets % 2):
            raise ValueError('malformed offsets: {}'.format(offsets))

        if offsets[0] < 0 or offsets[-1] > textlen:
            raise ValueError('illegal offsets: {}'.format(offsets))

        if len_offsets > 1 and not all(offsets[i-1] < offsets[i] for i in
                                       range(1, len(offsets))):
            raise ValueError('unordered offsets: {}'.format(offsets))

    # Byte Offset Maps

    @property
    def utf8(self) -> tuple:
        """
        A tuple of byte-offsets of each character in UTF-8 encoding
        (read-only).
        """
        return self._utf('_utf8')

    def _utf8(self):
        offset = 0

        for c in self.iter():
            yield offset
            o = ord(c)
            if   o < 0x80: offset += 1
            elif o < 0x800: offset += 2
            elif o < 0x1000: offset += 3
            else: offset += 4

    @property
    def utf16(self) -> tuple:
        """
        A tuple of byte-offsets of each character in UTF-16 encoding
        (read-only).
        """
        return self._utf('_utf16')

    def _utf16(self):
        offset = 0

        for c in self.iter():
            yield offset
            if ord(c) > 0xFFFF: offset += 4
            else: offset += 2

    @property
    def utf32(self) -> tuple:
        """
        A tuple of byte-offsets of each character in UTF-32 encoding
        (read-only).
        """
        return self._utf('_utf32')

    def _utf32(self):
        for i in range(len(self)):
            yield i * 4

    def _utf(self, name:str) -> tuple:
        if self._maps.get(name) is not None:
            m = self._maps[name]
        else:
            m = tuple(getattr(self, name)())
            self._maps[name] = m

        return m

    # String methods

    @property
    def string(self) -> str:
        """
        This is a special property that should be used when taking **slices**
        or retrieving individual characters of the text's string.

        This property is provided to circumvent the problem of wrong offset
        counts when using narrow Python builds where Unicode is based on
        UTF-16 characters, and surrogate pairs get sadly counted as length 2::

            >>> from libfnl.nlp.text import Text
            >>> text = Text('abc\U0010ABCDabc')
            >>> text.string[4]
            '\U0010ABCD'
            >>> text.string[3:5]
            'c\U0010ABCDa'

        .. note::

            If you wish to access the entire string, use ``s = str(text)``,
            don't do ``s = text.string`` or something similar. On narrow
            Python builds you might not be receiving a string type, but a
            special class to fix the offset behaviour. You could use
            ``s = str(text.string)`` to ensure this is always a string, but
            this, in turn, would be very inefficient on narrow builds -- just
            stick with ``str(text)``...
        """
        return self._FIX

    def iter(self) -> iter:
        """
        Iterate over the characters in the string.

        Can yield "characters" of length 2 if they are from the Unicode SMP
        (ie., surrogate pairs) on narrow Python builds.
        """
        return iter(self._FIX)

    def encode(self, encoding:str='utf-8', errors:str='strict') -> bytes:
        """
        Return the encoded text string.
        """
        return self._TEXT.encode(encoding, errors)

    # Text identity

    @property
    def base64digest(self) -> str:
        """
        The base64-encoded ASCII string of the :attr:`.digest` without the
        redundant ``=`` padding characters (read-only).

        Instead of regular base64 encoding, the characters ``+`` and ``/``
        are mapped to a **CouchDB-URL**\ -safe versions via :func:`.b64encode`.
        """
        return b64encode(self.digest)[:-2].decode('ASCII')

    @property
    def digest(self) -> bytes:
        """
        The hash digest of the UTF-8 encoded text (read-only).
        """
        if not self._digest:
            self._digest = hashlib.md5(self.encode()).digest()

        return self._digest

    # Text serialization

    @classmethod
    def fromJson(cls, json:dict):
        """
        Create a `Text` instance, deserialized from a JSON dictionary with
        the same keys mentioned in :meth:`.toJson`.

        Raises any exception that the `Text` constructor might.

        :raise ValueError: If the JSON dictionary has no text or checksum,
            or if the checksum match test fails for any possible reason.
        """
        tags = json.get('tags', [])

        if tags:
            tags = { Text.Tag(tag[0], tag[1], tuple(tag[2])): attr
                     for tag, attr in tags }

        try:
            text = cls(json['text'], tags,
                       **json.get('maps', {}))
        except KeyError:
            raise ValueError('no text in this JSON dictionary')

        try:
            hash_type, hex = json['checksum'][0].lower(), json['checksum'][1]
        except KeyError:
            raise ValueError('no checksum in this JSON dictionary')
        except IndexError:
            raise ValueError('checksum list malformed')
        except TypeError:
            raise ValueError('checksum list malformed')

        digest = bytes(int(hex[i:i+2], 16) for i in range(0, len(hex), 2))

        if hash_type == 'md5':
            if text.digest != digest:
                raise ValueError('text and checksum mismatch')
        else:
            try:
                hasher = getattr(hashlib, hash_type)
            except NameError:
                raise ValueError('hash type "{}" unknown'.format(hash_type))

            if hasher(str(text).encode()).digest() != digest:
                raise ValueError('text and checksum mismatch')

        return text

    def toJson(self) -> dict:
        """
        Serialize the text to a dictionary that can be encoded as a JSON
        string.

        Sets the following keys on the dictionary:

        * **text**: ``"<the text>"``
        * **checksum**: ``( "md5", "<the checksum as hex-string>" )``
        * **maps**: ``{ "utf<X>": [<byte-offsets>] }``
        * **tags**: ``[ ( ("<ns>", "<key>", (<offsets>)), <attributes dict or None> ), ... ]``

        Note that ``tags`` are only set if present.
        """
        json = { 'text': self._TEXT,
                 'checksum': ('md5',
                              ''.join('{:x}'.format(b) for b in self.digest)),
                 'maps': {
                     'utf8': self.utf8,
                     'utf16': self.utf16,
                     'utf32': self.utf32
                 }
        }
        if self._keys: json['tags'] = [t for t in iter(self)]
        return json
