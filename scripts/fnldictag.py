#!/usr/bin/env python3

"""detect dictionary entries in text"""

import logging
import re

__author__ = 'Florian Leitner'
__version__ = '1.0'

ALNUM = re.compile(r'[\-\w ]*\d[ \w\-]*')
NUM = re.compile(r'(\d+)')
SEP = re.compile(r'[ \-_]')
STOPWORDS = frozenset({
    'An',
    'I',
    'In',
    'The',
    'To',
    'an',
    'and',
    'be',
    'have',
    'in',
    'not',
    'of',
    'that',
    'the',
    'to',
})


def CaseInsensitiveTokenizer(string):
    return tuple(
        token.lower() for word in SEP.split(string) for
        token in NUM.split(word) if token
    )


def CaseSensitiveTokenizer(string):
    return tuple(
        token for word in SEP.split(string) for
        token in NUM.split(word) if token
    )


def Invert(dictionary):
    inv = {}

    for key, values in dictionary.items():
        for name in values:
            inv.setdefault(''.join(name), []).append(key)

    return inv


class Dictionary:

    def __init__(self, mappings, ignore_case=False):
        self.tokenizer = CaseInsensitiveTokenizer if ignore_case else \
            CaseSensitiveTokenizer
        self.dictionary = mappings
        self.normal_dict = {
            k: tuple(self.tokenizer(n) for n in v) for k, v in mappings.items()
        }
        self.reverse_dict = Invert(self.normal_dict)
        logging.debug(
            'created a dictionary with %s keys and %s names',
            len(mappings), len(self.reverse_dict)
        )

    @staticmethod
    def load(file, ignore_case=False, sep='\t'):
        mapping = {}

        with open(file) as instream:
            for line in instream:
                names = line.strip().split(sep)

                if names:
                    key = names.pop(0)

                    if key in mapping:
                        logging.warning('duplicate key "%s" on line:\n%s',
                                        key, line.strip())

                    mapping[key] = names

        return Dictionary(mapping, ignore_case)

    def save(self, file, sep='\t'):
        with open(file, mode='wt') as outstream:
            for key, names in self.dictionary.items():
                print('{}{}{}'.format(key, sep, sep.join(names)),
                      file=outstream)

    def buildRegex(self, ignore_case=False):
        all_names = sorted(list({
            r'[ \-_]?'.join(re.escape(token) for token in name) for
            values in self.normal_dict.values() for name in values
        }))
        regex = r'|'.join(r'\b{}\b'.format(n) for n in all_names)
        return re.compile(regex, flags=re.I if ignore_case else 0)

    def getNames(self, key, default=None):
        return self.dictionary.get(key, default)

    def getKeys(self, name, default=None):
        normal_name = ''.join(self.tokenizer(name))
        keys = self.reverse_dict.get(normal_name, default)

        if keys is default:
            logging.warning("no keys for %s", normal_name)

        return keys


def main(dictionary, *streams, ignore_case=False):
    regex = dictionary.buildRegex(ignore_case)
    hits, counts = 0, 0

    for input in streams:
        for line in input:
            matches = set(
                regex.findall(line)
            )
            matches -= STOPWORDS

            if matches:
                mappings = {
                    '{}: "{}"'.format(key, name)
                    for name in matches for key in dictionary.getKeys(name)
                }
                counts += len(mappings)
                hits += len(matches)
                print('{}\t{}'.format(line[:-1], ', '.join(mappings)))

    logging.info('detect %s names mapping to %s keys', hits, counts)


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
        'dictionary', metavar='DICT',
        help='dictionary table with one key (1st col.) '
        'and a list of names (remaining columns) per row'
    )
    parser.add_argument(
        'files', metavar='FILE', nargs='*', type=open,
        help='input file(s); if absent, read from <STDIN>'
    )
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        '-i', '--ignore', action='store_true',
        help='letter case'
    )
    parser.add_argument(
        '-s', '--sep', default="\t",
        help='dictionary value separator string (default: tab)'
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

    try:
        dict_ = Dictionary.load(args.dictionary, args.ignore, args.sep)

        if args.files:
            main(dict_, *args.files,
                 ignore_case=args.ignore)
        else:
            main(dict_, sys.stdin,
                 ignore_case=args.ignore)
    except:
        logging.exception("unexpected program error")
        sys.exit(1)

    sys.exit(0)
