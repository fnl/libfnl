#!/usr/bin/env python3
"""
Segement text [in a particular column] into sentences.

When splitting text in a column, the remaining columns are all printed, and
the column containing the text is split in two, one column enumerating the
sentences on a per-input-row basis, and the sentence itself.
"""

import logging
import pickle
import re

from nltk.tokenize.punkt import PunktSentenceTokenizer

__author__ = 'Florian Leitner'
__version__ = '1.0'

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


if __name__ == '__main__':
    import os
    import sys

    from argparse import ArgumentParser

    epilog = 'system (de-facto) encoding: {}'.format(sys.getdefaultencoding())
    parser = ArgumentParser(
        usage='%(prog)s [options] MODEL [FILE ...]',
        description=__doc__, epilog=epilog,
        prog=os.path.basename(sys.argv[0])
    )

    parser.set_defaults(loglevel=logging.WARNING)
    parser.add_argument(
        'model', metavar='MODEL',
        help='a PunktSegementTokenzier model file'
    )
    parser.add_argument(
        'files', metavar='FILE', nargs='*', type=open,
        help='TSV input file(s); if absent, read from <STDIN>'
    )
    parser.add_argument(
        '-c', '--column', metavar='COL', type=int,
        help='the (1-based) column number where the text is found'
    )
    parser.add_argument(
        '-s', '--separator', metavar='SEP', default='\t',
        help='field separator [\\t]'
    )
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        '-v', '--verbose', action='store_const', const=logging.INFO,
        dest='loglevel', help='INFO log level [WARN]'
    )
    parser.add_argument(
        '-q', '--quiet', action='store_const', const=logging.ERROR,
        dest='loglevel', help='ERROR log level [WARN]'
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=args.loglevel,
        format='%(asctime)s %(levelname)s: %(message)s'
    )

    try:
        model = pickle.load(open(args.model, 'rb'))
        pst = PunktSentenceTokenizer(model)
    except:
        logging.exception('failed to unpickle %s', args.model)
        args.error('could not load model')

    streams = args.files if args.files else (sys.stdin,)

    for input in streams:
        try:
            if args.column is None:
                SplitText(input, pst)
            else:
                SplitTextInColumn(input, pst, args.column,
                                  sep=args.separator)
        except:
            logging.exception("unexpected program error")
            sys.exit(1)

    sys.exit(0)
