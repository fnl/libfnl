#!/usr/bin/env python3

"""extract per-sentence combinations between two or more dictag entity types"""
import inspect

import logging
from itertools import product
from nltk.classify import maxent
from fnl.nlp.sentence import SentenceParser

__author__ = 'Florian Leitner'
__version__ = '1.0'


def CoocurrenceRelations(input_stream):
	"""
	If neither a model or ground truth file is provided, just extract all co-ocurrences of
	the input entities.

	:param input_stream: a `fnl.nlp.sentence.SentenceParser` generator object
	:return: `uid, relation` where relation is formed of each unique per-type entity with a
	         a B label in the sentence.
	"""
	for uid, sentence in input_stream:
		for annotations in YieldRelations(sentence):
			yield uid, tuple(a.value for a in annotations)


def YieldRelations(sentence):
	if len(sentence.annotations) > 1:
		done = set()

		for annotations in product(*sentence.annotations.values()):
			if annotations not in done:
				yield annotations
				done.add(annotations)


def FeatureGenerator(input_stream, feature_generation_code):
	variables = {}

	try:
		exec(feature_generation_code, None, variables)
	except Exception as e:
		logging.exception("feature generation code could not be executed")
		return

	for name, obj in variables.items():
		if callable(obj):
			spec = inspect.getargspec(obj)

			if len(spec.args) > 2:
				FeatureBuilder = obj
				break
	else:
		raise RuntimeError('no feature extraction function found')

	for uid, sentence in input_stream:
		for annotations in YieldRelations(sentence):
			yield uid, annotations, FeatureBuilder(sentence, *annotations)



def DetectRelations(input_stream, classifier, feature_generation_code):
	"""
	Given a "dic-tagged" input stream and a trained model, extract predicted relations per
	sentence.

	:param input_stream: a `fnl.nlp.sentence.SentenceParser` generator object
	:param classifier:
	:return:
	"""
	for uid, relation, features in FeatureGenerator(input_stream, feature_generation_code):
		if classifier.classify(features):
			yield uid, relation


class ModelTrainer:

	def __init__(self, truth, feature_generation_code, algorithm='IIS', **kwargs):
		self.ground_truth = truth
		self.feature_code = feature_generation_code
		self.algorithm = algorithm
		self._kwd_args = {
		    'count_cutoff': 0,
		    'encoding': None,
		    'labels': None,
		    'trace': 3,
		    # megam only:
		    'gaussian_prior_sigma': 1.0,
			# 'bernoulli': True,
		    # 'explicit': True,
		}
		self._kwd_args.update(kwargs)

	def useMegam(self, path):
		from nltk.classify import config_megam
		config_megam(path)
		self.algorithm = 'megam'

	def minObservations(self, count):
		"The minimum `count` of observations before a feature is used."
		assert int(count) >= 0, "negative count"
		self._kwd_args['count_cutoff'] = int(count)

	def setLabels(self, labels):
		"Set the list of `labels`."
		labels = list(labels)
		assert len(labels) > 0, "non-empty label list"
		assert self._kwd_args['encoding'] is None, "illegal setup: encoding already defined"
		self._kwd_args['labels'] = labels

	def defineEncoding(self, encoding):
		"Set the feature encoding mechanism."
		assert self._kwd_args['labels'] is None, "illegal setup: labels already defined"
		self._kwd_args['encoding'] = encoding

	def setGaussianPrior(self, sigma):
		"For MegaM only: `lambda = 1.0/sigma**2`."
		self._kwd_args['gaussian_prior_sigma'] = float(sigma)

	def setTrace(self, level):
		"Set the trace output level."
		level = int(level)
		assert level >= 0, "negative trace"
		self._kwd_args['trace'] = level

	def train(self, instream):
		feature_set = self._wrapLabel(FeatureGenerator(instream, self.feature_code))

		if self._kwd_args['encoding'] is None:
			feature_set = list(feature_set)

		return maxent.MaxentClassifier.train(feature_set, self.algorithm, **self._kwd_args)

	def _wrapLabel(self, feature_generator):
		for uid, relation, features in feature_generator:
			if uid in self.ground_truth:
				yield features, relation in self.ground_truth[uid]
			else:
				yield features, False


def GroundTruthParser(input_stream, column=2):
	for line in input_stream:
		line = line.strip()

		if line:
			items = tuple(line.split('\t'))
			yield items[:column], items[:column]


if __name__ == '__main__':
	import os
	import sys
	import pickle

	from argparse import ArgumentParser

	epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())
	parser = ArgumentParser(
		description=__doc__, epilog=epilog,
		prog=os.path.basename(sys.argv[0])
	)

	parser.set_defaults(loglevel=logging.WARNING)
	parser.add_argument(
		'file', metavar='FILE', nargs='?', type=open,
		help='input file (dictag output); if absent, read from <STDIN>'
	)
	parser.add_argument(
		'-f', '--feature-function', metavar='FILE', type=open,
	    help='a function to generate a MaxEnt feature dictionary: The function should take a '
	         'Sentence and as many Annotation instances as are required to form a relationship '
	         'and return a feature dictionary; required for model training, evaluation, or '
	         'classification; without a feature function definition, all co-ocurrence '
	         'relationships are extracted'
	)
	parser.add_argument(
		'-m', '--model', metavar='FILE',
	    help='path to the pickled model file; without a ground truth, implies classification '
	         'on the input file; with a ground truth, implies model training and '
	         'defines the location where the trained model file will be stored'
	)
	parser.add_argument(
		'-t', '--truth', metavar='FILE', type=open,
	    help='ground truth: per (doc_id, s_idx) relationships; '
	         'only required for model training and/or classifier evaluation'
	)
	parser.add_argument(
		'-e', '--evaluate', action="store_true",
		help='evaluate (only used in conjunction with a [ground] truth file and a model file)'
	)
	parser.add_argument(
		'-c', '--cross-evaluate', metavar='N', action="store", type=int,
		help='do N-fold cross-evaluation (only used in conjunction with a [ground] truth file)'
	)
	parser.add_argument(
		'--megam', metavar='PATH', action="store",
		help='use MegaM at PATH (instead of IIS) for training the MaxEnt classifier; on Mac using '
		     'Homebrew, MegaM will be at /usr/local/Cellar/megam/0.9.2/bin/megam'
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

	parser = SentenceParser(args.file if args.file else sys.stdin, ('MASK_A', 'MASK_B'))
	truth = None
	feature_function_code = None
	model_path = None

	if args.truth:
		truth = {}

		for key, value in GroundTruthParser(args.truth):
			if key in truth:
				truth[key].add(value)
			else:
				truth[key] = {value}

	if args.feature_function:
		feature_function_code = args.feature_function.read()

	if args.model:
		model_path = args.model

	if truth and feature_function_code and (model_path or args.evaluate or args.cross_evaluate):
		if args.evaluate:
			# TODO
			pass
		else:
			trainer = ModelTrainer(truth, feature_function_code)

			if args.megam:
				trainer.useMegam(args.megam)

			if args.cross_evaluate:
				# TODO
				pass

			if model_path:
				with open(args.model, 'wb') as output_file:
					model = trainer.train(parser)
					pickle.dump(model, output_file)
					model.show_most_informative_features()
	elif model_path and feature_function_code:
		with open(args.model, 'rb') as input_file:
			model = pickle.load(input_file)

		for sid, rel in DetectRelations(parser, model, feature_function_code):
			print('%s\t%s' % ('\t'.join(sid), '\t'.join(rel)))
	else:
		for sid, rel in CoocurrenceRelations(parser):
			print('%s\t%s' % ('\t'.join(sid), '\t'.join(rel)))