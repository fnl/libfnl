"""
.. py:module:: text
   :synopsis: Data types to annotate text.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
"""
from hashlib import sha256


class AnnotatedContent:
    """
    Abstract manager class for tagging content, implemented by both
    :py:class:`.Binary` and :py:class:`.Unicode`.
    """

    def __init__(self):
        self._tags = dict()

    def __len__(self):
        raise NotImplementedError("abstract")

    def addTag(self, namespace:str, value:str, *key:tuple([int])):
        """
        Add a new tag.

        :param namespace: The namespace this tag belongs to.
        :param value: The value of the tag, e.g. the PoS name, chunk type...
        :param key: The position of this tag; either a single offset value
                    for tags pointing to just one location in the content,
                    or paired integers in increasing order indicating the
                    offsets (start, end) of one or more spans. It is
                    not allowed to add multiple tags with the same *key* and
                    *namespace*.
        :raises AssertionError: If the key is malformed.
        """
        # try to fetch the namespace or create a new one
        if namespace not in self._tags:
            tags = dict()
            self._tags[namespace] = tags
        else:
            tags = self._tags[namespace]

        # check key is not duplicate and well-formed
        assert key not in tags, \
            "{} annotation at {} already exists".format(namespace, key)
        assert key[0] >= 0 and key[-1] <= len(self), \
            "offsets {} invalid (max: {})".format(key, len(self))

        if len(key) > 1:
            assert all(key[i-1] < key[i] for i in range(1, len(key))), \
                "key offsets {} not successive".format(key)
            assert len(key) % 2 == 0, "odd number of offsets: {}".format(key)

        # all ok, set the value
        tags[key] = value

    def delTag(self, namespace:str, *key:tuple([int])):
        """
        Delete the tag in *namespace* with the given *key*.

        :raises KeyError: if the tag doesn't exist.
        """
        del self._tags[namespace][key]

        # also clean up the namespace if empty
        if not self._tags[namespace]:
            del self._tags[namespace]

    def getTags(self, namespace:str) -> dict({tuple([int]): str}):
        """
        Get a dictionary of all tags in that *namespace*.
        """
        return dict(self._tags[namespace])

    def getValue(self, namespace:str, *key:tuple([int])) -> str:
        """
        Get the exact value of a tag in *namespace* identified by *key*.
        """
        return self._tags[namespace][key]

    def iterNamespaces(self) -> iter([str]):
        """
        Return an iterator of all tag namespaces.
        """
        return self._tags.keys()

    def iterTags(self, namespace:str) -> iter([(tuple([int]), str)]):
        """
        Return an iterator of all tags in *namespace*, returning the tags
        in order of the key's start (lowest first), end (last offset in key,
        highest first), and finally ordered by the rest of the key.

        For example, the keys: (1,2,3), (1,3), (2,), and (1,3,4) will be
        ordered like this:

        #. (1,3,4)
        #. (1,2,3)
        #. (1,3)
        #. (2,)

        :return: An iterator yielding tuples of (key, value) pairs.
        """
        tags = self._tags[namespace]
        keys = sorted(tags.keys(), key=lambda k: (k[0], k[-1] * -1, k))
        for k in keys: yield k, tags[k]

    def tags(self) -> list([(tuple([int]), str, str)]):
        """
        Return a list of all tags on this instance, ordered just as with
        `iterTags`, but over all namespaces.

        :return: A list of (key, namespace, value) tuples.
        """
        key_ns_val = []

        for ns, kv in self._tags.items():
            key_ns_val.extend(
                (key[0], key[-1] * -1, key, ns, val)
                for key, val in kv.items()
            )

        return list([item[2:] for item in sorted(key_ns_val)])


class Binary(bytes, AnnotatedContent):
    """
    A specialized :py:func:`bytes` class for binary text (ie., encoded)
    and implementing :py:class:`.AnnotatedContent`.
    """

    def __new__(cls, *args):
        # get rid of the encoding argument giving hickups to bytes...
        if isinstance(args[0], str):
            return super(Binary, cls).__new__(cls, *args)
        else:
            return super(Binary, cls).__new__(cls, args[0])


    def __init__(self, *args):
        """
        To create a new Binary, pass it the text as `bytes` and a `str`
        with the encoding of the text, or pass the text as `str`, again with
        a target encoding, and possibly the error parameter for the encoding
        operation (see `bytes`).
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
        Return the :py:class:`.Unicode` view of this document, with
        any tag keys mapped to the offsets in the decoded Unicode.
        """
        string = self.decode(self._encoding, errors)
        text = Unicode(string)

        if self._tags:
            for key, ns, val in self.tags():
                translated_key = [self._strpos(pos, errors) for pos in key]
                text.addTag(ns, val, *translated_key)

        return text

    def _strpos(self, pos:int, errors:str) -> int:
        # Return the offset of that *pos* in the Unicode string.
        if pos not in self._str_alignment:
            self._str_alignment[pos] = len(
                self[:pos].decode(self._encoding, errors)
            )

        return self._str_alignment[pos]


class Unicode(str, AnnotatedContent):
    """
    A specialized :py:func:`str` class for text as Unicode (ie., decoded)
    and implementing :py:class:`.AnnotatedContent`.
    """

    #noinspection PyUnusedLocal
    def __init__(self, *args):
        """
        Create just as any `str` object.
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
        Return the raw :py:class:`.Binary` view of the text, with
        any tag keys mapped to the offsets in the encoded `bytes`.
        """
        doc = Binary(self.encode(encoding), encoding)

        if self._tags:
            alignment = self._mapStrToBytes(doc.encoding, errors)

            for key, ns, val in self.tags():
                translated_key = [alignment[pos] for pos in key]
                doc.addTag(ns, val, *translated_key)

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
