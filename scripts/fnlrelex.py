#!/usr/bin/env python3

"""extract per-sentence combinations between two or more dictag entity types"""

from itertools import product

__author__ = 'Florian Leitner'
__version__ = '1.0'


def ExtractRelations(data):
	for pmid, sentences in data:
		for sid, sent in enumerate(sentences):
			label_sets = []

			for entities in sent:
				if len(label_sets) == 0:
					for _ in range(len(entities)):
						label_sets.append(set())

				for idx, label in enumerate(entities):
					if label.startswith('B-'):
						label_sets[idx].add(label[2:])

			for relation in product(*label_sets):
				yield pmid, sid, relation


def ReadParsingResult(file):
	pmid = 0
	current_pmid = 0
	sentences = []
	sent = []
	sid = None

	for line in file:
		line = line.strip()

		if line:
			data = line.split('\t')
			pmid = int(data[0])
			sent.append(data[7:])

			if sid is None:
				sid = data[1]
			else:
				assert sid == data[1]
		else:
			if pmid != 0 and pmid != current_pmid:
				yield current_pmid, sentences
				sentences = [sent]
				current_pmid = pmid
			else:
				sentences.append(sent)

			sent = []
			sid = None


if __name__ == '__main__':
	import os
	import sys

	from argparse import ArgumentParser

	epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())
	parser = ArgumentParser(
		description=__doc__, epilog=epilog,
		prog=os.path.basename(sys.argv[0])
	)

	parser.add_argument(
		'file', metavar='FILE', nargs='?', type=open,
		help='input file (dictag output); if absent, read from <STDIN>'
	)

	args = parser.parse_args()

	input_stream = args.file if args.file else sys.stdin

	for pmid, sid, rel in ExtractRelations(ReadParsingResult(input_stream)):
		print('%d\t%d\t%s' % (pmid, sid, '\t'.join(rel)))