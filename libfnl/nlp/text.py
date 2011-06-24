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
        self._tags = {}

    def __len__(self):
        raise NotImplementedError("abstract")

    @property
    def tags(self) -> {str: {str: [(int,)]}}:
        """
        Get a copy of the dictionary of tags.
        """
        return AnnotatedContent._copyTags(self._tags)

    @tags.setter
    def tags(self, tags:{str: {str: [(int,)]}}):
        """
        Replace the entire tags dictionary. No safety checks are made, but
        the tags are copied before they are stored.
        """
        self._tags = AnnotatedContent._copyTags(tags)

    @staticmethod
    def sorted(offsets:[(int,)]) -> [(int,)]:
        """
        Return a sorted iterator over the list of *offsets*.

        The offsets are sorted by the values of their offsets. Offset sorting
        is in order of the offset's start (lowest first), end (last offset
        value, highest first), and then the rest of the offset values.

        For example::

        >>> offsets = [(1, 2, 3, 5), (1, 3), (2,), (1, 2, 4, 5)]
        >>> list(AnnotatedContent.sorted(offsets))
        [(1, 2, 3, 5), (1, 2, 4, 5), (1, 3), (2,)]
        """
        return sorted(offsets, key=lambda k: (k[0], k[-1] * -1, k))

    def addTag(self, namespace:str, key:str, offsets:tuple([int])):
        """
        Add a new tag.

        Unless in optimized mode, various assertions are made to ensure the
        tag conforms to the specification.

        The *namespace* and *key* may not be ``None`` or the empty string.

        The *offsets* may not be ``None`` or an empty tuple.

        :param namespace: The namespace this tag belongs to.
        :param key: The identifier for that tag in the given namespace.
        :param offsets: The position of this tag; either a single offset value
            for tags pointing to just one location in the content, or paired
            integers in increasing order indicating the offsets (start, end) of
            one or more spans (ie., each offset must be larger than its former).
        :raise AssertionError: If the input is malformed.
        """
        # assert all elements are given and not empty
        assert namespace, "namespace missing"
        assert key, "key missing"
        assert offsets, "offsets missing"
        tags = self._getTags(namespace, key)
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
        tags.append(tuple(offsets))

    def delNamespace(self, namespace:str):
        """
        Delete an entire *namespace* and all its containing tags.

        :raise KeyError: If the *namespace* doesn't exist.
        """
        del self._tags[namespace]

    def delKey(self, namespace:str, key:str):
        """
        Delete the all the offsets for *key* in *namespace* and the *key*
        itself.

        Also deletes the *namespace* it it happens to be empty after that.

        :raise KeyError: If the *namespace* or *key* doesn't exist.
        """
        del self._tags[namespace][key]
        # also clean up the namespace if empty
        if not self._tags[namespace]: del self._tags[namespace]

    def delOffset(self, namespace:str, key:str, offsets:tuple([int])):
        """
        Delete the *offset* in *namespace*, *key*.

        Also deletes the *key* it it happens to be empty after that, as well
        as the *namespace*, if empty too.

        :raise KeyError: If the *namespace* or *key* doesn't exist.
        :raise ValueError: If a tag at those *offsets* doesn't exist.
        """
        ns = self._tags[namespace]
        ns[key].remove(offsets)
        # also clean up the key and namespace if empty
        if not ns[key]:
            del ns[key]
            if not ns: del self._tags[namespace]

    def iterTags(self) -> iter([(str, str, tuple)]):
        """
        Yield each tags as ``(namespace, key, offsets)`` tuples.
        """
        for ns, keys in self._tags.items():
            for key, offset_list in keys.items():
                for offsets in offset_list:
                    yield ns, key, offsets

    def namespaces(self) -> iter([str]):
        """
        Get an iterator over the namespaces.
        """
        return self._tags.keys()

    def keys(self, namespace:str) -> iter([str]):
        """
        Get an iterator over the keys in *namespace*.

        :raise KeyError: If that *namespace* doesn't exist.
        """
        return self._tags[namespace].keys()

    def offsets(self, namespace:str, key:str, sort:bool=False) -> [(int,)]:
        """
        Get a list of all tag offsets (int-tuples) in *namespace*, *key*.

        :param sort: If ``True``, return an iterator that yields the offsets
            sorted according to :method:`.sorted()`.
        :raise KeyError: If the *namespace* or *key* doesn't exist.
        """
        if sort:
            extract = AnnotatedContent.sorted
        else:
            extract = list

        return extract(self._tags[namespace][key])

    def sort(self, namespace:str=None, key:str=None):
        """
        Order any tags' offset lists, in place and according to
        :method:`.sorted()`.

        :param namespace: The *namespace* to sort or all if ``None``.
        :param key: The tag's *key* to sort or all if ``None``.
        :raise KeyError: If the *namespace* or *key* doesn't exist.
        """
        ns_iter = (namespace,) if namespace else self._tags.keys()

        for ns in ns_iter:
            ns_dict = self._tags[ns]
            key_iter = (key,) if key else ns_dict.keys()

            for k in key_iter:
                ns_dict[k] = list(AnnotatedContent.sorted(ns_dict[k]))

    @staticmethod
    def _copyTags(tags, Offsets=list):
        # Make a 'deep copy' of the *tags*.
        # *Offsets* can be any function to copy the list of offsets (tuples).
        ns, k = None, None
        repack = lambda keys: { k: Offsets(o) for k, o in keys.items() }
        return { ns: repack(keys) for ns, keys in tags.items() }

    def _getTags(self, namespace:str, key:str):
        # Try to fetch the *namespace* and *key* values or create new ones.
        if namespace in self._tags:
            ns = self._tags[namespace]
        else:
            ns = dict()
            self._tags[namespace] = ns

        if key in ns:
            tags = ns[key]
        else:
            tags = list()
            ns[key] = tags

        return tags


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
        To instantiate a `Binary`, pass it the text as `bytes` and a `str`
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
        self._encoding = str(args[1])
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

        :raise UnicodeDecodeError: If any tag key is illegal.
        :return: :class:`.Unicode`
        """
        text = Unicode(self.decode(self._encoding, errors))

        if self._tags:
            mapper = lambda offsets: [ tuple( self._strpos(pos, errors)
                                              for pos in o ) for o in offsets]
            text._tags = AnnotatedContent._copyTags(self._tags, mapper)

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
        Instantiate just as you would any other string.
        """
        AnnotatedContent.__init__(self)

    def getMultispan(self, offsets:tuple([int])) -> list([str]):
        """
        Get the text of a multi-span offsets (ie., key length is an even value,
        but can also be just a single pair), as a `list` of strings, using the
        integer values of each pair in the key as start and end positions.

        :param offsets: a tuple of 2\ ``n`` integer values, where ``n > 0``.
        """
        assert len(offsets) % 2 == 0, "odd number of offsets"
        return [ self[offsets[i]:offsets[i + 1]]
                 for i in range(0, len(offsets), 2) ]

    def toBinary(self, encoding:str, errors:str="strict") -> Binary:
        """
        Return the raw :class:`.Binary` view of the text, with
        any tag's offsets aligned to the encoded `bytes`.

        :raise UnicodeEncodeError: If any tag's offsets are illegal.
        """
        doc = Binary(self, encoding, errors)

        if self._tags:
            alignment = self._mapping(encoding, errors)
            mapper = lambda offsets: [ tuple( alignment[pos] for pos in o )
                                       for o in offsets ]
            doc._tags = AnnotatedContent._copyTags(self._tags, mapper)

        return doc

    def _mapping(self, encoding:str, errors:str) -> list([int]):
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
