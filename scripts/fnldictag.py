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
from fnl.nlp.token import Token
from fnl.text.strtok import WordTokenizer
from fnl.text.dictionary import Dictionary
from fnl.nlp.genia.nersuite import NerSuite
from fnl.nlp.genia.tagger import GeniaTagger

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


def splitNerTokens(ner_tokens, tokens):
    assert len(tokens) > len(ner_tokens)
    new_tokens = []
    t_iter = iter(tokens)

    for token in ner_tokens:
        t = next(t_iter)

        if t == token.word:
            new_tokens.append(token)
        else:
            word = [t]

            while ''.join(word) != token.word:
                word.append(next(t_iter))

            tmp = list(token)

            for t in word:
                tmp[0] = t
                tmp[1] = t
                new_tokens.append(Token(*tmp))

    assert len(tokens) == len(new_tokens)
    return new_tokens


def matchNerAndDictionary(dict_tags, ner_tokens):
    for i, token in enumerate(ner_tokens):
        if token.entity != Dictionary.O and dict_tags[i] != Dictionary.O:
            dic = dict_tags[i]

            if dic[:2] == token.entity[:2]:
                yield dic
            else:
                yield Dictionary.B % dic[2:]
        else:
            yield Dictionary.O


def align(dictionary, tokenizer, pos_tagger, ner_tagger, input_streams, **_):
    for input in input_streams:
        for line in input:
            line = line.strip()
            tokens = list(tokenizer.split(line))
            dict_tags = list(dictionary.walk(tokens))
            ner_tokens = list(ner_tagger.send(pos_tagger.send(line)))

            if len(ner_tokens) != len(tokens):
                ner_tokens = splitNerTokens(ner_tokens, tokens)

            gene_tags = list(matchNerAndDictionary(dict_tags, ner_tokens))
            lens = [max(len(tok), len(tag)) for tok, tag in zip(tokens, gene_tags)]

            for src in (tokens, gene_tags):
                print(" ".join(("{:<%i}" % l).format(t) for l, t in zip(lens, src)))

            print("--")


def normalize(dictionary, tokenizer, pos_tagger, ner_tagger, input_streams, sep="\t"):
    for input in input_streams:
        for line in input:
            uid, text = line.strip().split(sep)
            tokens = list(tokenizer.split(text))
            dict_tags = list(dictionary.walk(tokens))
            ner_tokens = list(ner_tagger.send(pos_tagger.send(line)))

            if len(ner_tokens) != len(tokens):
                ner_tokens = splitNerTokens(ner_tokens, tokens)

            tags = {tag[2:] for tag in matchNerAndDictionary(dict_tags, ner_tokens) if tag != Dictionary.O}

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
        'model', metavar='MODEL', help='file with the NER Suite model'
    )
    parser.add_argument(
        'files', metavar='FILE', nargs='*', type=open,
        help='input file(s); if absent, read from <STDIN>'
    )
    parser.add_argument('--version', action='version', version=__version__)
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
    pos_tagger = GeniaTagger()
    ner_tagger = NerSuite(args.model)

    try:
        qualifier_list = [l.strip() for l in args.qranks]
        raw_dict_data = load(args.dictionary, qualifier_list, args.separator)
        tokenizer = WordTokenizer(skipTags={'space'}, skipMorphs={'e'})
        dictionary = Dictionary(raw_dict_data, tokenizer)

        if args.files:
            method(dictionary, tokenizer, pos_tagger, ner_tagger, args.files, sep=args.separator)
        else:
            method(dictionary, tokenizer, pos_tagger, ner_tagger, [sys.stdin], sep=args.separator)
    except:
        logging.exception("unexpected program error")
        sys.exit(1)

    sys.exit(0)
