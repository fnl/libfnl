"""
.. py:module:: fnl.nlp.genia.tagger
   :synopsis: A subprocess wrapper for the GENIA Tagger.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

import logging
from operator import itemgetter
import os
from subprocess import Popen, PIPE
from threading import Thread

GENIATAGGER_DIR = os.environ.get('GENIATAGGER_DIR', '/usr/local/share/geniatagger')
"""
The directory containing the ``geniatagger`` binary and ``morphdic`` directory,
defaulting to ``/usr/local/share/geniatagger``, or as set in the environment.
"""

GENIATAGGER = "geniatagger"
"""
The default path of the ``geniatagger``. If the GENIA Tagger is on the ``PATH``,
the name of the binary will do.
"""

class GeniaTagger(object):
    """
    A subprocess wrapper for the GENIA Tagger.
    """

    L = logging.getLogger("GeniaTagger")

    def __init__(self, binary:str=GENIATAGGER,
                 morphdic_dir:str=GENIATAGGER_DIR,
                 tokenize:bool=True):
        """
        :param binary: The path or name (if in ``$PATH``) of the geniatagger
                       binary.
        :param morphdic_dir: The directory where the morphdic directory is
                             located (ie., **not** including the ``morphdic``
                             directory itself).
        :param tokenize: If ``False``, geniatagger is run without
                         tokenization (ie., with the ``-nt`` flag).
        """
        if os.path.isabs(binary): GeniaTagger._checkPath(binary, os.X_OK)
        GeniaTagger._checkPath("{}/morphdic".format(morphdic_dir), os.R_OK)
        args = [binary] if tokenize else [binary, '-nt']
        self.L.debug("starting '%s'" % ' '.join(args))
        self.L.debug("in directory '%s'", morphdic_dir)
        self._proc = Popen(args, cwd=morphdic_dir,
                          stdin=PIPE, stdout=PIPE, stderr=PIPE)
        debug_msgs = Thread(target=GeniaTagger._logStderr,
                            args=(self.L, self._proc.stderr))
        debug_msgs.start()

    @staticmethod
    def _checkPath(path, acc_code):
        assert os.path.exists(path) and os.access(path, acc_code), \
        "invalid path %s" % path

    @staticmethod
    def _logStderr(logger, stderr):
        while True:
            line = stderr.readline().decode()
            if line: logger.debug("STDERR: %s", line.strip())
            else: break

    def __del__(self):
        self.L.debug("terminating")
        if hasattr(self, "_proc"): self._proc.terminate()

    def __iter__(self):
        return self

    def __next__(self):
        status = self._proc.poll()

        if status is not None:
            raise RuntimeError("geniatagger exited with %i" % status * -1)

        self.L.debug('reading token')
        line = self._proc.stdout.readline()
        self.L.debug('fetched token')
        line = line.decode().strip()
        if not line: raise StopIteration
        items = line.split('\t')
        self.L.debug('raw result: %s', items)
        return Token(*items)

    # To make this module compatible with Python 2:
    next = __next__

    def send(self, sentence:str):
        """
        Send a single *sentence* (w/o newline) to the tagger.
        """
        self.L.debug('sending sentence: "%s"', sentence)
        self._proc.stdin.write(sentence.encode())
        self._proc.stdin.write(b"\n")
        self._proc.stdin.flush()


class Token(tuple):
    """
    A named tuple data structure for GENIA tokens with some additional
    introspection methods about the token's tags (``is...``).

    Tokens have the following items and attributes:

    0. ``word`` - the actual token
    1. ``stem`` - the stemmed form of ``word``
    2. ``pos`` - the PoS-tag for this token
    3. ``chunk`` - the chunk-tag for this token
    4. ``entity`` - the entity-tag for this token
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
        Make a new :py:class:`.tagger.Token` object from a sequence or iterable.
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

    word = property(itemgetter(0))
    stem = property(itemgetter(1))
    pos = property(itemgetter(2))
    chunk = property(itemgetter(3))
    entity = property(itemgetter(4))
