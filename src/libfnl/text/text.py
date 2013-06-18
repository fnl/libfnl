"""
.. py:module:: text
   :synopsis: Data types to annotate text.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from binascii import b2a_base64
import hashlib
from collections import defaultdict, namedtuple
from itertools import chain

from libfnl import PyUTF16

class Text:
    """
    Annotate strings with character-offset based tags.

    Tags are assumed to be tuples of three values::

        tag = ( 'namespace', 'identifier', <offsets> )

    Where the last, offset, is a tuple of 1 or 2n integers with n > 0::

        offset = ( <start>, ... <[stop]> )

    Using (whole) character offsets for strings with Supplementary Multilingual
    Plane (SMP) codepoints works even on narrow Python builds, via a special
    fix for strings containing surrogate pairs.
    """

    class StringFix(str):
        # A fix for offset problems in strings containing SMP characters on
        # narrow Python builds.

        def __init__(self, value:str='', *_):
            str.__init__(self)
            # __fixed is a tuple of codepoint-grouped strings where Surrogate
            # Pairs are represented as a single tuple elements to ensure
            # the same coordinates of string offsets on both Python builds.
            self.__fixed = tuple(Text.StringFix.__chars(value))
            self.__len = len(self.__fixed)

        # "fixed" methods

        @staticmethod
        def __chars(text:str) -> iter:
            # For character count problems with narrow Python builds: an
            # iterator of real characters, joining surrogate pairs as one.
            char_iter = iter(text)

            while True:
                c = next(char_iter)

                if '\ud800' <= c < '\udc00':
                    c += next(char_iter)

                    if not '\udc00' <= c[1] < '\ue000':
                        raise UnicodeError('low surrogate character missing')

                yield c

        def __getitem__(self, idx) -> str:
            return ''.join(self.__fixed[idx])

        def __iter__(self) -> iter:
            return iter(self.__fixed)

        def __reversed__(self) -> iter:
            return reversed(self.__fixed)

        def __len__(self) -> int:
            return self.__len

    Key = lambda tag: (tag[2][0], -tag[2][-1], tag[2], tag[0], tag[1])
    """
    Ordering of tags in forward offset order (lowest start, highest stop,
    other offsets, namespace, ID).
    """

    ReverseKey = lambda tag: (-tag[2][-1], tag[2][0], tag[2], tag[0], tag[1])
    """
    Sort key of tags in reverse offset order (highest stop, lowest start,
    other offsets, namespace, ID).

    Not used anywhere, but provided for convenience, especially for
    :meth:`.Text.tags`.

    .. note::

        The reversed offset order is not the same as reversing the list
        offset-ordered tags -- ie.::

            reversed(sorted(tags, key=Text.Key)) != sorted(tags, key=Text.ReverseKey)
    """

    _Token = namedtuple('_Token', 'id text attributes')

    def __init__(self, text, tags:iter=None, **utf_maps):
        """
        Constructing a `Text` instance might raise any exception that
        :meth:`.add` might raise.

        :param text: The string to annotate or another `Text` instance to copy.
        :param tags: The tags holding the annotations; Ignored if *text* is a
            `Text` instance. See :meth:`.add` for more information about the
            structure of *tags*.
        :param utf_maps: Provide pre-calculated maps for UTF-8 and UTF-16
            encodings. Normally, this parameter is only used when
            deserializing `Text` instances. Maps are dropped silently if they
            are incorrect. UTF-32 maps are ignored, because they are trivial:
            ``bytes := characters * 4 + 4`` where ``+ 4`` is the BOM (Byte
            Order Mark) length.
        :raise TypeError: If *text* is neither a string or a `Text` instance.
        """
        if isinstance(text, Text): # deep copy from that instance
            self._FIX = text._FIX
            self._TEXT = text._TEXT
            self.attributes = { ns: { tag: dict(a)
                                      for tag, a in attrs.items() }
                                for ns, attrs in text.attributes.items() }
            self._digest = text._digest
            self._maps = dict(text._maps)
            self._tags = { ns: list(tags)
                           for ns, tags in text._tags.items() }
        elif isinstance(text, str): # create a new instance
            self._TEXT = text # NB: immuteable!
            self._digest = None
            self._maps = dict()
            self._tags = dict()
            self.attributes = dict()

            if PyUTF16:
                self._FIX = Text.StringFix(text)
                # But only use this fix if there are SMP codepoints!
                if len(self._FIX) == len(self._TEXT): self._FIX = self._TEXT
            else:
                self._FIX = self._TEXT

            if tags: self.add(tags)

            if utf_maps:
                for name in utf_maps:
                    normal = name.strip().lower().replace('-', '')

                    if normal in ('utf8', 'utf16'):
                        try:
                            self._maps['_' + normal] = \
                                self.__checkMap(utf_maps[name])
                        except TypeError:
                            pass # silently drop bad maps
                        except ValueError:
                            pass # silently drop bad maps
        else:
            raise TypeError('text not a Text or string')

    # Special and Private Methods

    def __checkMap(self, map:iter) -> tuple:
        map = tuple(int(i) for i in map)
        maplen = len(self.string) + 1

        if maplen != len(map): # must be as long as the text has characters +1
            raise ValueError('UTF map len {} != {}'.format(len(map), maplen))

        # BOM sizes: 2 -> UTF-16, 3 -> UTF-8, 4 -> UTF-32
        if map[0] not in (0, 2, 3, 4): # if not 0 or BOM size this map is wrong
            raise ValueError('illegal initial UTF map offset')

        if maplen == 1: # if the text has no characters, we are fine already
            return map

        if map[-1] > (maplen - 1) * 4 + map[0]: # if the max offset is more
            # than 4x the text len, the offsets cannot be right - no known
            # encoding leads to more than 4x as many bytes as characters, so
            # the last offset must be lower than that value
            raise ValueError('UTF map offsets too large')

        if map[-1] < (maplen - 1) + map[0]: # if the min offset is less than
            # 1x the text len, the offsets cannot be right - no known
            # encoding leads to less bytes than characters, so the last
            # offset must be at least that value
            raise ValueError('UTF map offsets too small')

        if not all(map[i - 1] < map[i] for i in range(1, maplen)):
            # all offsets must be consecutive, otherwise the map is wrong
            raise ValueError('UTF map offsets not consecutive')

        return map

    def __contains__(self, tag) -> bool:
        # Check if this *tag* is annotated on the text.
        if self._tags and isinstance(tag, tuple) and len(tag):
            try:
                return tag in self._tags[tag[0]]
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
                if self._tags == other._tags:
                    return True

        return False

    def __iter__(self) -> iter:
        # Iterate over all tags, yielding them without their attributes.
        return chain(*self._tags.values())

    def __getitem__(self, idx:int) -> iter:
        # Get all tags at a character position in text; optionally, a slice.
        # Note: The list is always ordered by offsets.
        # If the slice step evaluates to ``True``, only tags that are
        # completely contained in the slice are fetched.
        return sorted(self.__getitemHelper(idx), key=Text.Key)

    def __getitemHelper(self, idx):
        begin, end = 0, len(self.string)
        inclusive = False

        if isinstance(idx, slice):
            start, stop, inclusive = self.__unslice(idx)
        else:
            if idx < 0: idx += end
            start, stop = idx, idx + 1

        if inclusive:
            in_range = lambda t: t[2][0] >= start and t[2][-1] <= stop
        else:
            in_range = lambda t: t[2][0] < stop and t[2][-1] > start

        for ns, taglist in self._tags.items():
            for tag in filter(in_range, taglist):
                yield tag

    def __len__(self) -> int:
        # The number of tags on this text.
        return sum(len(tags) for tags in self._tags.values())

    def __repr__(self) -> str:
        return '<{} {}@{}>'.format(Text.__name__, id(self), self.base64digest)

    def __reversed__(self) -> iter:
        # Ensure using reversed() does not produce unexpected results.
        return iter(self)

    def __setitem__(self, key, value):
        # Set a tag on a character, span, or offsets tuple:
        # text[10] = 'ns', 'id'
        # text[10:20] = 'ns', 'id'
        # text[10:20] = 'ns', 'id', {'attr': 'value'}
        # text[(10,15,18,20)] = 'ns', 'id'
        # Note: the key may contain additional colon characters.
        # Slice step values are ignored.
        # Very inefficient way to add tags!!!
        if isinstance(key, slice):
            start, stop, _ = self.__unslice(key)
            offsets = (start, stop)
        elif isinstance(key, tuple):
            offsets = key
        else:
            offsets = (int(key),)

        if len(value) == 3:
            ns, id, attributes = value[0], value[1], dict(value[2])
        else:
            ns, id = value
            attributes = None

        try:
            tags = self._tags[ns]
        except KeyError:
            tags = list()

        tag = (ns, id, offsets)

        if tag not in tags:
            tags.append(tag)
            self._tags[ns] = sorted(tags, key=Text.Key)

        if attributes:
            attrs = self.attributes.setdefault(ns, dict())
            Text.__update(attrs.setdefault(tag, dict()), attributes)

    def __str__(self) -> str:
        # The underlying string of this text.
        return self._TEXT

    @staticmethod
    def __update(attrs, new):
        # Update an exisiting attribute dictionary, updating any dictionary
        # values, extending any list values, or otherwise adding/replacing
        # the values.
        for name, value in new.items():
            if name in attrs:
                target = attrs[name]

                if isinstance(target, dict) and \
                   isinstance(value, dict):
                    target.update(value)
                elif isinstance(target, list) and \
                     isinstance(value, (list, tuple)):
                    target.extend(value)
                else: # "unmutable" JSON target
                    attrs[name] = value
            else:
                attrs[name] = value

    def __unslice(self, s):
        # Decompose a slice into start, stop, step.
        l = len(self.string)

        if not s.start: start = 0
        elif s.start < 0: start = l + s.start
        else: start = s.start

        if start < 0: start = 0

        if s.stop is None: stop = l
        elif s.stop < 0: stop = l + s.stop
        else: stop = s.stop

        if stop > l: stop = l

        return start, stop, s.step

    # Tag Methods

    def add(self, tags:iter, namespace:str=None):
        """
        Add several tags at once, updating any existing ones. The *tags* can
        be any iterable with a structure as the iterable returned by
        :meth:`.Text.get`.

        Existing attribute dictionaries are updated. If the new attribute names
        are not present, the new values are added. If the name exists, the
        value is replaced, or ``update()``\ d if the value is a dictionary
        and ``extend()``\ ed if it is a list.
        
        If tags are added to an existing namespace, the tags are ordered after
        appending them. Tags for a novel namespace are **not** ordered because
        tag lists are assumed to be created in order anyways, so by default no
        ordering takes place when an entire new namespace is added. If the
        to be added new namespace for some reason is not ordered it is
        recommended to order them prior to adding.

        :param tags: Any iterable of tag, attributes tuples::

                ( ( "namespace", "id", ( <offset>, ... ) ),
                  { "name": <value>, ... }                  )

            If the tag has no attributes, attributes can be ``None`` instead of
            a dictionary. The values of an attribute dictionary should be
            JSON-serializable and the attribute names therefore plain strings.
        :param namespace: If given, all tags are treated as being for that
            namespace only, which improves the time needed to add tags for
            just one namespace. None the less, the namespace element of the
            *tags* has to be present in every tag, but no check is made to
            ensure no different (ie., wrong) namespace is set in any of the
            *tags*.
        :raise TypeError: If any tag is not a sequence of items or not hashable
            or if an attribute is not dictionary-like.
        :raise ValueError: If a tag seems like a sequence of three items, but
            is not - eg., ``('tag', 'id')``. If an attribute seems dictionary
            like, but turns out to be not - eg., ``[('name', 'value',
            'illegal')]``. Finally, a `ValueError` occurs if only tags but no
            attributes are added: ie., using ``[tag1, tag2, tag3]`` instead of
            ``[(tag1, None), (tag2, None), (tag3, None)]``.
        """
        if namespace:
            self._add(namespace, tags)
        else:
            groups = defaultdict(list)

            for tag_attrs in tags:
                groups[tag_attrs[0][0]].append(tag_attrs)

            for ns, ns_tags in groups.items():
                self._add(ns, ns_tags)

    def addFromDict(self, tags:dict):
        """
        Add tags from a dictionary as the one produced by :meth:`.tagsAsDict`.

        :param tags: A dictionary of tags.
        """
        for ns, ns_dict in tags.items():
            tag_attrs = []

            for id, off_dict in ns_dict.items():
                for off, attrs in off_dict.items():
                    offsets = tuple(map(int, off.split('.')))
                    tag_attrs.append(((ns, id, offsets), attrs))

            self._add(ns, sorted(tag_attrs, key=lambda ta: Text.Key(ta[0])))

    def _add(self, namespace:str, tags:iter):
        # Add new or update existing tags and attributes in *namespace* with
        # additional *tags* and their attributes.
        if namespace in self._tags:
            existing_tags = frozenset(self._tags[namespace])
            existing_attrs = self.attributes[namespace]
            new_tags = list()

            for tag, attrs in tags:
                if tag not in existing_tags:
                    new_tags.append(tag)

                if attrs:
                    if tag in existing_attrs:
                        Text.__update(existing_attrs[tag], dict(attrs))
                    else:
                        existing_attrs[tag] = dict(attrs)

            if new_tags:
                new_tags.extend(existing_tags)
                self._tags[namespace] = sorted(new_tags, key=Text.Key)
        else:
            taglist = self._tags[namespace] = list()
            attdict = self.attributes[namespace] = dict()

            for tag, attrs in tags:
                taglist.append(tag)
                if attrs: attdict[tag] = dict(attrs)

    def get(self, namespace:str=None) -> iter:
        """
        An iterator over the list of tags and attributes annotated on this
        text, optionally only for one namespace.

        No ordering of the tags is guaranteed, although tags for one
        *namespace* normally should be in correct order -- which only would
        not be the case if tags had been added unordered. If no *namespace* is
        specified, tags are grouped by namespaces (in alphanumerical order of
        namespaces).

        :param namespace: Only fetch the tags for the given namespace (instead
            of all tags).
        :return: An iterator over ``(tag, attrs)`` pairs where ``attrs`` is
            the dictionary of attributes or ``None`` if the tag has no
            attributes.
        :raise KeyError: If the *namespace* does not exist.
        :raise TypeError: If any tag previously added was malformed.
        """
        if namespace:
            return self._get(namespace)
        else:
            return chain(*(self._get(ns) for ns in sorted(self.namespaces)))

    def _get(self, ns:str) -> iter:
        attrs = self.attributes[ns]

        for t in self._tags[ns]:
            yield t, attrs.get(t)

    @property
    def namespaces(self) -> iter:
        """
        An iterator over all namespace strings of all tags.
        """
        return self._tags.keys()

    def remove(self, tags:iter, namespace:str=None):
        """
        Remove several *tags* (without attributes) or an entire *namespace* at
        once.

        :param tags: An iterable of tags or ``None`` to remove an entire
            *namespace*.
        :param namespace: The namespace to remove tags from (avoids grouping
            the *tags* by namespaces first, but all tags must be from the
            same namespace). If *tags* is ``None``, the entire namespace is
            removed.
        :raise KeyError: If any tag's namespace does not exist.
        :raise ValueError: If any tag does not exist.
        """
        if tags is None:
            del self._tags[namespace]
            if namespace in self.attributes: del self.attributes[namespace]
        elif namespace:
            self._remove(namespace, tags)
        else:
            groups = defaultdict(list)

            for t in tags:
                groups[t[0]].append(t)

            for ns, ns_tags in groups.items():
                self._remove(ns, ns_tags)

    def _remove(self, namespace:str, tags:list):
        target = self._tags[namespace]
        attrs = self.attributes[namespace]

        for t in tags:
            target.remove(t)
            if t in attrs: del attrs[t]

        if not self._tags[namespace]:
            del self._tags[namespace]
            del self.attributes[namespace]

    def tags(self, key=Key) -> list:
        """
        Return a list of **all** tags (without attributes), sorted by *key*.

        :param key: By default, uses :obj:`.Text.Key` order.
        """
        return sorted(self, key=key)

    def tagsAsDict(self) -> dict:
        """
        Return **all** tags and attributes as a dictionary that can be used to
        serialize the annotations.

        An example:

        >>> from libfnl.text.text import Text
        >>> text = Text('example')
        >>> text[2] = 'ns1', 'id1', {'a': 'v'}
        >>> text[(1,3,4,6)] = 'ns1', 'id1'
        >>> text.tagsAsDict()
        {'ns1': {'id1': {'1.3.4.6': None, '2': {'a': 'v'}}}}

        :return: A `dict` of all tags and attributes, grouped by namespace,
            ID, (string) offsets (offset integers, joined with dots (``.``)).
        """
        tags = dict()

        for ns in self.namespaces:
            attributes = self.attributes[ns]
            ns_dict = tags[ns] = dict()

            for tag in self._tags[ns]:
                id_dict = ns_dict.setdefault(tag[1], {})
                offsets = '.'.join(map(str, tag[2]))
                attrs = attributes.get(tag)

                if attrs:
                    assert all(map(lambda key: isinstance(key, str), attrs)), \
                        'key not a string: {}'.format(list(attrs.keys()))
                
                id_dict[offsets] = attrs

        return tags

    def update(self, text):
        """
        Update with tags and attributes from another `Text` instance that has
        the same underlying string.

        If you really need to update from another text with a different digest
        and underlying string, you could simply use::

            text.add(other.get())

        .. seealso:: :meth:`.Text.add`

        :param text: A `Text` instance.
        :raise ValueError: If *text* is a `Text` instance, but the digests do
            not match.
        :raise TypeError: If *text* is not a `Text` instance.
        """
        try:
            if self.digest != text.digest:
                raise ValueError('the two texts mismatch')
        except AttributeError:
            raise TypeError('{} not a Text instance'.format(repr(text)))

        for ns in text.namespaces:
            self._add(ns, text.get(ns))

    # String methods

    @property
    def base64digest(self) -> str:
        """
        The base64-encoded ASCII string of the :attr:`.digest` without the
        redundant ``=`` padding characters (read-only).
        """
        return b2a_base64(self.digest)[:-3].decode('ASCII')

    @property
    def digest(self) -> bytes:
        """
        The MD5 digest of the UTF-8 encoded text (read-only).
        """
        if not self._digest:
            self._digest = hashlib.md5(self.encode()).digest()

        return self._digest

    def encode(self, encoding:str='utf-8', errors:str='strict') -> bytes:
        """
        Return the encoded text string.
        """
        return self._TEXT.encode(encoding, errors)

    def iter(self, namespace:str) -> iter:
        """
        Iterate over the string tokens of all tags in a given *namespace*.

        Tokens are named tuples to represent token strings for a given tag.
        The tuple consists of an *id* string (the tag ID), *text* (the string),
        and an *attributes* dictionary (as set on the tag; possibly ``None``).

        :param namespace: The namespace to iterate over
        :return: Named tuples of ``(id, text, attributes)`` values.
        """
        attributes = self.attributes[namespace]

        for t in self._tags[namespace]:
            off = t[2]

            if len(off) > 2:
                text = ''.join(self._FIX[off[i]:off[i+1]]
                               for i in range(0, len(off), 2))
            else:
                text = self._FIX[off[0]:off[-1]]

            yield Text._Token(t[1], text, attributes.get(t))

    @property
    def string(self) -> str:
        """
        This is a special (read-only) property that should be used when taking
        **slices** or retrieving individual characters of the text's string.

        This property is provided to circumvent the problem of wrong offset
        counts when using narrow Python builds where Unicode is based on
        UTF-16 characters, and Surrogate Pairs normally are counted as length
        2::

        .. doctest::

            >>> from libfnl.text.text import Text
            >>> text = Text('abc\U0010ABCDabc')
            >>> text.string[3] # SP \udbea\udfcd of length 2 on narrow builds
            '\\U0010abcd'
            >>> text.string[2:5]
            'c\\U0010abcda'
            >>> for char in text.string:
            ...     print(char)
            a
            b
            c
            \U0010ABCD
            a
            b
            c
            >>> len(text.string)
            7
            >>> text.string
            'abc\\U0010abcdabc'
            >>> isinstance(text.string, str)
            True

        .. note::

            If you wish to access the entire string, you can also just use
            ``str(text)``.
        """
        return self._FIX

    # Byte Offset Maps

    @property
    def utf8(self) -> tuple:
        """
        A tuple of byte-offsets of each character in UTF-8 encoding
        (read-only).

        The tuple is one element longer than the text characters, with the
        last element representing the total length of the encoded string.
        The first element starts at 0 bytes (the possible, but unusual 3 byte
        UTF-8 BOM should never be counted).
        """
        return self._utf('_utf8')

    def _utf8(self):
        offset = 0

        for c in self.string:
            yield offset
            o = ord(c)
            if   o < 0x80: offset += 1
            elif o < 0x800: offset += 2
            elif o < 0x1000: offset += 3
            else: offset += 4

        yield offset

    @property
    def utf16(self) -> tuple:
        """
        A tuple of byte-offsets of each character in UTF-16 encoding
        (read-only).

        The tuple is one element longer than the text characters, with the
        last element representing the total length of the encoded string.
        The first element starts at 2 bytes because of the 2 byte long Byte
        Order Mark (BOM) in UTF-16 strings before the first character byte.
        """
        return self._utf('_utf16')

    def _utf16(self):
        offset = 2 # 2 byte BOM

        for c in self.string:
            yield offset
            if ord(c) > 0xFFFF: offset += 4
            else: offset += 2

        yield offset

    def _utf(self, name:str) -> tuple:
        if self._maps.get(name) is not None:
            m = self._maps[name]
        else:
            m = tuple(getattr(self, name)())
            self._maps[name] = m

        return m

    # Text serialization

    @classmethod
    def fromJson(cls, json:dict):
        """
        Create a `Text` instance without annotations, deserialized from a JSON
        dictionary with the same keys as mentioned in :meth:`.toJson`.

        Raises any exception that the `Text` constructor might.

        :raise ValueError: If the JSON dictionary has no text or checksum,
            or if the checksum match test fails for any reason.
        """
        # Create the text instance:
        try:
            text = cls(json['text'], **json.get('maps', {}))
        except KeyError:
            raise ValueError('text not present in raw JSON')

        # Ensure the checksum is correct:
        try:
            hex = None
            checksum = { k.lower().replace('-', ''): v
                         for k, v in json['checksum'].items() }
            encoding = checksum['encoding'].lower().replace('-', '')
        except KeyError:
            raise ValueError('checksum in raw JSON missing or malformed')
        except AttributeError:
            raise ValueError('checksum in raw JSON malformed')

        if 'md5' in checksum:
            hex = checksum['md5']

            if encoding == 'utf8':
                text_digest = text.digest
            else:
                text_digest = hashlib.md5(str(text).encode(encoding)).digest()
        else:
            hash_function = None

            for hash_type in checksum:
                try:
                    hash_function = getattr(hashlib, hash_type)
                    hex = checksum[hash_type]
                except (NameError, AttributeError):
                    pass
                else:
                    break

            if hash_function is None:
                msg = 'no known hash types ({})'.format(
                    ', '.join(k for k in checksum.keys() if k != 'encoding')
                )
                raise ValueError(msg)

            text_digest = hash_function(str(text).encode(encoding)).digest()

        if text_digest != bytes(int(hex[i:i+2], 16)
                                for i in range(0, len(hex), 2)):
            raise ValueError('text and checksum mismatch')

        return text

    def toJson(self) -> dict:
        """
        Serialize the text to a dictionary that can be encoded as a JSON
        string.

        Sets the following keys on the dictionary:

        * text
        * checksum
        * maps
        """
        return {
            'text': self._TEXT,
             'checksum': {
                 'encoding': 'utf8',
                 'md5': ''.join('{:x}'.format(b) for b in self.digest)
             },
             'maps': {
                 'utf8': self.utf8,
                 'utf16': self.utf16
             }
        }
