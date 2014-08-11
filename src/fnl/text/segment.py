"""
.. py:module:: fnl.text.segment
   :synopsis: Classes to generate features from token sequences and assign semantic annotations
   on them.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from fn.monad import optionable
from operator import itemgetter


class segment(tuple):

    """
    Segments of text make working with tokens and annotations (child segments) in that segment
    possible.

    Child segments can be added as "annotations" to existing segments. Sections that coincide with
    annotations can be *masked*, that is, instead of showing the acutal string, the namespace of
    the annotation is used. This is useful to generate features for classifiers that should not
    "learn" the actual words, but rather the presence of an entity, for example.
    """

    __slots__ = ()

    _optional = ('identifier', 'annotations')

    def __new__(cls, txt, *ns_off, **meta):
        if len(ns_off) == 0 and not isinstance(txt, str):
            txt, namespace, offset, meta = cls.__copy(txt)
        else:
            txt, namespace, offset, meta = cls.__make(txt, ns_off, meta)

        assert isinstance(txt, str)
        assert isinstance(namespace, str)
        meta = tuple(meta.get(key) for key in cls._optional)
        return tuple.__new__(cls, (txt, namespace, offset) + meta)

    @staticmethod
    def __make(txt, ns_off, meta):
        """Default constructor helper."""
        try:
            namespace = ns_off[0]
            offset = tuple(int(i) for i in ns_off[1])
        except IndexError:
            raise ValueError('namespace and/or offset undefined')

        if len(offset) == 0 or len(offset) != 1 and len(offset) % 2 != 0:
            raise ValueError('illegal offset %s' % repr(offset))

        for idx, key in enumerate(segment._optional):
            if len(ns_off) > idx + 2:
                meta[key] = ns_off[idx + 2]
            else:
                break

        return txt, namespace, offset, meta

    @staticmethod
    def __copy(txt):
        """Copy constructor helper."""
        meta = {}
        txt = tuple(txt)

        if len(txt) < 3 + len(segment._optional):
            raise ValueError('incorrect number of values: %i' % len(txt))

        for idx, key in enumerate(segment._optional):
            if txt[idx + 3] is not None:
                meta[key] = txt[idx + 3]

        off = tuple(txt[2])
        ns = txt[1]
        txt = txt[0]

        return txt, ns, off, meta

    text = property(itemgetter(0), doc="the text object containing this segment")
    namespace = property(itemgetter(1), doc="the namespace of this segment")
    offset = property(itemgetter(2), doc="the offset in the text")
    identifier = property(optionable(itemgetter(3)), doc="an identifier for this segment")
    annotations = property(optionable(itemgetter(4)), doc="child segments (if allowed)")

    ns = namespace
    """An alias for `namespace`."""
    id = identifier
    """An alias for `identifier`."""

    @property
    def begin(self) -> int:
        """Return the first offset index of the segment."""
        return self.offset[0]

    @property
    def end(self) -> int:
        """Return the last offset index of the segment."""
        return self.offset[-1]

    def __repr__(self) -> str:
        return 'segment(%s, %s%s)' % (
            self.namespace, ':'.join(str(i) for i in self.offset),
            ''.join([
                getattr(self, key).map(lambda val: ', %s=%r' % (key, val)).get_or('')
                for key in self._optional
            ])
        )

    def __str__(self) -> str:
        s = ['\\N' if i is None else str(i).replace('\t', '\\t') for i in self[1:]]
        s[1] = ':'.join(str(i) for i in self.offset)
        return '\t'.join(s)

    def Update(self, **kwds):
        """Return a new `token` by replacing the specified fields."""
        txt = kwds.get('text', self.text)
        namespace = kwds.get('namespace', self.namespace)
        offset = kwds.get('offset', self.offset)

        for key in self._optional:
            kwds[key] = kwds.get(key, getattr(self, key).get_or(None))

        return segment(txt, namespace, offset, **kwds)