"""
.. py:module:: fnl.nlp.segment
   :synopsis: functions to segment text using the NLTK PunktSentenceTokenizer.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
import re

__author__ = "Florian Leitner"

AUTHOR_PATTERN_TAIL = re.compile(r',(?: [A-Z]\.)+$')
AUTHOR_PATTERN_HEAD = re.compile(
    r'^(?:[A-Z]\.(?:, [A-Za-z \.\-]+)*|\([12]\d{3}\))'
)


def JoinAuthorSplits(sentences):
    """
    Join sentences that were split wrongly in the middle of lists of author
    names, returning the "joined" list of sentences.
    """
    if any(AUTHOR_PATTERN_TAIL.search(s) for s in sentences):
        joined = []

        for s in sentences:
            if joined and \
               AUTHOR_PATTERN_TAIL.search(joined[-1]) and \
               AUTHOR_PATTERN_HEAD.search(s):
                joined[-1] += ' ' + s
            else:
                joined.append(s)

        return joined
    else:
        return sentences


def SplitText(stream, pst):
    """
    Split the text on the input `stream` into sentences.

    The splitted input is printed one sentence per line.

    :param stream: iterable stream of text
    :param pst: a PunktSentenceTokenizer model instance
    """
    for text in stream:
        for s in JoinAuthorSplits(pst.tokenize(text.strip())):
            print(s)


def SplitTextInColumn(stream, pst, column, sep='\t'):
    """
    Split text found in a particular `column` on the input `stream`.

    The splitted rows are printed one sentence each, and an extra column is
    added before the text column, enumerating each sentence per input row.

    :param stream: iterable stream of text
    :param pst: a PunktSentenceTokenizer model instance
    :param column: the column to split (1-based offset)
    :param sep: (optional) column separator string to use
    """
    for text in stream:
        items = text.strip().split(sep)
        prefix = sep.join(items[:column-1])
        suffix = sep.join(items[column:])

        try:
            sentences = JoinAuthorSplits(pst.tokenize(items[column-1].strip()))
        except IndexError:
            logging.critical('input has no column %s:\n%s', column, items)
            break

        for idx, sent in enumerate(sentences):
            print(sep.join((prefix, str(idx+1), sent, suffix)))
