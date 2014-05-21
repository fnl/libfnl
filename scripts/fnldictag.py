#!/usr/bin/env python3

"""dictag tags tokens with keys mapped to strings in a dictionary"""

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
from unidecode import unidecode
from fnl.nlp.token import Token
from fnl.text.strtok import WordTokenizer
from fnl.text.dictionary import Dictionary
from fnl.nlp.genia.nersuite import NerSuite
from fnl.nlp.genia.tagger import GeniaTagger

__author__ = 'Florian Leitner'
__version__ = '1.0'

GREEK = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "omicron": "ο",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "upsilon": "υ",
    "ypsilon": "υ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "Alpha": "Α",
    "Beta": "Β",
    "Gamma": "Γ",
    "Delta": "Δ",
    "Epsilon": "Ε",
    "Zeta": "Ζ",
    "Eta": "Η",
    "Theta": "Θ",
    "Iota": "Ι",
    "Kappa": "Κ",
    "Lambda": "Λ",
    "Mu": "Μ",
    "Nu": "Ν",
    "Xi": "Ξ",
    "Omicron": "Ο",
    "Pi": "Π",
    "Rho": "Ρ",
    "Sigma": "Σ",
    "Tau": "Τ",
    "Upsilon": "Υ",
    "Ypsilon": "Υ",
    "Phi": "Φ",
    "Chi": "Χ",
    "Psi": "Ψ",
    "Omega": "Ω",
}

LATIN = {v: k for k, v in GREEK.items()}


def align(dictionary, tokenizer, pos_tagger, ner_tagger, input_streams, sep="", tag_all_nouns=False, expand_greek_letters=False):
	"""Align the output of the dictionary tags below the tokens."""
	uid = []

	for input in input_streams:
		for text in input:
			if sep:
				*uid, text = text.strip().split(sep)

			logging.debug('aligning %s "%s"', sep.join(uid), text)
			tokens = list(tokenizer.split(text))

			try:
				tags, _ = prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer, tag_all_nouns, expand_greek_letters)
			except RuntimeError as e:
				logging.exception('at UID %s', sep.join(uid))
				continue

			lens = [max(len(tok), len(tag)) for tok, tag in zip(tokens, tags)]

			if sep and uid:
				print(sep.join(uid))

			assert len(tokens) == len(tags), "alignemnt failed %i != %i; details: %s" % (
			    len(tokens), len(tags), repr(list(zip(tokens, tags)))
			)

			for src in (tokens, tags):
				print(" ".join(("{:<%i}" % l).format(t) for l, t in zip(lens, src)))

			print("--")


def tagging(dictionary, tokenizer, pos_tagger, ner_tagger, input_streams, sep="\t", tag_all_nouns=False, expand_greek_letters=False):
	"""Print columnar output of [text UID,] token data and tags; one token per line."""
	for input in input_streams:
		for line in input:
			*uid, text = line.strip().split(sep)
			logging.debug('tagging %s: "%s"', '-'.join(uid), text)
			tokens = list(tokenizer.split(text))

			try:
				tags, ner_tokens = prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer, tag_all_nouns, expand_greek_letters)
			except RuntimeError as e:
				logging.exception('at UID %s', sep.join(uid))
				continue

			for tag, tok in zip(tags, ner_tokens):
				print("{}{}{}{}{}".format(sep.join(uid), sep if uid else "", sep.join(tok), sep, tag))

			print("")


def normalize(dictionary, tokenizer, pos_tagger, ner_tagger, input_streams, sep="\t", tag_all_nouns=False, expand_greek_letters=False):
	"""Print only [text UIDs and] dictionary tags."""
	for input in input_streams:
		for line in input:
			*uid, text = line.strip().split(sep)
			logging.debug('normalizing %s: "%s"', '-'.join(uid), text)
			tokens = list(tokenizer.split(text))

			try:
				tags, _ = prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer, tag_all_nouns, expand_greek_letters)
			except RuntimeError as e:
				logging.exception('at UID %s', sep.join(uid))
				continue

			for tag in {tag[2:] for tag in tags if tag != Dictionary.O}:
				print("{}{}{}".format(sep.join(uid), sep if uid else "", tag))


def ungreek(token):
	if token in LATIN:
		return LATIN[token]
	else:
		return token


def prepare(dictionary, ner_tagger, pos_tagger, text, tokens, tokenizer, tag_all_nouns, expand_greek_letters):
	if expand_greek_letters:
		normalizations = list(dictionary.walk([ungreek(t) for t in tokens]))
	else:
		normalizations = list(dictionary.walk(tokens))

	pos_tagger.send(text)
	tags = list(pos_tagger)
	ner_tagger.send(tags)
	tags = list(ner_tagger)

	if len(tags) != len(tokens):
		tags = alignTokens(tags, tokens, tokenizer)

	assert len(normalizations) == len(tags), "alignment error: %i != %i; details: %s" % (
		len(normalizations), len(tags), repr(list(zip([t.word for t in tags], normalizations)))
	)
	normalizations = list(matchNerAndDictionary(normalizations, tags, tag_all_nouns))
	assert len(normalizations) == len(tags), "matching error: %i != %i; details: %s" % (
		len(normalizations), len(tags), repr(list(zip([t.word for t in tags], normalizations)))
	)
	return normalizations, tags


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


def alignTokens(tags, tokens, tokenizer):
	"Return the aligned NER tokens (to the PoS tags and text tokens)."
	# TODO: make this method's code actually understandable...
	aligned_tags = []
	t_iter = iter(tokens)
	index = 0

	while index < len(tags):
		word = next(t_iter)
		ascii = unidecode(word)
		tag = tags[index]

		while all(category(c) == "Pd" for c in tag.word) and index < len(tags):
			logging.debug("dropping punctuation dash tag '%s' [%s]", tag.word, tag[-1])
			index += 1
			tag = tags[index]

		if ascii == tag.word:
			if tag.word == word:
				aligned_tags.append(tag)
			else:
				aligned_tags.append(Token(word, *tag[1:]))
		elif word == '"' and tag.word in ("``", "''"):
			# " is a special case (gets converted to `` or '' by GENIA)
			aligned_tags.append(Token('"', *tag[1:]))
		elif len(word) > len(tag.word):
			logging.debug('word %s exceeds tag word %s', repr(word), repr(tag.word))
			tag_words = [tag.word]
			matches = lambda: ascii == ''.join(tag_words)

			while not matches() and sum(map(len, tag_words)) < len(word):
				index += 1
				tag_words.append(tags[index].word)

			if matches():
				logging.debug("dropping tags '%s' and adding %s [%s]",
							  ' '.join(tag_words), repr(word), tag[-1])
				aligned_tags.append(Token(word, ascii, *tag[2:]))
			else:
				logging.error('alignment of tokens %s to word "%s" at %i failed in "%s" vs "%s"',
				              repr(tag_words), word, repr(tokens), index, repr([t.word for t in tags]))
				raise RuntimeError("alignment failed")
		elif len(word) < len(tag.word):
			logging.debug('tag word %s exceeds word %s', repr(tag.word), repr(word))
			tmp = list(tag)
			words = [word]
			asciis = [ascii]
			tag_word = ''.join(tokenizer.split(tag.word))
			matches = lambda: ''.join(asciis) == tag_word

			while not matches() and sum(map(len, words)) < len(tag_word):
				words.append(next(t_iter))
				asciis.append(unidecode(words[-1]))

			if matches():
				logging.debug("dropping tag %s [%s] for words '%s'",
				  			  repr(tag.word), tag[-1], ' '.join(words))
				for w, a in zip(words, asciis):
					tmp[0] = w
					tmp[1] = a
					logging.debug("adding tag %s [%s]", repr(w), tmp[-1])
					aligned_tags.append(Token(*tmp))

					for p in (3, 4):
						if tmp[p].startswith('B-'):
							tmp[p] = 'I' + tmp[p][1:]
			else:
				logging.error('alignment of words %s to token "%s" as "%s" at %i failed in "%s" vs "%s"',
				              repr(words), tag.word, tag_word, index, repr(tokens), repr([t.word for t in tags]))
				raise RuntimeError("alignment failed")
		else:
			logging.error('alignment of "%s" and %s failed', word, repr(tag))
			raise RuntimeError('alignment failed')

		index += 1

	assert len(tokens) == len(aligned_tags) and \
	       tokens == [tag.word for tag in aligned_tags], "%i != %i; details: %s" % (
			   len(tokens), len(aligned_tags), repr([(w, t) for w, t in zip(tokens, [t.word for t in aligned_tags]) if w != t])
	)
	return aligned_tags


def matchNerAndDictionary(dict_tags, ner_tokens, tag_all_nouns=False):
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
			elif tag_all_nouns and token.pos.startswith('NN'):
				if opened:
					yield Dictionary.I % dic[2:]
					opened = False
				else:
					yield Dictionary.B % dic[2:]
					opened = True
			else:
				logging.debug("droping normalization of %s with %s", token, dic)
				yield Dictionary.O
				opened = False
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
		help='allow any noun to be tagged (default: only NER tagged tokens)'
	)
	parser.add_argument(
		'--ungreek', action="store_true",
		help='expand Greek letters to Latin names'
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
			method(dictionary, tokenizer, pos_tagger, ner_tagger, args.files, sep=args.separator, tag_all_nouns=args.nouns, expand_greek_letters=args.ungreek)
		else:
			method(dictionary, tokenizer, pos_tagger, ner_tagger, [sys.stdin], sep=args.separator, tag_all_nouns=args.nouns, expand_greek_letters=args.ungreek)

		del pos_tagger
		del ner_tagger
	except:
		logging.exception("unexpected program error")
		sys.exit(1)

	sys.exit(0)
