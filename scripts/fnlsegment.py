#!/usr/bin/env python3
"""
Segement text [in a particular column] into sentences.

When splitting text in a column, the remaining columns are all printed, and
the column containing the text is split in two, one column enumerating the
sentences on a per-input-row basis, and the sentence itself.
"""

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import pickle
import os
import sys

from argparse import ArgumentParser
from nltk.tokenize.punkt import PunktSentenceTokenizer
from fnl.text.segment import SplitText, SplitTextInColumn

__author__ = 'Florian Leitner'
__version__ = '1.0.1'

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
        args.error('could not split the input text')
