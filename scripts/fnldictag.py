#!/usr/bin/env python3

"""dictag tags tokens with keys mapped to strings"""

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
from fnl.text.strtok import Tokenizer, WordTokenizer
from fnl.text.dictionary import Dictionary

__author__ = 'Florian Leitner'
__version__ = '1.0'


def load(instream, qualifier_list, sep='\t') -> iter:
    """
    Create an iterator over a dictionary input file.

    :param instream: from the dictionary file (symbol - count - qualifier - string)
    :param qualifier_list: ordered list of most important qualifiers
    :param sep: used in the dictionary file
    :return: an iterator over (key:str, count:int, qualifier:int, name:str) tuples
    """
    for line in instream:
        line = line.strip()

        if line:
            key, cite_count, qualifier, name = line.split(sep)

            # special case: boost "official_symbol" qualifiers by doubling their cite counts
            if qualifier == "official_symbol":
                cite_count *= 2

            yield key, name, 0 - int(cite_count), qualifier_list.index(qualifier)


def align(dictionary: Dictionary, tokenizer: Tokenizer, instreams):
    for input in instreams:
        for line in input:
            tokens = list(tokenizer.split(line.strip()))
            tags = list(dictionary.walk(tokens))
            lens = [max(len(tok), len(tag)) for tok, tag in zip(tokens, tags)]
            print(" ".join(("{:<%i}" % l).format(tok) for l, tok in zip(lens, tokens)))
            print(" ".join(("{:<%i}" % l).format(tag) for l, tag in zip(lens, tags)))
            print("--")


def normalize(dictionary: Dictionary, tokenizer: Tokenizer, instreams, sep="\t"):
    for input in instreams:
        for line in input:
            uid, text = line.strip().split(sep)
            tags = {tag[2:] for tag in dictionary.walk(tokenizer.split(text)) if tag != Dictionary.O}

            for tag in tags:
                print("{}{}{}".format(uid, sep, tag))


if __name__ == '__main__':
    import os
    import sys

    from argparse import ArgumentParser

    epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())
    parser = ArgumentParser(
        description=__doc__, epilog=epilog,
        prog=os.path.basename(sys.argv[0])
    )

    parser.set_defaults(loglevel=logging.WARNING)
    parser.add_argument(
        'dictionary', metavar='DICT', type=open,
        help='dictionary table with one key (1st col.), weight/count (2nd col.), '
        'qualifier name (3nd col.) and name/symbol string (4th col.) per row'
    )
    parser.add_argument(
        'qranks', metavar='QRANKS', type=open,
        help='ranking of dictionary qualifiers (3rd col.) to'
        'use for ambiguous hits'
    )
    parser.add_argument(
        'files', metavar='FILE', nargs='*', type=open,
        help='input file(s); if absent, read from <STDIN>'
    )
    parser.add_argument('--version', action='version', version=__version__)
    # parser.add_argument(
    #     '-c', '--column', default=0,
    #     help='token column in in the input file(s); (default: text)'
    # )
    # parser.add_argument(
    #     '-i', '--ignore', action='store_true',
    #     help='ignore letter case'
    # )
    parser.add_argument(
        '-s', '--separator', default="\t",
        help='dictionary (and token input file) separator (default: tab)'
    )
    parser.add_argument(
        '-n', '--normalize', action="store_true",
        help='entity link input text of the form "uid\\ttext\\n"'
    )
    parser.add_argument(
        '-q', '--quiet', action='store_const', const=logging.CRITICAL,
        dest='loglevel', help='critical log level only [warn]'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_const', const=logging.DEBUG,
        dest='loglevel', help='debug log level [warn]'
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.loglevel, format='%(asctime)s %(levelname)s: %(message)s'
    )

    method = normalize if args.normalize else align

    try:
        qualifier_list = [l.strip() for l in args.qranks]
        data_ = load(args.dictionary, qualifier_list, args.separator)
        tok_ = WordTokenizer(skipTags={'space'}, skipMorphs={'e'})
        dict_ = Dictionary(data_, tok_)

        if args.files:
            method(dict_, tok_, args.files)
        else:
            method(dict_, tok_, [sys.stdin])
    except:
        logging.exception("unexpected program error")
        sys.exit(1)

    sys.exit(0)
