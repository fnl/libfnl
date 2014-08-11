"""
.. py:module:: fnl.nlp.genia.nersuite
   :synopsis: A subprocess wrapper for the NER Suite tagger.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

import logging
import os
from subprocess import Popen, PIPE, DEVNULL
from unidecode import unidecode

from fnl.text.token import Token

NERSUITE_TAGGER = "nersuite"
"""
The default path of the ``nersuite``. If the NER Suite tagger is on the ``PATH``,
the name of the binary will do.
"""


class NerSuite(object):
    """
    A subprocess wrapper for the NER Suite tagger.
    """

    L = logging.getLogger("NerSuite")

    def __init__(self, model, binary=NERSUITE_TAGGER):
        """
        :param model: The path to the model to use by the tagger.
        :param binary: The path or name (if in ``$PATH``) of the nersuite binary.
d        """
        if os.path.isabs(binary):
            NerSuite._checkPath(binary, os.X_OK)

        NerSuite._checkPath(model, os.R_OK)
        args = [binary, 'tag', '-m', model]
        self.L.debug("executing %s", ' '.join(args))
        self._proc = Popen(args, stdin=PIPE, stdout=PIPE, stderr=DEVNULL)
        # TODO: fix hang in readline() below when exiting
        # debug_msgs = Thread(target=NerSuite._logStderr,
        #                     args=(self.L, self._proc.stderr))
        # debug_msgs.start()

    @staticmethod
    def _checkPath(path, acc_code):
        assert os.path.exists(path) and os.access(path, acc_code), \
            "invalid path %s" % path

    @staticmethod
    def _logStderr(logger, stderr):
        while True:
            # TODO: thread hangs here after parent terminates...
            line = stderr.readline().decode()

            if line:
                logger.warning(line.strip())
            else:
                break

    def __del__(self):
        if hasattr(self, "_proc"):
            self.L.debug("ner tagger terminating")
            self._proc.terminate()

    def __iter__(self):
        return self

    def __next__(self):
        status = self._proc.poll()

        if status is not None:
            raise RuntimeError("nersuite exited with status %i" % status * -1)

        self.L.debug('reading token')
        # noinspection PyUnresolvedReferences
        line = self._proc.stdout.readline().decode('ASCII').strip()
        self.L.debug('fetched line "%s"', line)

        if not line:
            raise StopIteration

        items = line.split('\t')
        self.L.debug('raw result: %s', items)
        return Token(*items[2:])

    # To make this module compatible with Python 2:
    next = __next__

    def send(self, tokens):
        """
        Send a single sentence as a list of tokens to the tagger.

        **Important**: The NER Suite only is able to work with ASCII text!
        """
        self.L.debug('sending tokens for: "%s"', '" "'.join([t.word for t in tokens]))

        for t in tokens:
            self._proc.stdin.write("0\t{}\t".format(len(t.word)).encode('ASCII'))
            self._proc.stdin.write(unidecode('\t'.join(t[:-1])).encode('ASCII'))
            self._proc.stdin.write("\n".encode('ASCII'))

        self._proc.stdin.write("\n".encode('ASCII'))
        self._proc.stdin.flush()
