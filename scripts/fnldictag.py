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
from unicodedata import category
from fnl.nlp.token import Token
from fnl.text.strtok import WordTokenizer
from fnl.text.dictionary import Dictionary
from fnl.nlp.genia.nersuite import NerSuite
from fnl.nlp.genia.tagger import GeniaTagger

__author__ = 'Florian Leitner'
__version__ = '1.0'


def align(dictionary, tokenizer, pos_tagger, ner_tagger, input_streams, sep="", nouns=False):
	"""Align the output of the tags below the tokens."""
	uid = []

	for input in input_streams:
		for text in input:
			if sep:
				*uid, text = text.strip().split(sep)

			logging.debug('aligning %s "%s"', sep.join(uid), text)
			tokens = list(tokenizer.split(text))

			try:
				tags, _ = _prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer, nouns)
			except RuntimeError as e:
				logging.exception('at UID %s', sep.join(uid))
				continue

			lens = [max(len(tok), len(tag)) for tok, tag in zip(tokens, tags)]

			if sep and uid:
				print(sep.join(uid))

			assert len(tokens) == len(tags), "alignemnt failed %i != %i; details: %s" % (len(tokens), len(tags), repr(list(zip(tokens, tags))))

			for src in (tokens, tags):
				print(" ".join(("{:<%i}" % l).format(t) for l, t in zip(lens, src)))

			print("--")


def tagging(dictionary, tokenizer, pos_tagger, ner_tagger, input_streams, sep="\t", nouns=False):
	"""Print columnar output of [text UID,] token data and tags; one token per line."""
	for input in input_streams:
		for line in input:
			*uid, text = line.strip().split(sep)
			logging.debug('tagging %s: "%s"', '-'.join(uid), text)
			tokens = list(tokenizer.split(text))

			try:
				tags, ner_tokens = _prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer, nouns)
			except RuntimeError as e:
				logging.exception('at UID %s', sep.join(uid))
				continue

			for tag, tok in zip(tags, ner_tokens):
				print("{}{}{}{}{}".format(sep.join(uid), sep if uid else "", sep.join(tok), sep, tag))

			print("")


def normalize(dictionary, tokenizer, pos_tagger, ner_tagger, input_streams, sep="\t", nouns=False):
	"""Print only [text UIDs and] tags."""
	for input in input_streams:
		for line in input:
			*uid, text = line.strip().split(sep)
			logging.debug('normalizing %s: "%s"', '-'.join(uid), text)
			tokens = list(tokenizer.split(text))

			try:
				tags, _ = _prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer, nouns)
			except RuntimeError as e:
				logging.exception('at UID %s', sep.join(uid))
				continue

			for tag in {tag[2:] for tag in tags if tag != Dictionary.O}:
				print("{}{}{}".format(sep.join(uid), sep if uid else "", tag))


def _prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer, nouns):
	dict_tags = list(dictionary.walk(tokens))
	pos_tagger.send(text)
	pos_tokens = list(pos_tagger)
	ner_tagger.send(pos_tokens)
	ner_tokens = list(ner_tagger)

	if len(ner_tokens) != len(tokens):
		ner_tokens = _alignTokens(ner_tokens, pos_tokens, tokens, tokenizer)

	assert len(dict_tags) == len(ner_tokens), "alignment error: %i != %i; details: %s" % (
		len(dict_tags), len(ner_tokens), repr(list(zip([t.word for t in ner_tokens], dict_tags)))
	)
	gene_tags = list(_matchNerAndDictionary(dict_tags, ner_tokens, nouns))
	assert len(gene_tags) == len(ner_tokens), "matching error: %i != %i; details: %s" % (
		len(gene_tags), len(ner_tokens), repr(list(zip([t.word for t in ner_tokens], gene_tags)))
	)
	return gene_tags, ner_tokens


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


def _alignTokens(ner_tokens, pos_tokens, tokens, tokenizer):
	"Return the aligned NER tokens (to the PoS tags and text tokens)."
	# TODO: make this method's code actually understandable...
	aligned_ner_tokens = []
	t_iter = iter(tokens)
	index = 0

	while index < len(ner_tokens):
		word = next(t_iter)
		ner_t = ner_tokens[index]

		while all(category(c) == "Pd" for c in ner_t.word) and index < len(ner_tokens):
			logging.debug("skipping punctuation dash '%s'", ner_t.word)
			index += 1
			ner_t = ner_tokens[index]

		if word == ner_t.word or word == '"':  # " is a special case (gets converted to `` or '' by GENIA)
			aligned_ner_tokens.append(ner_t)
		elif len(word) > len(ner_t.word):
			pos_words = [pos_tokens[index].word]
			logging.debug('word %s exceeds %s/%s', repr(word), pos_words[0], repr(ner_t.word))

			while word != ''.join(pos_words):
				try:
					index += 1
					pos_words.append(pos_tokens[index].word)
				except IndexError:
					logging.error('alignment of %i tokens "%s" - "%s" to word "%s" at %i failed in "%s" vs "%s"',
					              len(pos_words), pos_words[0], pos_words[-1], word, index, repr(tokens),
					              repr([t.word for t in pos_tokens]))
					raise RuntimeError("alignment failed")

			logging.debug('aligned %s to %s [%s]', repr(word), repr(pos_words), ner_t[-1])
			aligned_ner_tokens.append(Token(word, word, *ner_t[2:]))
		else:
			words = [word]
			pos_words = ''.join(tokenizer.split(pos_tokens[index].word))
			tmp = list(ner_t)
			logging.debug('token %s/%s exceeds %s', pos_words, repr(ner_t.word), repr(word))

			while ''.join(words) != pos_words:
				try:
					words.append(next(t_iter))
				except StopIteration:
					pos_word = pos_tokens[index].word
					logging.error('alignment of %i words "%s"-"%s" to %s/%s as "%s" at %i failed in "%s" vs "%s"',
					              len(words), word, words[-1], pos_word, ner_t.word,
					              ' '.join(tokenizer.split(pos_word)), index, repr(tokens),
					              repr([t.word for t in pos_tokens]))
					raise RuntimeError("alignment failed")

			logging.debug('aligned %s [%s] to %s', repr(pos_words), ner_t[-1], repr(words))

			for w in words:
				tmp[0] = w
				tmp[1] = w
				aligned_ner_tokens.append(Token(*tmp))

				for p in (3, 4):
					if tmp[p].startswith('B-'):
						tmp[p] = 'I' + tmp[p][1:]

		index += 1

	assert len(tokens) == len(aligned_ner_tokens), "%i != %i; details: %s" % (
		len(tokens), len(aligned_ner_tokens), repr(list(zip(tokens, [t.word for t in aligned_ner_tokens])))
	)
	return aligned_ner_tokens


def _matchNerAndDictionary(dict_tags, ner_tokens, nouns=False):
	opened = False
	assert len(dict_tags) == len(ner_tokens), "%i != %i; details: %s" % (len(dict_tags), len(ner_tokens), repr(list(zip([t.word for t in ner_tokens], dict_tags))))

	for token, dic in zip(ner_tokens, dict_tags):
		if dic != Dictionary.O:
			if token.entity != Dictionary.O:
				if dic[:2] == token.entity[:2]:
					yield dic
					opened = (dic[:2] == Dictionary.O)
				else:
					yield Dictionary.B % dic[2:]
					opened = True
			elif nouns and token.pos.startswith('NN'):
				if opened:
					yield Dictionary.I % dic[2:]
					opened = False
				else:
					yield Dictionary.B % dic[2:]
					opened = True
			else:
				raise RuntimeError("at token %s with tag %s in %s" % (token, dic, repr(list(zip([t.word for t in ner_tokens], dict_tags)))))
		else:
			yield Dictionary.O
			opened = False


if __name__ == '__main__':
	import os
	import sys

	ALIGNED = 1
	NORMALIZED = 2
	TABULAR = 3

	from argparse import ArgumentParser

	epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())
	parser = ArgumentParser(
		description=__doc__, epilog=epilog,
		prog=os.path.basename(sys.argv[0])
	)

	parser.set_defaults(loglevel=logging.WARNING)
	parser.set_defaults(output=ALIGNED)
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
		'--nouns', action="store_true",
		help='allow any noun to be tagged (default: only gene-NER tagged tokens)'
	)
	parser.add_argument(
		'-s', '--separator', default="\t",
		help='dictionary (and token input file) separator (default: tab)'
	)
	parser.add_argument(
		'-n', '--normalize', action="store_const", const=NORMALIZED,
		dest="output", help='output entity linked input text using text UIDs'
	)
	parser.add_argument(
		'-t', '--tabular', action="store_const", const=TABULAR,
		dest="output", help='output tabular, per-token IOB tagging results'
	)
	parser.add_argument(
		'-a', '--align', action="store_const", const=ALIGNED,
		dest="output", help='output tokens and tags aligned to each other (default)'
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
		raw_dict_data = load(args.dictionary, qualifier_list, args.separator)
		tokenizer = WordTokenizer(skipTags={'space'}, skipMorphs={'e'}) # skips Unicode Categories Zs and Pd
		dictionary = Dictionary(raw_dict_data, tokenizer)

		if args.files:
			method(dictionary, tokenizer, pos_tagger, ner_tagger, args.files, sep=args.separator, nouns=args.nouns)
		else:
			method(dictionary, tokenizer, pos_tagger, ner_tagger, [sys.stdin], sep=args.separator, nouns=args.nouns)

		del pos_tagger
		del ner_tagger
	except:
		logging.exception("unexpected program error")
		sys.exit(1)

	sys.exit(0)
