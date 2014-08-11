"""
.. py:module:: fnl.text.token
   :synopsis: A tuple structure to hold token metadata.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from operator import itemgetter, methodcaller
from fn import _
from fn.monad import optionable


class token(tuple):

    """
    A data structure for tokens.

    Provides some additional introspection methods about the token's tags (``...Is...``).

    Tokens have the following attributes:

    1. ``text`` - the text object containing this token
    1. ``namespace`` - the namespace for this token (e.g., the URI of the tokenizer used)
    1. ``offset`` - the offset of the token in its containing string (e.g., ``(10, 15)``)
    1. ``norm`` - a normalized form of the token (i.e., its stem or lemma)
    1. ``ortho`` - a regular representation of the token's orthographic features
    1. ``pos`` - the PoS tag (e.g., 'NNS')
    1. ``chunk`` - the chunk tag in BIO-notation (e.g., 'B-NP')
    1. ``entity`` - the entity tag in BIO-notation (e.g., 'I-gene')
    1. ``word`` - the actual token string
    1. ``begin`` - the begin postion (inclusive) of this token in the text
    1. ``end`` - the end postion (exclusive) of this token in the text

    The first three attributes (text, ns, and offset) are required, the last three properties
    (word, begin, end) are inferred. All other attributes are optional **tags** on this token and
    are returned as `Option` values.
    """

    __slots__ = ()

    _optional = ('norm', 'ortho', 'pos', 'chunk', 'entity')

    def __new__(cls, txt, *ns_off, **tags):
        """
        Create a new token.

        A new token can either be created from a single object that can be evaluate to a tuple
        of length of the number of required attributes and optional tags or by providing the
        required attributes plus any optional tags (as keywords or in order).
        """
        if len(ns_off) == 0  and not isinstance(txt, str):
            txt, namespace, offset, tags = cls.__copy(txt)
        else:
            txt, namespace, offset, tags = cls.__make(txt, ns_off, tags)

        assert isinstance(txt, str)
        assert isinstance(namespace, str)
        tags = tuple(tags.get(key) for key in cls._optional)
        return tuple.__new__(cls, (txt, namespace, offset) + tags)

    @staticmethod
    def __make(txt, ns_off, tags):
        """Default constructor helper."""
        try:
            namespace = ns_off[0]
            begin, end = ns_off[1]
            offset = (int(begin), int(end))
        except IndexError:
            raise ValueError('namespace and/or offset undefined')

        for idx, key in enumerate(token._optional):
            if len(ns_off) > idx + 2:
                tags[key] = ns_off[idx + 2]
            else:
                break

        return txt, namespace, offset, tags

    @staticmethod
    def __copy(txt):
        """Copy constructor helper."""
        tags = {}
        txt = tuple(txt)

        if len(txt) < 3 + len(token._optional):
            raise ValueError('incorrect number of values: %i' % len(txt))

        for idx, key in enumerate(token._optional):
            if txt[idx + 3] is not None:
                tags[key] = txt[idx + 3]

        begin, end = tuple(txt[2])
        off = (int(begin), int(end))
        ns = txt[1]
        txt = txt[0]

        return txt, ns, off, tags

    text = property(itemgetter(0), doc="the text object containing this token")
    namespace = property(itemgetter(1), doc="the namespace of this token")
    offset = property(itemgetter(2), doc="the (begin, end) offset in the text")
    norm = property(optionable(itemgetter(3)), doc="the normalized token tag")
    ortho = property(optionable(itemgetter(4)), doc="the orthographic descriptor tag")
    pos = property(optionable(itemgetter(5)), doc="the part-of-speech tag")
    chunk = property(optionable(itemgetter(6)), doc="the BIO phrase tag")
    entity = property(optionable(itemgetter(7)), doc="the BIO NER tag")

    ns = namespace
    """An alias for `namespace`."""

    @property
    def begin(self) -> int:
        """Return the begin index (inclusive) of the token."""
        return self.offset[0]

    @property
    def end(self) -> int:
        """Return the end index (exclusive) of the token."""
        return self.offset[1]

    @property
    def word(self) -> str:
        """Return the underlying token itself."""
        return self.text[self.begin:self.end]

    def __repr__(self) -> str:
        return 'token(%s, %r%s)' % (
            self.namespace, self.word,
            ''.join([
                getattr(self, key).map(lambda val: ', %s=%r' % (key, val)).get_or('')
                for key in self._optional
            ])
        )

    def __str__(self) -> str:
        s = ['\\N' if i is None else str(i).replace('\t', '\\t') for i in self[1:]]
        s[1] = '%i:%i' % self.offset
        return '\t'.join(s)

    def Update(self, **kwds):
        """Return a new `token` by replacing the specified fields."""
        txt = kwds.get('text', self.text)
        namespace = kwds.get('namespace', self.namespace)
        offset = kwds.get('offset', self.offset)

        for key in self._optional:
            kwds[key] = kwds.get(key, getattr(self, key).get_or(None))

        return token(txt, namespace, offset, **kwds)

    @staticmethod
    def _IsBegin(tag) -> bool:
        return tag.map(methodcaller('startswith', 'B-')).get_or(False)

    @staticmethod
    def _IsInside(tag) -> bool:
        return tag.map(methodcaller('startswith', 'I-')).get_or(False)

    @staticmethod
    def _IsOutside(tag) -> bool:
        return tag.map(_ == 'O').get_or(False)

    def PosIs(self, value) -> bool:
        return self.pos.map(_ == value).get_or(value is None)

    def PosStartswith(self, value) -> bool:
        return self.pos.map(methodcaller('startswith', value)).get_or(False)

    def ChunkIsOutside(self) -> bool:
        return token._IsOutside(self.chunk)

    def ChunkIsBegin(self) -> bool:
        return token._IsBegin(self.chunk)

    def ChunkIsInside(self) -> bool:
        return token._IsInside(self.chunk)

    def ChunkIs(self, value) -> bool:
        return self.chunk.map(lambda c: c[2:] == value).get_or(False)

    def EntityIsOutside(self) -> bool:
        return token._IsOutside(self.entity)

    def EntityIsBegin(self) -> bool:
        return token._IsBegin(self.entity)

    def EntityIsInside(self) -> bool:
        return token._IsInside(self.entity)

    def EntityIs(self, value) -> bool:
        return self.entity.map(lambda e: e[2:] == value).get_or(False)
