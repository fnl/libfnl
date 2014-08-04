#!/usr/bin/env python3

"""extract per-sentence combinations between two or more dictag entity types"""
import inspect
import logging
from itertools import product, chain
from random import shuffle
from nltk.classify import maxent
from nltk.metrics import precision, recall, f_measure
from numpy import std
from fnl.nlp.sentence import SentenceParser

__author__ = 'Florian Leitner'
__version__ = '1.0'


def CoOccurrenceRelations(input_stream):
	"""
	If neither a model or ground truth file is provided, just extract all co-occurrences of
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
		logging.exception("feature generation code could not be parsed")
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
			yield uid, tuple(a.value for a in annotations), \
			      FeatureBuilder(sentence, *annotations)


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
		'trace': 3 if logging.getLogger().getEffectiveLevel() > logging.WARNING else 0,
		# megam only:
		'gaussian_prior_sigma': 1.0,
		# 'bernoulli': True,
		# 'explicit': False,
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

	def buildFeatureSets(self, instream) -> iter([(tuple, tuple, dict, bool)]):
		return self._wrapLabel(FeatureGenerator(instream, self.feature_code))

	def train(self, feature_sets):
		if self._kwd_args['encoding'] is None:
			feature_sets = list(feature_sets)

		return maxent.MaxentClassifier.train([(f, l) for u, r, f, l in feature_sets],
		                                     self.algorithm, **self._kwd_args)

	def _wrapLabel(self, feature_generator):
		for uid, relation, features in feature_generator:
			if uid in self.ground_truth:
				yield uid, relation, features, relation in self.ground_truth[uid]
			else:
				yield uid, relation, features, False


def GroundTruthParser(input_stream, column=2):
	for line in input_stream:
		line = line.strip()

		if line:
			items = tuple(line.split('\t'))
			yield items[:column], items[column:]


def CrossValidationSets(data_set, num_evaluations):
	num_instances = len(data_set)
	logging.info("%s %s instances", num_instances, data_set[0][-1])
	logging.info(data_set[0])
	logging.info(data_set[-1])
	sizes = num_instances // num_evaluations

	for i in range(num_evaluations):
		start = i * sizes
		end = (i + 1) * sizes if i != num_evaluations - 1 else num_instances
		yield chain(data_set[0:start], data_set[end:num_instances]), data_set[start:end]


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
		     'Sentence and as many Annotation instances as are required to form a '
		     'relationship and return a feature dictionary; required for model training, '
		     'evaluation, or classification; without a feature function definition, all '
		     'co-ocurrence relationships are extracted'
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
		'-c', '--cross-evaluations', metavar='N', action="store", type=int, default=1,
		help='do N-fold cross-evaluation (only in conjunction with a [ground] truth file)'
	)
	parser.add_argument(
		'--megam', metavar='PATH', action="store",
		help='use MegaM at PATH (instead of IIS) for training the MaxEnt classifier; on Mac '
		     'using Homebrew, MegaM will be at /usr/local/Cellar/megam/0.9.2/bin/megam'
	)
	parser.add_argument(
		'-q', '--quiet', action='store_const', const=logging.CRITICAL,
		dest='loglevel', help='critical log level only (default: warn)'
	)
	parser.add_argument(
		'-v', '--verbose', action='store_const', const=logging.INFO,
		dest='loglevel', help='info log level (default: warn)'
	)

	args = parser.parse_args()
	logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s',
	                    level=args.loglevel)
	sentences = SentenceParser(args.file if args.file else sys.stdin, ('MASK_A', 'MASK_B'))
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

	if truth and feature_function_code and (model_path or args.cross_evaluations > 1):
		trainer = ModelTrainer(truth, feature_function_code)

		if args.megam:
			trainer.useMegam(args.megam)

		if args.evaluate and model_path:
			with open(model_path, 'rb') as input_file:
				model = pickle.load(input_file)

			labeled_features = trainer.buildFeatureSets(sentences)

			# TODO
		else:
			if args.cross_evaluations > 1:
				sentences = list(sentences)
				shuffle(sentences)
				sentence_dict = dict(sentences)
				labeled_features = list(trainer.buildFeatureSets(sentences))
				pos = [i for i in labeled_features if i[-1]]
				neg = [i for i in labeled_features if not i[-1]]
				pos_sets_iter = CrossValidationSets(pos, args.cross_evaluations)
				neg_sets_iter = CrossValidationSets(neg, args.cross_evaluations)
				cv_size = len(labeled_features) / args.cross_evaluations
				results = {
					'precision': [],
				    'recall': [],
				    'f_measure': []
				}

				for split in range(args.cross_evaluations):
					pos_train, pos_eval = next(pos_sets_iter)
					neg_train, neg_eval = next(neg_sets_iter)
					model = trainer.train(chain(pos_train, neg_train))
					print("Evaluation Round", split + 1)
					predicted = set()
					pos_eval = list(pos_eval)
					pos_cases = len(pos_eval)
					assert pos_cases, "no TRUE annotations"
					annotated = set(range(pos_cases))
					show_fp, show_fn = True, True

					for i, (uid, rel, feats, label) in enumerate(chain(pos_eval, neg_eval)):
						if model.classify(feats):
							predicted.add(i)

							if show_fp and i >= pos_cases:
								print("FALSE POSITIVE", "<->".join(rel))
								print(' '.join(t.word for t in sentence_dict[uid].tokens))
								model.explain(feats)
								show_fp = False

						elif show_fn and i < pos_cases:
							print("FALSE NEGATIVE", "<->".join(rel))
							print(' '.join(t.word for t in sentence_dict[uid].tokens))
							model.explain(feats)
							show_fn = False

					print("       TP  %5d" % len(predicted & annotated))
					print("       FP  %5d" % len(predicted - annotated))
					print("       FN  %5d" % len(annotated - predicted))
					print("    total  %5d" % cv_size)

					for measure in (precision, recall, f_measure):
						result = measure(predicted, annotated)
						print("% 9s %5.01f%%" % (measure.__name__, result * 100))
						results[measure.__name__].append(result)

					print("\n")

				print("%d-fold Cross-Evaluation Results" % args.cross_evaluations)
				model.show_most_informative_features()

				for measure in ("precision", "recall", "f_measure"):
					mean = sum(results[measure]) / args.cross_evaluations
					sd = std(results[measure])
					print("% 9s %5.01f%% +/- %4.01f" % (measure, mean * 100, sd * 100))

				print("\n")

			if model_path:
				with open(args.model, 'wb') as output_file:
					model = trainer.train(trainer.buildFeatureSets(sentences))
					pickle.dump(model, output_file)
					model.show_most_informative_features()
	elif model_path and feature_function_code:
		with open(model_path, 'rb') as input_file:
			model = pickle.load(input_file)

		for sid, rel in DetectRelations(sentences, model, feature_function_code):
			print('%s\t%s' % ('\t'.join(sid), '\t'.join(rel)))
	else:
		for sid, rel in CoOccurrenceRelations(sentences):
			print('%s\t%s' % ('\t'.join(sid), '\t'.join(rel)))