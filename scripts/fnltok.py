#!/usr/bin/env python3
"""
tokenize input text
"""
from argparse import ArgumentParser
import logging
import os
import sys

from fnl.text.strtok import SpaceTokenizer, WordTokenizer, AlnumTokenizer

__author__ = 'Florian Leitner'
__version__ = '0.0.1'


def map(text_iterator, tokenizer):
    for text in text_iterator:
        for token in tokenizer.tag(text):
            print(*token, sep='\t')


epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())
parser = ArgumentParser(
    usage='%(prog)s [options] [FILE ...]',
    description=__doc__, epilog=epilog,
    prog=os.path.basename(sys.argv[0])
)

parser.set_defaults(loglevel=logging.WARNING)
parser.set_defaults(tokenizer=AlnumTokenizer)
parser.add_argument('files', metavar='FILE', nargs='*', type=open,
                    help='input file(s); if absent, read from <STDIN>')
parser.add_argument('--space', action='store_const', const=SpaceTokenizer,
                    dest='tokenizer', help='use space tokenizer [alnum]')
parser.add_argument('--word', action='store_const', const=WordTokenizer,
                    dest='tokenizer', help='user word tokenizer [alnum]')
parser.add_argument('--version', action='version', version=__version__)
parser.add_argument('--error', action='store_const', const=logging.ERROR,
                    dest='loglevel', help='error log level only [warn]')
parser.add_argument('--info', action='store_const', const=logging.INFO,
                    dest='loglevel', help='info log level [warn]')
parser.add_argument('--debug', action='store_const', const=logging.DEBUG,
                    dest='loglevel', help='debug log level [warn]')
parser.add_argument('--logfile', metavar='FILE',
                    help='log to file instead of <STDERR>')

args = parser.parse_args()
files = args.files if args.files else [sys.stdin]

logging.basicConfig(
    filename=args.logfile, level=args.loglevel,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s'
)

for input_stream in files:
    try:
        map(input_stream, args.tokenizer())
    except:
        logging.exception("unexpected program error")
        parser.error("unexpected program error")
