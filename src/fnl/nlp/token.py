"""
.. py:module:: fnl.nlp.token
   :synopsis: A simple class to hold tokens and their metadata.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

from operator import itemgetter

# noinspection PyPropertyAccess
class Token(tuple):
    """
    A named tuple data structure for tokens with some additional
    introspection methods about the token's tags (``is...``).

    Tokens have the following items and attributes:

    0. ``word`` - the actual token
    1. ``stem`` - the stemmed form of ``word``
    2. ``pos`` - the PoS tag for this token
    3. ``chunk`` - the chunk tag for this token
    4. ``entity`` - the entity tag for this token
    """

    __slots__ = ()

    _fields = ('word', 'stem', 'pos', 'chunk', 'entity')

    #noinspection PyInitNewSignature
    def __new__(cls, word, stem, pos, chunk, entity):
        return tuple.__new__(cls, (word, stem, pos, chunk, entity))

    def __repr__(self):
        return 'Token(word=%r, stem=%r, pos=%r, chunk=%r, entity=%r)' % self

    #noinspection PyInitNewSignature,PyMethodOverriding
    def __getnewargs__(self):
        return tuple(self)

    @classmethod
    def make(cls, iterable, new=tuple.__new__, len=len):
        """
        Make a new :py:class:`fnl.nlp.token.Token` object from a sequence or iterable.
        """
        result = new(cls, iterable)

        if len(result) != 5:
            raise TypeError('Expected 5 arguments, got %d' % len(result))

        return result

    def asDict(self) -> dict:
        """
        Return a `dict` that maps field names to their values.
        """
        return {
            'word': self[0], 'stem': self[1], 'pos': self[2],
            'chunk': self[3], 'entity': self[4]
        }

    def replace(self, **kwds):
        """
        Return a new :py:class:`.tagger.Token` replacing specified fields with new values.
        """
        result = self.make(map(
            kwds.pop, ('word', 'stem', 'pos', 'chunk', 'entity'), self
        ))

        if kwds:
            raise ValueError('Got unexpected field names: %r' % kwds.keys())

        return result

    word = property(itemgetter(0), doc="get the token string")
    stem = property(itemgetter(1), doc="get the stemmed or lemmatized string")
    pos = property(itemgetter(2), doc="get the PoS tag")
    chunk = property(itemgetter(3), doc="get the chunk tag")
    entity = property(itemgetter(4), doc="get the entity tag")

    # Introspection Helpers

    # chunks

    def isUnknownChunk(self) -> bool:
        return self.chunk == 'O'

    def isNounPStart(self) -> bool:
        return self.chunk == 'B-NP'

    def isVerbPStart(self) -> bool:
        return self.chunk == 'B-VP'

    def isPreposPStart(self) -> bool:
        return self.chunk == 'B-PP'

    def isAdjectivePStart(self) -> bool:
        return self.chunk == 'B-ADJP'

    def isAdverbPStart(self) -> bool:
        return self.chunk == 'B-ADVP'

    def isInNounP(self) -> bool:
        return self.chunk == 'I-NP'

    def isInVerbP(self) -> bool:
        return self.chunk == 'I-VP'

    def isInPreposP(self) -> bool:
        return self.chunk == 'I-PP'

    def isInAdjectiveP(self) -> bool:
        return self.chunk == 'I-ADJP'

    def isInAdverbP(self) -> bool:
        return self.chunk == 'I-ADVP'

    # entities

    def isUnknownEntity(self) -> bool:
        return self.entity == 'O'

    def isProteinStart(self) -> bool:
        return self.entity == 'B-protein'

    def isInProtein(self) -> bool:
        return self.entity == 'I-protein'

    def isCellLineStart(self) -> bool:
        return self.entity == 'B-cell_line'

    def isInCellLine(self) -> bool:
        return self.entity == 'I-cell_line'

    def isCellTypeStart(self) -> bool:
        return self.entity == 'B-cell_type'

    def isInCellType(self) -> bool:
        return self.entity == 'I-cell_type'
