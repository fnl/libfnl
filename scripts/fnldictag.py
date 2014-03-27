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


def splitNerTokens(ner_words, pos_tokens, tokens, tokenizer):
    assert len(tokens) > len(ner_words)
    new_tokens = []
    t_iter = iter(tokens)

    for i, ner_t in enumerate(ner_words):
        word = next(t_iter)

        if word == ner_t.word:
            new_tokens.append(ner_t)
        else:
            words = [word]
            ner_words = list(tokenizer.split(pos_tokens[i].word))

            while words != ner_words:
                print(words, ner_words, pos_tokens[i].word, repr(ner_t))
                words.append(next(t_iter))

            tmp = list(ner_t)

            for i, w in enumerate(words):
                tmp[0] = w
                tmp[1] = w
                new_tokens.append(Token(*tmp))

                for p in (3, 4):
                    if tmp[p].startswith('B-'):
                        tmp[p] = 'I' + tmp[p][1:]

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
        for text in input:
            text = text.strip()
            tokens = list(tokenizer.split(text))
            tags = _prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer)
            lens = [max(len(tok), len(tag)) for tok, tag in zip(tokens, tags)]

            for src in (tokens, tags):
                print(" ".join(("{:<%i}" % l).format(t) for l, t in zip(lens, src)))

            print("--")


def normalize(dictionary, tokenizer, pos_tagger, ner_tagger, input_streams, sep="\t"):
    for input in input_streams:
        for line in input:
            uid, text = line.strip().split(sep)
            tokens = list(tokenizer.split(text))
            tags = _prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer)

            for tag in {tag[2:] for tag in tags if tag != Dictionary.O}:
                print("{}{}{}".format(uid, sep, tag))


def _prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer):
    dict_tags = list(dictionary.walk(tokens))
    pos_tagger.send(text)
    pos_tokens = list(pos_tagger)
    ner_tagger.send(pos_tokens)
    ner_tokens = list(ner_tagger)
    if len(ner_tokens) != len(tokens):
        ner_tokens = splitNerTokens(ner_tokens, pos_tokens, tokens, tokenizer)
    gene_tags = list(matchNerAndDictionary(dict_tags, ner_tokens))
    return gene_tags


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
