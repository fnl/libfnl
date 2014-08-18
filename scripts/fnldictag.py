#!/usr/bin/env python3

"""shallow parsing and dictionary linking of entities [and nouns]"""

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
from fnl.nlp.analysis import TextAnalytics
from fnl.nlp.genia.nersuite import NerSuite
from fnl.nlp.genia.tagger import GeniaTagger
from fnl.nlp.dictionary import Dictionary
from fnl.nlp.strtok import WordTokenizer


__author__ = 'Florian Leitner'
__version__ = '1.0'


def align(dictionaries, tokenizer, pos_tagger, ner_tagger, input_streams, sep="", **flags):
    """Print the aligned dictionary tags below the tokens."""
    uid = []
    worker = TextAnalytics(tokenizer, pos_tagger, **flags)
    worker.addNerTagger(ner_tagger)

    for d in dictionaries:
        worker.addDictionary(d)

    for input in input_streams:
        for text in input:
            if sep:
                *uid, text = text.strip().split(sep)

            logging.debug('aligning %s "%s"', sep.join(uid), text)

            try:
                tokens, _, dict_tags = worker.analyze(text)
            except RuntimeError:
                logging.exception('at UID %s', sep.join(uid))
                continue

            lens = [max(len(tok), max(len(t) for t in tags)) for tok, *tags in
                    zip(tokens, *dict_tags)]

            if sep and uid:
                print(sep.join(uid))

            print(" ".join(("{:<%i}" % l).format(t) for l, t in zip(lens, tokens)))

            for tags in dict_tags:
                print(" ".join(("{:<%i}" % l).format(t) for l, t in zip(lens, tags)))

            print("--")


def tagging(dictionaries, tokenizer, pos_tagger, ner_tagger, input_streams, sep="\t", **flags):
    """Print columnar output of [text UID,] token data and entity tags; one token per line."""
    worker = TextAnalytics(tokenizer, pos_tagger, **flags)
    worker.addNerTagger(ner_tagger)

    for d in dictionaries:
        worker.addDictionary(d)

    for input in input_streams:
        for line in input:
            *uid, text = line.strip().split(sep)
            logging.debug('tagging %s: "%s"', '-'.join(uid), text)

            try:
                _, ner_tokens, dict_tags = worker.analyze(text)
            except RuntimeError:
                logging.exception('at UID %s', sep.join(uid))
                continue

            for idx in range(len(ner_tokens[0])):
                token = ner_tokens[0][idx]
                tags = [t[idx].entity for t in ner_tokens[1:]]
                tags.extend(d[idx] for d in dict_tags)
                print("{}{}{}{}{}".format(sep.join(uid), sep if uid else "", sep.join(token),
                                          sep if tags else "", sep.join(tags)))

            print("")


def normalize(dictionaries, tokenizer, pos_tagger, ner_tagger, input_streams, sep="\t", **flags):
    """Print only [text UIDs and] dictionary tags."""
    worker = TextAnalytics(tokenizer, pos_tagger, **flags)
    worker.addNerTagger(ner_tagger)

    for d in dictionaries:
        worker.addDictionary(d)

    for input in input_streams:
        for line in input:
            *uid, text = line.strip().split(sep)
            logging.debug('normalizing %s: "%s"', '-'.join(uid), text)

            try:
                _, _, dict_tags = worker.analyze(text)
            except RuntimeError:
                logging.exception('at UID %s', sep.join(uid))
                continue

            for tags in dict_tags:
                for tag in {tag[2:] for tag in tags if tag != Dictionary.O}:
                    print("{}{}{}".format(sep.join(uid), sep if uid else "", tag))


def dictionaryReader(instream, qualifier_list, sep='\t') -> iter:
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


if __name__ == '__main__':
    import os
    import sys

    from argparse import ArgumentParser


    ALIGNED = 1
    NORMALIZED = 2
    TABULAR = 3

    epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())
    parser = ArgumentParser(
        description=__doc__, epilog=epilog,
        prog=os.path.basename(sys.argv[0])
    )

    parser.set_defaults(loglevel=logging.WARNING)
    parser.set_defaults(output=TABULAR)
    parser.add_argument(
        'qranks', metavar='QRANKS', type=open,
        help='ranking of dictionary qualifiers (3rd col.) to'
             'use for ambiguous hits'
    )
    parser.add_argument(
        'model', metavar='MODEL', help='file with a NER Suite model'
    )
    parser.add_argument(
        'files', metavar='FILE', nargs='*', type=open,
        help='input file(s); if absent, read from <STDIN>'
    )
    parser.add_argument(
        '-d', '--dictionary', metavar='DICT', type=open, action='append',
        help='a dictionary table with a key (col 1), weight/count (2), '
             'qualifier name (3) and name/symbol string (4) per row; '
             'use repeatedly for each dictionary (entity type)'
    )
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        '--nouns', action="count",
        help='allow any noun to be tagged (default: only NER tagged tokens); '
             'has to be repeated once for each dictionary (in same order)'
    )
    parser.add_argument(
        '--greek', action="store_true",
        help='do not regularize Greek letters to Latin names; '
             'has to be repeated once for each dictionary (in same order)'
    )
    parser.add_argument(
        '-s', '--separator', default="\t",
        help='separator used in input files (default: tab)'
    )
    parser.add_argument(
        '-n', '--normalize', action="store_const", const=NORMALIZED,
        dest="output", help='output entity linked input text using text UIDs'
    )
    parser.add_argument(
        '-t', '--tabular', action="store_const", const=TABULAR,
        dest="output", help='output tabular, per-token IOB tagging results (default)'
    )
    parser.add_argument(
        '-a', '--align', action="store_const", const=ALIGNED,
        dest="output", help='output tokens and tags aligned to each other'
    )
    parser.add_argument(
        '-q', '--quiet', action='store_const', const=logging.CRITICAL,
        dest='loglevel', help='critical log level only (default: warn)'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_const', const=logging.DEBUG,
        dest='loglevel', help='debug log level (default: warn)'
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.loglevel, format='%(asctime)s %(levelname)s: %(message)s'
    )

    if args.output == NORMALIZED:
        method = normalize
    elif args.output == TABULAR:
        method = tagging
    elif args.output == ALIGNED:
        method = align
    else:
        parser.error("unknown output option " + args.output)
        method = lambda *args: None

    try:
        pos_tagger = GeniaTagger()
        ner_tagger = NerSuite(args.model)
        qualifier_list = [l.strip() for l in args.qranks]
        raw_dict_data = [dictionaryReader(d, qualifier_list, args.separator)
                         for d in args.dictionary]
        # a tokenizer that skips Unicode Categories Zs and Pd:
        tokenizer = WordTokenizer(skipTags={'space'}, skipOrthos={'e'})
        dictionaries = [Dictionary(stream, tokenizer) for stream in raw_dict_data]
        logging.info("initialized %s dictionaries", len(dictionaries))
        lst = [dictionaries, tokenizer, pos_tagger, ner_tagger]
        kwds = dict(sep=args.separator,
                    tag_all_nouns=args.nouns,
                    use_greek_letters=args.greek)

        if args.files:
            lst.append(args.files)
        else:
            lst.append([sys.stdin])

        method(*lst, **kwds)

        del ner_tagger
        del pos_tagger
    except:
        logging.exception("unexpected program error")
        sys.exit(1)

    sys.exit(0)
