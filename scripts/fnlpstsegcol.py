#!/usr/bin/env python3
"""
Segement text in a particular column into sentences.
"""

import logging
import pickle

from nltk.tokenize.punkt import PunktSentenceTokenizer

__author__ = 'Florian Leitner'
__version__ = '1.0'


def main(stream, pst, col=2, sep='\t'):
    for text in stream:
        items = text.strip().split(sep)
        prefix = sep.join(items[:col-1])
        suffix = sep.join(items[col:])

        try:
            for idx, sentence in enumerate(pst.tokenize(items[col-1].strip())):
                print(sep.join((prefix, str(idx+1), sentence, suffix)))
        except IndexError:
            logging.critical('input has no column %s:\n%s', col, items)
            break


if __name__ == '__main__':
    import os
    import sys

    from argparse import ArgumentParser

    epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())
    parser = ArgumentParser(
        usage='%(prog)s [options] MODEL COL [FILE ...]',
        description=__doc__, epilog=epilog,
        prog=os.path.basename(sys.argv[0])
    )

    parser.set_defaults(loglevel=logging.WARNING)
    parser.add_argument(
        'model', metavar='MODEL',
        help='a PunktSegementTokenzier model file'
    )
    parser.add_argument(
        'column', metavar='COL', type=int,
        help='the column number where the text is found'
    )
    parser.add_argument(
        'files', metavar='FILE', nargs='*', type=open,
        help='TSV input file(s); if absent, read from <STDIN>'
    )
    parser.add_argument(
        '-s', '--separator', default='\t',
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

    if args.files:
        for infile in args.files:
            try:
                main(infile, pst, col=args.column, sep=args.separator)
            except:
                logging.exception("unexpected program error")
                sys.exit(1)
    else:
        try:
            main(sys.stdin, pst, col=args.column, sep=args.separator)
        except:
            logging.exception("unexpected program error")
            sys.exit(1)

    sys.exit(0)
