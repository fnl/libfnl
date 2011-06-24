"""
.. py:module:: text
   :synopsis: Data types to annotate text.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
"""
from hashlib import sha256


class AnnotatedContent:
    """
    Abstract manager class for tagging content, implemented by both
    :class:`.Binary` and :class:`.Unicode`.
    """

    def __init__(self):
        if tags is None: tags = {}
        self._tags = tags
        self._sorted = {} # for each namespace, store the sorted stated of it

    def __len__(self):
        raise NotImplementedError("abstract")

    @property
    def tags(self) -> list([(tuple([int]), str, object)]):
        """
        Get a copy of the dictionary of tags.
        """
        return { ns: list(tag) for ns, tag in self._tags.items() }

    @tags.setter
    def tags(self, tags:dict):
        """
        Replace the entire tags dictionary. No checks are made!
        """
        self._tags = tags
        self._sorted = { ns: False for ns in tags }

    def addTag(self, namespace:str, offsets:tuple([int]), value:object):
        """
        Add a new tag.

        :param namespace: The namespace this tag belongs to.
        :param offsets: The position of this tag; either a single offset value
            for tags pointing to just one location in the content, or paired
            integers in increasing order indicating the offsets (start, end) of
            one or more spans (ie., each offset must be larger than its former).
        :param value: The value of the tag, eg., the PoS name or chunk type;
            Usually, a string, but it could also be dictionary, fe., with the
            following keys:
            ``{'id': some_id, 'annotator': uri, 'confidence': float}``.
        :raises AssertionError: If the key is malformed.
        """
        # try to fetch the namespace or create a new one
        if namespace in self._tags:
            tags = self._tags[namespace]
        else:
            tags = list()
            self._tags[namespace] = tags

        # assert all elements are given and not empty
        assert namespace, "namespace missing"
        assert offsets, "offsets missing"
        assert value, "value missing"

        # assertions that the offsets are well-formed
        assert offsets[0] >= 0 and offsets[-1] <= len(self), \
            "offsets {} invalid (max: {})".format(offsets, len(self))

        if len(offsets) > 1:
            assert len(offsets) % 2 == 0, \
                "odd number of offsets: {}".format(offsets)
            assert all(offsets[i-1] < offsets[i]
                       for i in range(1, len(offsets))), \
                "offsets {} not successive".format(offsets)

        # all ok, append the tag
        self._sorted[namespace] = False
        tags.append((tuple(offsets), value))

    def addTagUnsafe(self, namespace:str, offsets:tuple([int]), value:object):
        """
        Add a new tag, but without any checks. Use at your own discretion!

        :param namespace: The namespace this tag belongs to, a string.
        :param offsets: The position of this tag, a tuple.
        :param value: The value of the tag, a string or dictionary.
        """
        # try to fetch the namespace or create a new one
        if namespace in self._tags:
            tags = self._tags[namespace]
        else:
            tags = list()
            self._tags[namespace] = tags

        self._sorted[namespace] = False
        tags.append((offsets, value))

    def delNamespace(self, namespace:str):
        """
        Delete an entire *namespace* and all its tags.

        :raise KeyError: If the *namespace* doesn't exist.
        """
        del self._tags[namespace]
        del self._sorted[namespace]

    def delTag(self, namespace:str, offsets:tuple([int]), value:object):
        """
        Delete the tag in *namespace* with the given *offsets* and *value*.

        :raise KeyError: If the *namespace* doesn't exist.
        :raise ValueError: If that (*offsets*, *value*) tag doesn't exist.
        """
        self._tags[namespace].remove((offsets, value))
        # also clean up the namespace if empty
        if not self._tags[namespace]:
            del self._tags[namespace]
            del self._sorted[namespace]

    def getTags(self, namespace:str) -> [((int,), object)]:
        """
        Get a copied list of all ``(offsets, value)`` tags in *namespace*.
        """
        return list(self._tags[namespace])

    def iterNamespaces(self) -> iter([str]):
        """
        Return an iterator over the known namespaces.
        """
        return self._tags.keys()

    def iterValues(self, namespace:str, offsets:tuple([int])) -> iter([object]):
        """
        Get an iterator over all values of any tags in *namespace* that exactly
        match *offsets*.
        """
        # is this much used? could be made faster by divide & conquer
        # maybe a "get values at position" would be more useful?
        match_offsets = lambda ov: ov[0] == offsets
        return_value = lambda ov: ov[1]
        return map(return_value, filter(match_offsets, self._tags[namespace]))

    def sort(self, namespace:str=None):
        """
        Order the tags in place.

        The tags are sorted by the ``offsets``, then the ``value``.
        Offset sorting is in order of the offset's start (lowest first), end
        (last offset value, highest first), and then the rest of the offset
        values. If this isn't sufficient, they are ordered by the natural order
        of the ``value``.

        For example, the offsets (1,2,3,5), (1,3), (2,), and (1,2,4,5) will be
        ordered like this:

        #. (1,2,3,5)
        #. (1,2,4,5)
        #. (1,3)
        #. (2,)

        If the tags in a namespace have been sorted already and are unchanged,
        they are not ordered again.

        :param namespace: The *namespace* to sort or all if ``None``.
        :raise KeyError: If the *namespace* does not exist.
        """
        ns_iter = (namespace,) if namespace else self._tags.keys()
        sort_by_offset = lambda k: (k[0][0], k[0][-1] * -1, k[0], k[1])

        for ns in ns_iter:
            if self._sorted[ns]: continue
            self._tags[ns] = sorted(self._tags[ns], key=sort_by_offset)
            self._sorted[ns] = True

    def _mapTags(self, MapOffsets):
        # Return a new tag dictionary, mapping the offsets tuple by sending
        # them to MapOffsets and expecting a new tuple with the mapped offsets.
        # Used by the toUnicode() and toBinary() casting methods.
        realign = lambda tag: (MapOffsets(tag[0]), tag[1])
        return {
            ns: list(map(realign, self._tags[ns]))
            for ns in self.iterNamespaces()
        }


class Binary(bytes, AnnotatedContent):
    """
    A specialized `bytes` class for binary (ie., encoded) text
    and implementing :class:`.AnnotatedContent`.

    Contrary to regular `bytes` objects, it also stores the encoding of
    itself, plus the annotation tags.
    """

    def __new__(cls, *args):
        if isinstance(args[0], str):
            return super(Binary, cls).__new__(cls, *args)
        else:
            # get rid of the encoding argument to bytes...
            return super(Binary, cls).__new__(cls, args[0])


    def __init__(self, *args):
        """
        To instantiate a Binary, pass it the text as `bytes` and a `str`
        with the encoding of the text, or pass the text as `str`, again with
        a target encoding, and possibly the error parameter for the encoding
        operation. Ie., in the former case (via a `bytes` text) add the
        encoding as a parameter, in the latter case (via `str`) it is the
        same procedure as for a regular `bytes` object. See
        :func:`bytearray` for details about creating `bytes`.

        **To emphasize:** the second argument **must** be the encoding.
        """
        AnnotatedContent.__init__(self)
        self._digest = None
        self._encoding = args[1]
        self._str_alignment = dict()

    @property
    def encoding(self) -> str:
        """
        The encoding value (read-only).
        """
        return self._encoding

    @property
    def digest(self) -> bytes:
        """
        The SHA256 digest (ie., as `bytes`) of the content (read-only).
        """
        if self._digest is None:
            self._digest = sha256(self).digest()

        return self._digest
    
    @property
    def hexdigest(self) -> str:
        """
        The SHA256 hexdigest (ie., as `str`) of the content (read-only).
        """
        return "".join('%02x' % b for b in self.digest)

    def toUnicode(self, errors:str="strict") -> AnnotatedContent:
        """
        Return the :class:`.Unicode` view of this document, with
        any tag offsets mapped to the positions in the decoded Unicode.

        Contrary to the ``decode()`` method of `bytes`, the encoding argument
        is not needed.

        :raises UnicodeDecodeError: If any tag key is illegal.
        :return: :class:`.Unicode`
        """
        text = Unicode(self.decode(self._encoding, errors))

        if self._tags:
            map_offsets = lambda offsets: tuple( self._strpos(pos, errors)
                                                 for pos in offsets )
            text.tags = self._mapTags(map_offsets)

        return text

    def _strpos(self, offset:int, errors:str) -> int:
        # Return the offset of that (bytes) *offset* in a decoded string.
        if offset not in self._str_alignment:
            self._str_alignment[offset] = len(
                self[:offset].decode(self._encoding, errors)
            )

        return self._str_alignment[offset]


class Unicode(str, AnnotatedContent):
    """
    A specialized :func:`str` class for text as Unicode (ie., decoded)
    and implementing :class:`.AnnotatedContent`.
    """

    #noinspection PyUnusedLocal
    def __init__(self, *args):
        """
        Instantiate just as any `str` object.
        """
        AnnotatedContent.__init__(self)

    def getMultispan(self, *key:tuple([int])) -> list([str]):
        """
        Get the text of a multi-span key (ie., key length is an even value,
        incl. just a single pair), as a `list` of `str`, using the integer
        values of each pair in the key as start and end positions.

        :param key: a tuple of 2\ ``n`` integer values, where
                    ``n = {1, 2, ...}``
        :return: A `list` of `str` spans.
        """
        assert len(key) % 2 == 0, "odd number of offsets"
        return [ self[key[i]:key[i + 1]]
                 for i in range(0, len(key), 2) ]

    def toBinary(self, encoding:str, errors:str="strict") -> Binary:
        """
        Return the raw :class:`.Binary` view of the text, with
        any tag keys mapped to the offsets in the encoded `bytes`.

        :raises UnicodeEncodeError: If any tag key is illegal.
        """
        doc = Binary(self.encode(encoding), encoding)

        if self._tags:
            alignment = self._mapStrToBytes(doc.encoding, errors)
            map_offsets = lambda offsets: tuple(
                alignment[pos] for pos in offsets
            )
            doc.tags = self._mapTags(map_offsets)

        return doc

    def _mapStrToBytes(self, encoding:str, errors:str) -> list([int]):
        # Return a list of integers, one for each position in the content
        # string. The value at each position corresponds to the offset of
        # that position in the encoded bytes representation of the text.
        strlen = len(self)
        alignment = [-1] * (strlen + 1)
        idx = 0
        pos = 0

        while idx < strlen:
            alignment[idx] = pos
            char = self[idx]

            try:
                pos += len(char.encode(encoding, errors))
                idx += 1
            except UnicodeEncodeError:
                if idx + 1 < strlen:
                    char = self[idx:idx + 2]
                    pos += len(char.encode(encoding, errors))
                    idx += 2
                else:
                    raise

        alignment[idx] = pos
        return alignment
