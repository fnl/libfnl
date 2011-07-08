"""
.. py:module:: text
   :synopsis: Data types to annotate text.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import re
from cgi import escape
from collections import defaultdict, namedtuple
from datetime import datetime
from hashlib import md5 as digest
from io import StringIO
from itertools import count
from libfnl.couch.broker import Document
from libfnl.couch.serializer import b64encode
from logging import getLogger
from math import sqrt
from sys import maxsize, maxunicode
from types import FunctionType
from unicodedata import category
from urllib.parse import quote

class Annotated:
    """
    Abstract manager class for tagging content, implemented by both
    :class:`.Binary` and :class:`.Unicode`.
    """

    L = getLogger('Annotated')

    def __init__(self):
        self._tags = {}
        self.metadata = {}

    def __len__(self) -> int:
        # Unicode/str: return string (quasi-"character") length
        # Binary/bytes: return byte length
        raise NotImplementedError('abstract')

    @staticmethod
    def sorted(offsets:set, block:bool=False) -> list:
        """
        Return a sorted iterator over the *offsets* (a `set` or iterable of
        offsets).

        The offsets are sorted by their positional values. Offset sorting
        is in order of the offset's start (lowest first), end (last offset
        value, highest first), and then the rest of the offset values. For
        example:

        .. testsetup::

            from libfnl.nlp.text import Annotated

        .. doctest::

            >>> offsets = [(1, 2, 3, 5), (1, 2), (1, 5), (2,), (1, 2, 4, 5)]
            >>> list(Annotated.sorted(offsets))
            [(1, 5), (1, 2, 3, 5), (1, 2, 4, 5), (1, 2), (2,)]

        :param block: If ``True``, the offsets are faster sorted only by their
            lowest first and highest last element (ie., not regarding
            other positional values an offset might have, as above).

        .. doctest::

            >>> # Example including an overlapping tag pair: (1, 2), (2, 3)
            >>> offsets = [(1, 5), (1, 2), (2, 3), (1, 2, 3, 4)]
            >>> list(Annotated.sorted(offsets, True))
            [(1, 5), (1, 2, 3, 4), (1, 2), (2, 3)]
        """
        if block:
            return sorted(offsets, key=lambda k: (k[0], k[-1] * -1))
        else:
            return sorted(offsets, key=lambda k: (k[0], k[-1] * -1, k))

    @staticmethod
    def fromDocument(doc:dict):
        # Convert CouchDB documents to text.
        raise NotImplementedError('abstract')

    @staticmethod
    def attrOffset(offset:str) -> tuple:
        """
        Convert a string representation of an offset for the attributes
        dictionary to a real tuple.

        :param offset: A offset representation, eg., ``"(1, 2)"``.
        :return: The real `tuple`, eg., ``(1, 2)``.
        """
        return tuple(int(i) for i in offset[1:-1].split(','))

    @property
    def attributes(self) -> dict:
        """
        Get the dictionary of ``metadata['attributes']`` or ``None``.
        """
        if 'attributes' not in self.metadata:
            return None

        attr_dict = dict(self.metadata['attributes'])

        for ns, keys in attr_dict.items():
            keys_dict = {}

            for k, offsets in keys.items():
                offsets_dict = {}

                for o, attrs in offsets.items():
                    if isinstance(o, str):
                        offsets_dict[Annotated.attrOffset(o)] = attrs
                    else:
                        offsets_dict[o] = attrs

                keys_dict[k] = offsets_dict

            attr_dict[ns] = keys_dict

        return attr_dict

    @attributes.setter
    def attributes(self, attributes:dict):
        """
        Set or replace the entire attributes dictionary.
        """
        for keys in attributes.values():
            for offsets in keys.values():
                for o, attrs in offsets.items():
                    if isinstance(o, tuple):
                        offsets[repr(o)] = attrs
                        del offsets[o]

        self.metadata['attributes'] = attributes

    @property
    def tags(self) -> dict:
        """
        Get (a copy of) the dictionary of tags.
        """
        return Annotated._copyTags(self._tags)

    @tags.setter
    def tags(self, tags:dict):
        """
        Replace the entire tags dictionary. No safety checks are made, but
        the tags are copied before they are stored.
        """
        self._tags = Annotated._copyTags(tags)

    def addAttributes(self, namespace:str, key:str, offset:tuple, attrs:dict):
        """
        Add an *attrs* dictionary for the given tag, saved in the
        :attr:`metadata` key ``attributes``, overwriting any that might exist
        there.
        """
        if 'attributes' not in self.metadata:
            self.metadata['attributes'] = {
                namespace: { key: { repr(offset): attrs } }
            }
        else:
            attributes = self.metadata['attributes']

            if namespace not in attributes:
                ns = attributes['namespace'] = {}
            else:
                ns = attributes['namespace']

            if key not in ns:
                k = ns[key] = {}
            else:
                k = ns[key]

            k[repr(offset)] = attrs

    def addOffsets(self, namespace:str, key:str, offsets:set):
        """
        Overwrite any *offsets* stored in *namespace*, *key* with this new
        `set` (or iterable).

        If the *namespace* or *key* do not exist, they are created.

        .. note::

            No safety checks are made to ensure the offsets are conforming to
            the specification. It is the sole responsibility of the user
            to ensure the tags thus set are correct.
        """
        if namespace not in self._tags: self._tags[namespace] = {}
        self._tags[namespace][key] = set(offsets)

    def addTag(self, namespace:str, key:str, offset:tuple):
        """
        Add a new tag.

        Unless in optimized mode, various assertions are made to ensure the
        tag conforms to the specification.

        The *namespace* and *key* may not be ``None`` or the empty string.

        The *offset* may not be ``None`` or an empty tuple.

        :param namespace: The namespace this tag belongs to.
        :param key: The identifier for that tag in the given namespace.
        :param offset: The position of this tag; either a single position
            for tags pointing to just one location in the content, or paired
            integers in increasing order indicating the offset (start, end) of
            one or more spans (ie., each value must be larger than its former).
        :raise AssertionError: If the input is malformed.
        """
        # assert all elements are given and not empty
        assert namespace, "namespace missing"
        assert key, "key missing"
        assert offset, "offset missing"
        tags = self._getTags(namespace, key)
        # assertions that the offset are well-formed
        assert offset[0] >= 0 and offset[-1] <= len(self), \
            "offset {} invalid (max: {})".format(offset, len(self))

        if len(offset) > 1:
            assert len(offset) % 2 == 0, \
                "odd number of positions: {}".format(offset)
            assert all(offset[i-1] < offset[i]
                       for i in range(1, len(offset))), \
                "offset positions {} not successive".format(offset)

        # all ok, append the tag
        tags.append(tuple(offset))

    def delNamespace(self, namespace:str):
        """
        Delete an entire *namespace* and all its tags.

        :raise KeyError: If the *namespace* doesn't exist.
        """
        del self._tags[namespace]

    def delKey(self, namespace:str, key:str):
        """
        Delete *key* in *namespace* and all its offsets.

        Also deletes the *namespace* it it happens to be empty after that.

        :raise KeyError: If the *namespace* or *key* doesn't exist.
        """
        del self._tags[namespace][key]
        # also clean up the namespace if empty
        if not self._tags[namespace]: del self._tags[namespace]

    def delOffset(self, namespace:str, key:str, offset:tuple):
        """
        Delete a *offset* `tuple` in the *namespace* of *key*.

        Also deletes the *key* it it happens to be empty after that, as well
        as the *namespace*, if empty, too.

        :raise KeyError: If the *namespace* or *key* doesn't exist.
        :raise ValueError: If a tag at those *offset* doesn't exist.
        """
        ns = self._tags[namespace]
        ns[key].remove(offset)

        # also clean up the key and namespace if empty
        if not ns[key]:
            del ns[key]
            if not ns: del self._tags[namespace]

    def iterTags(self, sort:bool=False, block:bool=False) -> iter([tuple]):
        """
        Yield each tag as a ``(namespace, key, offset)`` tuple.

        :param sort: Yield the tuples in order of the offset values **over
            all namespaces**. See :meth:`.Annotated.sorted` for offset order.
        :param block: If *sort* is ``True``, all tags with the same start
            and end (``offset[-1]``) can be emitted as one block -- then, the
            iterator returns lists of tag tuples instead of the individual
            tuples; the tuples inside each list will only be in coarse *block*
            sort order, not the fine-grained `sorted` order.
        """
        if sort:
            all_tags = defaultdict(list)
            rng = (None, None)
            grp = None

            for ns, keys in self._tags.items():
                for key, offsets in keys.items():
                    for o in offsets:
                        all_tags[o].append((ns, key, o))

            if block:
                for o in Annotated.sorted(all_tags.keys(), block):
                    if rng[0] == o[0] and rng[1] == o[-1]:
                        grp.extend(all_tags[o])
                    else:
                        if grp: yield grp
                        grp = all_tags[o]
                        rng = (o[0], o[-1])
            else:
                for o in Annotated.sorted(all_tags.keys()):
                    for item in all_tags[o]:
                        yield item
        else:
            for ns, keys in self._tags.items():
                for key, offsets in keys.items():
                    for o in offsets:
                        yield ns, key, o

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

    def offsets(self, namespace:str, key:str, sort:bool=False) -> set:
        """
        Get a `set` of all tag offsets (integer tuples) in a *namespace* and for
        a *key*.

        :param sort: If ``True``, return an iterator that yields the offsets
            sorted according to :meth:`.sorted()`.
        :raise KeyError: If the *namespace* or *key* doesn't exist.
        """
        if sort:
            extract = Annotated.sorted
        else:
            extract = set

        return extract(self._tags[namespace][key])

    def slice(self, start:int=None, end:int=None):
        """
        Return the requested text slice of this instance as as a new text class
        instance and with the tags and their changed offsets correctly added
        (if there are any in that particular slice).

        At least either the *start* or the *end* must be specified. The *end*
        can be a negative integer, just as in ``seq[:-10]``, while only
        providing *start* results in a ``self[<start>:]`` slice call.

        .. note::

            Tags that do not cover the entire length of the slice are not
            preserved! Also, metadata is not copied to the new instance.

        :param start: The start position of the slice.
        :param end: The end position of the slice.
        :return: The text slice, either :class:`.Unicode` or :class:`.Binary`.
        :raise IndexError: If the provided *start* or *end* value is illegal.
        """
        if start is None:
            start = 0
            slice = self[:end]
        elif end is None:
            end = len(self)
            slice = self[start:]
        else:
            slice = self[start:end]

        if end < 0: end += len(self)
        tags = dict()

        for ns, keys in self._tags.items():
            ns_dict = dict()

            for key, offsets in keys.items():
                key_dict = defaultdict(set)

                for o in offsets:
                    if o[0] >= start and o[-1] <= end:
                        key_dict[key].add(tuple(i - start for i in o))

                if key_dict:
                    ns_dict[key] = dict(key_dict)

            if ns_dict:
                tags[ns] = ns_dict

        if isinstance(slice, bytes):
            text = Binary(slice, self._encoding)
        else:
            text = Unicode(slice)

        text._tags = tags
        return text

    def toDocument(self, id_or_doc=None) -> Document:
        # Convert instance to a CouchDB document.
        raise NotImplementedError('abstract')

    @staticmethod
    def _copyTags(tags, Offsets=set) -> dict:
        # Make a 'deep copy' of the *tags*.
        # *Offsets* can be any function to copy the set of offsets.
        repack = lambda keys: { k: Offsets(o) for k, o in keys.items() }
        return { ns: repack(keys) for ns, keys in tags.items() }

    def _getTags(self, namespace:str, key:str) -> list:
        # Try to fetch the *namespace* and *key* values or create new ones.
        if namespace in self._tags:
            ns = self._tags[namespace]
        else:
            ns = dict()
            self._tags[namespace] = ns

        if key in ns:
            tags = ns[key]
        else:
            tags = set()
            ns[key] = tags

        return tags


class Binary(bytes, Annotated):
    """
    A specialized `bytes` class for binary (ie., encoded) text
    and implementing :class:`.Annotated`.

    Contrary to regular `bytes` objects, it also stores the encoding of
    itself, plus the annotation tags.
    """

    L = getLogger('Binary')

    def __new__(cls, *args):
        if isinstance(args[0], str):
            return super(Binary, cls).__new__(cls, *args)
        else:
            # get rid of the encoding argument when instantiating bytes...
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

        .. note::

            **To emphasize:** the second argument **must** be the encoding,
            unlike the behaviour of the `bytes` "constructor function".

        :param args: Minimally, a `bytes` or `str` text and a encoding `str`.
            If the first (text) argument is a `str`, encoding behaviour may
            be set, too (errors: ``'strict'``, ``'replace'``, or ``'ignore'``).
        """
        Annotated.__init__(self)
        self._digest = None
        self._encoding = str(args[1]).lower()
        self._str_alignment = dict()

    @staticmethod
    def fromDocument(doc:dict):
        """
        Create a new UTF-8-encoded :class:`.Binary` instance from a CouchDB
        document.

        The document must have the field ``text`` with the actual text, may
        have ``tags``, while all other fields are stored as :attr:`.metadata`.

        :param doc: The document; A `dict` or :class:`.Document` instance.
        :return: A :class:`.Binary` object.
        :raise KeyError: If the document has no ``text`` field.
        :raise AttributeError: If the document has a ``tags`` dictionary,
            but it is not in the correct format.
        """
        text = Binary(doc['text'], 'utf-8')
        text.metadata = dict(doc)
        del text.metadata['text']

        if 'tags' in doc:
            if isinstance(doc['tags'], dict):
                text.tags = doc['tags']

            del text.metadata['tags']

        return text

    @property
    def encoding(self) -> str:
        """
        The encoding of the text `bytes` (read-only).
        """
        return self._encoding

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
        The hash digest `bytes` of the content (read-only).
        """
        if not self._digest:
            self._digest = digest(self).digest()

        return self._digest

    def toDocument(self, id_or_doc=None) -> Document:
        """
        Create a Couch :class:`.Document` from this text with the fields
        ``created``, ``modified``, ``text``, ``tags``, and an ``_id``.

        .. note::

            The instance should be encoded in UTF-8, or have no tags, otherwise
            the tags first need to be converted to UTF-8 conform offsets. This
            is required because text in CouchDB is stored as UTF-8.

        Additionally, any values in :attr:`.metadata` are set as their own
        fields on the document.

        The parameter *id_or_doc* is optional and can be a string representing
        the ``_id`` to assign the Document, which will be used even if the
        text's metadata has such a key.

        In addition, *id_or_doc* can be a `Document` instance to update
        with the values of this text object. If the original document had
        tags and, most importantly, both texts match, each tag namespace
        gets its keys updated separately. If the text do not match, is not the
        case, the entire ``tags`` in the document get overwritten with the
        :attr:`.tags` of the text.

        The updating of tags is done as follows: To preserve as much of the
        keys on the document, if only ``doc['tags'].update(text.tags)`` were
        used, updates could "delete" keys on the document that do not exist
        on the text. Therefore, instead, tags get updated as::

            doc_tags = doc['tags']

            for ns, keys in self.tags.items():
                if ns in doc_tags:
                    doc_tags[ns].update(keys)
                else:
                    doc_tags[ns] = keys

        which preserves existing keys in namespaces of the document that are
        not set in the same namespace on the text. In addition, the entire
        document gets updated with the :attr:`.metadata` of the text. Ie.,
        any metadata that coincides with a field on the document, it will
        overwrite that field (including the ``_id`` value, if set on the
        metadata). The ``created`` date and time is always used from the
        supplied document (otherwise, :func:`datetime.now` is set)

        The fields ``text``, ``modified`` are always written, even if they are
        already set on a supplied document, to ensure consistency.
        """
        if self._tags and self.encoding != 'utf-8':
            tags = self.toUnicode().toBinary('utf-8')._tags
        else:
            tags = self.tags

        if id_or_doc:
            if isinstance(id_or_doc, str):
                doc = Document(self.metadata)
                doc['_id'] = id_or_doc
                doc['tags'] = tags
            else:
                doc = id_or_doc

                if 'tags' in self.metadata:
                    self.L.warn('pruning "tags" from metadata')
                    del self.metadata['tags']

                if 'created' in doc:
                    created = doc['created']
                elif 'created' in self.metadata:
                    created = self.metadata['created']
                else:
                    created = datetime.now().replace(microsecond=0)

                doc.update(self.metadata)
                doc['created'] = created
                doc_tags = None

                if 'tags' in doc:
                    doc_digest = digest(doc['text'].encode('utf-8')).digest()

                    if doc_digest == self.digest:
                        doc_tags = doc['tags'] # update tags

                        for ns, keys in tags.items():
                            if ns in doc_tags:
                                doc_tags[ns].update(keys)
                            else:
                                doc_tags[ns] = keys
                    else:
                        self.L.info('doc %s and Binary %s text mismatch',
                                    doc['_id'], self.base64digest)

                if doc_tags is None:
                    doc['tags'] = tags # overwrite tags
        else:
            doc = Document(self.metadata)
            doc['tags'] = tags  # overwrite tags

        doc['modified'] = datetime.now().replace(microsecond=0)
        doc['text'] = self.decode(self.encoding)
        assert digest.__name__.endswith('md5'), digest.__name__
        doc['MD5'] = self.base64digest
        if 'created' not in doc: doc['created'] = doc['modified']
        if '_id' not in doc: doc['_id'] = self.base64digest
        return doc

    def toUnicode(self, errors:str="strict"):
        """
        Return the :class:`.Unicode` view of this document, with
        any tag offsets mapped to the positions in the decoded Unicode string.

        :raise UnicodeDecodeError: If any tag key is illegal.
        :return: :class:`.Unicode`
        """
        #noinspection PyArgumentList
        text = Unicode(self.decode(self._encoding, errors))

        if self._tags:
            mapper = lambda offsets: { tuple( self._strpos(pos, errors)
                                              for pos in o ) for o in offsets }
            text._tags = Annotated._copyTags(self._tags, mapper)

        text.metadata = dict(self.metadata)
        return text

    def _strpos(self, pos:int, errors:str) -> int:
        # Return the (str) pos of that (bytes) *pos* in a decoded string.
        if pos not in self._str_alignment:
            self._str_alignment[pos] = len(
                self[:pos].decode(self._encoding, errors)
            )

        return self._str_alignment[pos]


class Unicode(str, Annotated):
    """
    A specialized :func:`str` (ie., "decoded") implementation of
    :class:`.Annotated`.

    Instantiate just as any other string.
    """

    L = getLogger('Unicode')

    key_weights = {}
    """
    A dictionary of key weights for element nesting order in the :meth:`.markup`
    representation of a tagged text.
    """

    ns_weights = {}
    """
    A dictionary of namespace weights for element nesting order in the
    :meth:`.markup` representation of a tagged text.
    """

    ns_map = {}
    """
    A dictionary of ``namespace: mangled_ns`` mappings to change or drop
    (empty value string or ``None``) namespaces of element names in text
    :meth:`.markup` representation.
    """

    def __init__(self, *_):
        Annotated.__init__(self)

    @staticmethod
    def fromDocument(doc:dict):
        """
        Create a new :class:`.Unicode` instance from a CouchDB document.

        .. seealso::

            A convenience wrapper for :meth:`.Binary.fromDocument`\ .
        """
        text = Binary.fromDocument(doc)
        return text.toUnicode()

    def firstOverlappingTagPair(self) -> list:
        """
        Return a list of two ``(namespace, key, start, end)`` tuples.

        These are the first two tags that were found to overlap. Return ``None``
        if no tag overlaps with any other.

        Very simplified, this detects situations such as the following one,
        leading to invalid markup:

            <tag1>text..<tag2>text...</tag1>text...</tag2>
        """
        state = [] # stores the last tags iterated

        # iterate over the tags, ordered by lowest start and then highest end
        for tag in self.iterTags(True, True):
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

    def multispan(self, offset:tuple) -> list:
        """
        Get the text of any kind of offset, as a `list` of strings, using the
        integer values of each pair in the key as start and end positions.

        The empty tag with a single offset value will return a list with a
        single empty string. An empty tuple would return an empty list.

        :param offset: a tuple of integers.
        """
        if not len(offset) % 2:
            return [ self[offset[i]:offset[i + 1]]
                     for i in range(0, len(offset), 2) ]
        else:
            return [ '' ]

    def toBinary(self, encoding:str, errors:str="strict") -> Binary:
        """
        Return the raw :class:`.Binary` view of the text, with
        any tag's offsets aligned to the encoded `bytes`.

        :raise UnicodeEncodeError: If any tag's offsets are illegal or if the
            text cannot be represented in the chosen *encoding*.
        """
        text = Binary(self, encoding, errors)

        if self._tags:
            alignment = self._mapping(encoding, errors)
            mapper = lambda offsets: { tuple( alignment[pos] for pos in o )
                                       for o in offsets }
            text._tags = Annotated._copyTags(self._tags, mapper)

        text.metadata = dict(self.metadata)
        if 'encoding' in text.metadata: text.metadata['encoding'] = encoding
        return text

    def toDocument(self, id_or_doc=None) -> Document:
        """
        Create a Couch :class:`.Document` from this text with the fields
        ``created``, ``modified``, ``text``, ``tags``, and an ``_id``.

        .. seealso::

            A convenience wrapper for :meth:`.Binary.toDocument`\ .
        """
        binary = self.toBinary('utf-8')
        return binary.toDocument(id_or_doc)

    def toMarkup(self) -> str:
        """
        If not tagged, return the regular string; otherwise, if tags
        have been set, return a markup view of the string with the
        tags transformed to proper markup elements.

        .. note::

            It is well advised to check for any overlapping tags by calling
            :meth:`.firstOverlappingTagPair` to check for such situations
            before using this transformation.
        """
        if self._tags:
            buffer = StringIO()
            close_tags = defaultdict(list)
            GetBlock = self._getElementHelper()
            start, block = GetBlock()

            for pos, char in enumerate(self):
                if pos in close_tags:
                    for closer in reversed(close_tags[pos]):
                        buffer.write(closer)

                if start == pos:
                    start, block = Unicode.__blockRepr(
                        GetBlock, block, buffer, close_tags
                    )

                buffer.write(char)

            # append remaining closers and possible positional tags at the
            # very end of the Unicode string
            if len(self) in close_tags: # remaining closers at end
                for closer in reversed(close_tags[len(self)]):
                    buffer.write(closer)

            if start == len(self): # remaining (single-offset) tags at end
                Unicode.__blockRepr(GetBlock, block, buffer, close_tags)

            return buffer.getvalue()
        else:
            return str(self)

    def _mapping(self, encoding:str, errors:str) -> list:
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
                # Maybe a surrogate pair from the SMP
                if idx + 1 < strlen:
                    pair = self[idx:idx + 2]
                    pos += len(pair.encode(encoding, errors))
                    idx += 2
                else:
                    raise

        alignment[idx] = pos
        return alignment

    def _getElementHelper(self) -> FunctionType:
        # Get the next block of elements in namespace-key weighted order, the
        # namespaces replaced as as required, and any attributes "prepared".
        # The return value is the GetBlock function at the end.
        # This is a helper for markup representations of text.
        Element = namedtuple("Element", "name attributes end")
        ordered_blocks = self.iterTags(True, True)
        attributes = self.metadata.get('attributes', {})
        sort_key = WeightedSort if (Unicode.ns_weights or
                                    Unicode.key_weights) else None
        NAME = re.compile(r'[:\w][:\-\.\w]*')

        def Check(name):
            # Ensure names are (of elements and attributes) are valid
            if not NAME.match(name):
                raise ValueError('invalid name "{}"'.format(name))

        def Name(ns, key):
            # Create the element's name (Element.name)
            if ns in self.ns_map:
                ns = '{}:'.format(self.ns_map[ns]) if self.ns_map[ns] else ''
            else:
                ns = '{}:'.format(ns)

            return Check('{}{}'.format(ns, key))

        def NarrowPython(offset, rel_off, start):
            # Correct offset values on narrow python builds for SMP characters
            test = self[start:offset[-1]]
            src = [i for i in enumerate(test)
                   if category(test[i]) == 'Cs']

            if src: # surrogate range character(s) detected...
                assert len(src) % 2 == 0, "lone surrogate range char"
                src = [src[i] for i in range(1, len(src), 2)]
                pos = count()
                mapped = [next(pos) if (i not in src) else None
                          for i in range(len(test))]
                rel_off = [mapped[o] for o in rel_off]

            return rel_off

        def Attributes(ns, key, offset):
            # Create an 'attribute string' for a tag (Element.attributes)
            attrs = ''

            if ns in attributes and key in attributes[ns]:
                attrs = attributes[ns][key].get(repr(offset), None)

                if attrs:
                    clean = lambda string: quote(escape(string, True),
                                                 " !#$'()*+,/:;=?@[/]^`{|}~")
                    attrs = ' '.join('{}="{}"'.format(Check(name), clean(value))
                                     for name, value in attrs.items())

            if len(offset) > 2:
                start = offset[0]
                rel_off = [ o - start for o in offset ]

                if maxunicode == 0xFFFF:
                    rel_off = NarrowPython(offset, rel_off, start)

                spans = ' '.join('{:d}:{:d}'.format(rel_off[i], rel_off[i + 1])
                                 for i in range(len(offset), step=2))
                attrs = '{} offsets="{}"'.format(attrs, spans)

            return attrs

        def GetBlock():
            # Return the start of the next block of elements and an iterator
            # over the Element tuples at that position
            block = next(ordered_blocks)
            return block[0][1], (
                Element(Name(tag[0], tag[1]), Attributes(*tag),
                        tag[2][-1] if len(tag[2]) > 1 else None)
                for tag in sorted(block, key=sort_key)
            )

        return GetBlock

    @staticmethod
    def __blockRepr(GetBlock, block, buffer, close_tags):
        # This is a private helper for markup representations of text.
        for element in block:
            e_str = Unicode.__strElement(close_tags, element)
            buffer.write(e_str)

        try:
            return GetBlock()
        except StopIteration:
            return -1, None

    @staticmethod
    def __strElement(close_tags:defaultdict, elem:namedtuple) -> str:
        # Create the opening elem string representation of *elem*, and
        # add the closing elem to the *close_tags* defaultdict(list).
        # This is a private helper for markup representations of text.
        if elem.end is not None:
            close_tags[elem.end].append('</{}>'.format(elem.name))
            return '<{}{}>'.format(elem.name, elem.attributes)
        else:  # empty elem
            return '<{}{} />'.format(elem.name, elem.attributes)

DEFAULT_WEIGHT = int(sqrt(maxsize))

def WeightedSort(tag):
    # This is the sort-key of elements in markup representations of text.
    return Unicode.ns_weights.get(tag[0], DEFAULT_WEIGHT) * \
           Unicode.key_weights.get(tag[1], DEFAULT_WEIGHT), tag
