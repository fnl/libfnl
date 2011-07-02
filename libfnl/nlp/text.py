"""
.. py:module:: text
   :synopsis: Data types to annotate text.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from base64 import b64encode
from collections import defaultdict, namedtuple
from hashlib import sha256
from io import StringIO
from types import FunctionType
from libfnl.couch.broker import Database, Document


class AnnotatedContent:
    """
    Abstract manager class for tagging content, implemented by both
    :class:`.Binary` and :class:`.Unicode`.
    """

    def __init__(self):
        self._tags = {}
        self.metadata = {}

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
        value, highest first), and then the rest of the offset values. For
        example:

        .. testsetup::

            from libfnl.nlp.text import AnnotatedContent

        .. doctest::

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

    def addOffsets(self, namespace:str, key:str, offset_list:[([int])]):
        """
        Overwrite any offsets stored in *namespace*, *key* with this new
        *offset_list*.
        """
        if namespace not in self._tags: self._tags[namespace] = {}
        self._tags[namespace][key] = list(offset_list)

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

    def iterTags(self, ordered:bool=False) -> iter([(str, str, tuple)]):
        """
        Yield each tag as a ``(namespace, key, offsets)`` tuple.

        :param ordered: Yield the tuples in order of the offset values.
        """
        if ordered:
            all_tags = defaultdict(list)

            for ns, keys in self._tags.items():
                for key, offset_list in keys.items():
                    for offset in offset_list:
                        all_tags[offset].append((ns, key, offset))

            for offset in AnnotatedContent.sorted(all_tags.keys()):
                for item in all_tags[offset]:
                    yield item
        else:
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
            sorted according to :meth:`.sorted()`.
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
        :meth:`.sorted()`.

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

    @staticmethod
    def load(db:Database, doc_id:str, filename:str=None):
        """
        Load a text from a CouchDB.

        :param db: The Couch :class:`.Database`.
        :param doc_id: The document ID to load.
        :param filename: The name of the text attachment to load; if None,
            the document is checked for its ``textfile`` value.
        :return: A :class:`.Binary` text.
        :raise KeyError: If no document with that ID exists.
        :raise ValueError: If no file with that name exists or if the
            name of the file cannot be established.
        """
        doc = db[doc_id]

        try:
            if not filename: filename = doc["textfile"]
        except KeyError:
            msg = "cannot determine text attachment for {}".format(doc_id)
            raise ValueError(msg)

        att = db.getAttachment(doc, filename)

        if att is None:
            msg = "{} has no {} filename".format(doc_id, filename)
            raise ValueError(msg)

        binary = Binary(att.data, att.encoding)
        binary._tags = doc["tags"]
        del doc["tags"]
        binary.metadata = doc

        # cast offset values from lists to immutable tuples
        for keys in binary._tags.values():
            for offsets in keys.values():
                for i in range(len(offsets)):
                    offsets[i] = tuple(offsets[i])

        return binary

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

    def save(self, db:Database, doc_id:str=None, update:bool=False,
             filename:str="binary.txt") -> (str, str):
        """
        Store this text in a Couch *DB*, overwriting any existing document,
        unless *update* is used.

        To create the actual document, :meth:`.toDocument` is used, and, if
        this text already existed, the original version is first fetched from
        the database.

        :param db: The Couch :class:`.Database`.
        :param doc_id: The document ID to use; if not set, use the ``_id`` in
            metadata if set or finally the :attr:`.hexdigest` otherwise.
        :param update: Use dictionary updates instead of overwriting existing
            content (if the text already exists in the DB).
        :param filename: The name to use for the text attachment.
        :return: An ``(id, rev)`` tuple of the saved document.
        """
        if not doc_id:
            doc_id = self.metadata['_id'] if '_id' in self.metadata else \
                     self.hexdigest

        old = db[doc_id] if doc_id in db else None

        if update and old:
            doc = self.toDocument(old, filename)
        else:
            doc = self.toDocument(doc_id, filename)

        if not update and old:
            doc.rev = old.rev

        return db.save(doc)

    def toDocument(self, id_or_doc=None, filename:str="binary.txt") -> Document:
        """
        Convert this text to a CouchDB :class:`.Document`.

        The document ID will be either the one given in the *id or doc*, or, if
        set, the ``_id`` in :attr:`.metadata`, or, finally, the
        :attr:`.hexdigest` string. The document itself is made up of the
        :attr:`.metadata` as initial dictionary to base the document on, the
        :attr:`.tags` added as key with the same name, and a key ``textfile``
        to store the name of the attachment containing the tagged text.

        :param id_or_doc: Use the given ID as ``_id``, or, if a `Document` or
            dictionary, use it instead of creating a new document, updating it
            with the text's `metadata` and `tags`, while attaching the text,
            and return the updated document.
        :param filename: The name of the text file attachment.
        """
        assert "tags" not in self.metadata

        if id_or_doc and isinstance(id_or_doc, str):
            self.metadata["_id"] = id_or_doc
        elif not id_or_doc and "_id" not in self.metadata:
            self.metadata["_id"] = self.hexdigest

        if id_or_doc and isinstance(id_or_doc, dict):
            doc = id_or_doc
            doc.update(self.metadata)
        else:
            doc = Document(self.metadata)

        if "tags" in doc and isinstance(doc["tags"], dict):
            doc["tags"].update(self._tags)
        else:
            doc["tags"] = self.tags

        atts = doc.get('_attachments', {})
        atts[filename] = {
            'content_type': 'text/plain; charset={}'.format(self.encoding),
            'data': b64encode(self).decode('ASCII')
        }
        doc['_attachments'] = atts
        doc['textfile'] = filename
        return doc

    def toUnicode(self, errors:str="strict"):
        """
        Return the :class:`.Unicode` view of this document, with
        any tag offsets mapped to the positions in the decoded Unicode.

        :raise UnicodeDecodeError: If any tag key is illegal.
        :return: :class:`.Unicode`
        """
        text = Unicode(self.decode(self._encoding, errors))

        if self._tags:
            mapper = lambda offsets: [ tuple( self._strpos(pos, errors)
                                              for pos in o ) for o in offsets]
            text._tags = AnnotatedContent._copyTags(self._tags, mapper)

        text.metadata = dict(self.metadata)
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

    def __str__(self) -> str:
        """
        If not tagged, just return the string, otherwise, if tags have been
        set, it returns a XML-like tagging of the string.

        .. warning::

            Note that if any tags have partial overlaps, this will produce XML
            that is invalid.
        """
        if self._tags:
            if __debug__:
                overlaps = self.firstPartiallyOverlappingTags()
                assert not overlaps, overlaps

            buffer = StringIO()
            close_tags = defaultdict(list)
            GetTag = self._getTagHelper() # a function returning tags in order
            tag = GetTag()                # of their offsets, as named tuples

            for pos, char in enumerate(self):
                if pos in close_tags:
                    for closer in reversed(close_tags[pos]):
                        buffer.write(closer)

                while tag.start == pos:
                    # get the (XML-like) open tag string and add end tags to
                    # the close_tags dictionary:
                    tag_str = Unicode._strTag(close_tags, pos, tag)
                    buffer.write(tag_str)
                    try: tag = GetTag()
                    except StopIteration: tag = tag._replace(start=-1)

                buffer.write(char)

            # append remaining closers and possible positional tags at the
            # very end of the Unicode string
            if len(self) in close_tags: # remaining closers at end
                for closer in reversed(close_tags[len(self)]):
                    buffer.write(closer)

            if tag.start == len(self): # remaining (single-offset) tags at end
                while True:
                    # no more close_tags should be set here - if, we'd get an
                    # error for trying to do something dict-like with ``None``
                    tag_str = Unicode._strTag(None, len(self), tag)
                    buffer.write(tag_str)
                    try: tag = GetTag()
                    except StopIteration: break

            return buffer.getvalue()
        else:
            return str.__str__(self)

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

    def firstPartiallyOverlappingTags(self) -> bool:
        """
        Return a list of two ``(namespace, key, start, end)`` tuples of
        the first two tags that were found to partially overlap.

        Return ``None`` if no tag **partially** overlaps with any other.
        """
        state = [] # stores the last tags iterated

        # iterate over the tags, ordered by lowest start and then highest end
        for tag in self.iterTags(True):
            current = (tag[0], tag[1], tag[2][0], tag[2][-1])
            # pop tags where the end is before or at the current tag's start
            while state and state[-1][3] <= current[2]: state.pop()

            if state: # compare this tag to the last tag on the state store
                last = state[-1]
                # check the current tag starts after the last and ends before
                # it (anything else would be invalid, as at this stage we know
                # the last tag does not end before the current tag starts)
                if last[2] <= current[2] and last[3] >= current[3]:
                    state.append(current)
                else:
                    return [last, current] # REPORT PARTIAL OVERLAP
            else: # nothing on state list, just add
                state.append(current)

        return None

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

        doc.metadata = dict(self.metadata)
        return doc

    @staticmethod
    def _strTag(close_tags:defaultdict, pos:int, tag:namedtuple) -> str:
        # Create the opening tag string representation of *tag* at *pos*, and
        # add the closing tag to the *close_tags* defaultdict(list).
        # This is a helper for __str__().
        if len(tag.offsets) == 1: # Positional tag
            tag_str = '<{} id={} />'.format(tag.name, tag.id)
        else:
            close_tags[tag.offsets[-1]].append('</{}>'.format(tag.name))

            if len(tag.offsets) == 2: # Single-span tag
                tag_str = '<{} id={}>'.format(tag.name, tag.id)
            else: # Multi-span tag
                o = tag.offsets
                spans = ' '.join('{}:{}'.format(str(o[i]     - pos),
                                                  str(o[i + 1] - pos))
                                 for i in range(len(o), step=2))

                tag_str = '<{} id={} spans="{}">'.format(
                    tag.name, tag.id, spans,
                )

        return tag_str

    def _getTagHelper(self) -> FunctionType:
        # Get the next tag (in offset order) with a unique ID for it.
        # This is a helper for __str__().
        Tag = namedtuple("Tag", "id name start offsets")
        ordered_tags = enumerate(self.iterTags(True))

        def GetTag():
            id, (ns, key, offs) = next(ordered_tags)
            return Tag(id, "{}:{}".format(ns, key), offs[0], offs)

        return GetTag

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
