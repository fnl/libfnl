#!/usr/bin/env python3

"""extract per-sentence combinations between two or more dictag entity types"""
from collections import defaultdict
import inspect
import logging
import os
import pickle
import sys
from argparse import ArgumentParser
from itertools import product

import numpy
from matplotlib import pyplot
from sklearn.cross_validation import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score, roc_curve, auc, \
    precision_recall_curve, average_precision_score
from sklearn.naive_bayes import BernoulliNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from fnl.text.sentence import SentenceParser


__author__ = 'Florian Leitner'
__version__ = '1.0'


class Data:

    def __init__(self, feature_generator, ground_truth=None, sparse=True):
        self.feature_names = None
        self.labels = None
        self.extractor = DictVectorizer(sparse=sparse)
        self._feature_generator = feature_generator
        self._features = None
        self._raw_features = None
        self._relations = None
        self._uids = None

        if ground_truth is not None:
            for uid in self.uids:
                if uid in ground_truth:
                    logging.info('example truth for %s: %s', uid, ground_truth[uid])
                    break

            logging.info('ground truth contains %s true annotations',
                         sum(len(v) for v in ground_truth.values()))
            self.labels = numpy.zeros(self.n_instances, numpy.bool)

            for idx, (uid, rel) in enumerate(zip(self.uids, self.relations)):
                if uid in ground_truth and rel in ground_truth[uid]:
                    self.labels[idx] = True


    @property
    def uids(self):
        if self._uids is None:
            # noinspection PyCallingNonCallable
            for uid, _, _ in self.__generate():
                yield uid
        else:
            # noinspection PyTypeChecker
            for uid in self._uids:
                yield uid

    @property
    def relations(self):
        if self._relations is None:
            # noinspection PyCallingNonCallable
            for _, relation, _ in self.__generate():
                yield relation
        else:
            # noinspection PyTypeChecker
            for relation in self._relations:
                yield relation

    @property
    def raw_features(self):
        if self._raw_features is None:
            # noinspection PyCallingNonCallable
            for _, _, raw_feature in self.__generate():
                yield raw_feature
        else:
            # noinspection PyTypeChecker
            for raw_feature in self._raw_features:
                yield raw_feature

    @property
    def features(self):
        if self._features is None:
            if hasattr(self.extractor, 'feature_names_'):
                self.transform()
            else:
                self.fit_transform()

        return self._features

    @property
    def n_features(self):
        '''The number of features.'''
        return self.features.shape[1]

    @property
    def n_instances(self):
        '''The (total) number of instances.'''
        return self.features.shape[0]

    @property
    def n_labels(self):
        '''The (total) number of instances.'''
        if self.labels is not None:
            return self.labels.shape[0]
        else:
            return -1

    @property
    def n_positive(self):
        '''Number of positives instances.'''
        if self.labels is not None:
            return self.labels.sum()
        else:
            return -1

    def __generate(self):
        uids = []
        raw_features = []
        relations = []

        for uid, relation, raw_feature in self._feature_generator:
            uids.append(uid)
            relations.append(relation)
            raw_features.append(raw_feature)
            yield uid, relation, raw_feature

        self._uids = uids
        self._raw_features = raw_features
        self._relations = relations
        logging.info('loaded %s relations (instances)', len(uids))
        self.__generate = None  # safeguard: generate once and only once

    def fit_transform(self, features=None):
        if features is None:
            self._features = self.extractor.fit_transform(self.raw_features)
            self.feature_names = numpy.asarray(self.extractor.get_feature_names())
        else:
            return self.extractor.fit_transform(features)

    def transform(self, features=None):
        if features is None:
            self._features = self.extractor.transform(self.raw_features)
        else:
            return self.extractor.transform(features)


def CoOccurrenceRelations(input_stream, masks):
    """
    If neither a model or ground truth file is provided, just extract all co-occurrences of
    the input entities.

    :param input_stream: a `fnl.nlp.sentence.SentenceParser` generator object
    :return: `uid, relation` where relation is formed of each unique per-type entity with a
             a B label in the sentence.
    """
    for uid, sentence in input_stream:
        for annotations in YieldRelations(sentence, masks):
            yield uid, tuple(a.value for a in annotations)


def YieldRelations(sentence, masks):
    if len(sentence.annotations) > 1:
        done = set()

        ordered_annotations = [sentence.annotations[m] for m in masks]

        for ann in product(*ordered_annotations):
            if ann not in done:
                yield ann
                done.add(ann)


def FeatureGenerator(input_stream, feature_generation_code, masks):
    variables = {}

    try:
        exec(feature_generation_code, None, variables)
    except Exception as e:
        logging.exception('feature generation code could not be parsed')
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
        for annotations in YieldRelations(sentence, masks):
            yield uid, tuple(a.value for a in annotations), \
                FeatureBuilder(sentence, *annotations)


def DeduplicationIndex(uids, relations, probabilities):
    """
    Return a Boolean array for all elements in the given arrays,
    indicating the position of the entry for one uid and relation
    with the max. probability score.
    """
    assert len(uids) == len(probabilities)
    current_uid = None
    groups = defaultdict(list)
    keep = numpy.zeros(probabilities.shape, numpy.bool)

    for idx, (uid, relation) in enumerate(zip(map(tuple, uids), map(tuple, relations))):
        if uid == current_uid:
            groups[relation].append(idx)
        else:
            for rel, grp in groups.items():
                max_p = max(probabilities[grp])

                for i in grp:
                    if probabilities[i] == max_p:
                        keep[i] = True
                        break
                else:
                    raise RuntimeError('max_p of %s for %s not found' % (rel, uid))

            groups = defaultdict(list)
            current_uid = uid

    num_items = len(keep)
    logging.info("removing %s duplicates out of %s results", num_items - sum(keep), num_items)
    return keep


def DetectRelations(data, classifier):
    # TODO: should duplicate (uid, relation) pairs be removed from this stream, too?
    for uid, relation, features in zip(data.uids, data.relations, data.raw_features):
        prediction = classifier.predict([features])

        if prediction[0]:
            yield uid, relation


def GroundTruthParser(input_stream, id_columns=2):
    for line in input_stream:
        line = line.strip()

        if line:
            items = tuple(line.split('\t'))
            yield items[:id_columns], items[id_columns:]


def LogBestFeatures(classifier, data):
    # feature lists
    feature_list = (classifier.feature_importances_
                    if hasattr(classifier, 'feature_importances_') else
                    classifier.coef_)
    if feature_list.shape[0] == 1:
        feature_list = feature_list[0]
    best = numpy.argsort(feature_list)[-10:]
    logging.info('10 best features: "{0}"'.format(
        '", "'.join(data.feature_names[best]),
    ))


def CrossEvaluation(data, n_folds=5, plot=True):
    roc_plot, pr_plot = None, None

    # Do k-fold, stratified CV on the given data and report the results
    cross_evaluation = StratifiedKFold(data.labels, n_folds, shuffle=True)

    # F-score setup
    zeros = lambda: numpy.zeros(n_folds, numpy.float)
    uids = numpy.array(list(data.uids), numpy.object)
    relations = numpy.array(list(data.relations), numpy.object)
    scores = [
        ('Precision', precision_score, zeros()),
        ('Recall   ', recall_score, zeros()),
        ('F1-Score ', f1_score, zeros()),
    ]

    if plot:
        roc_plot = pyplot.figure(1).add_subplot(111)
        LayoutPlot()
        pr_plot = pyplot.figure(2).add_subplot(111)
        LayoutPlot()

    # ROC setup
    mean_tpr = 0.0
    mean_fpr = numpy.linspace(0, 1, 100)

    # PR setup
    all_labels = numpy.zeros([])
    all_probs = numpy.zeros([])
    idx = 0

    for i, (train, test) in enumerate(cross_evaluation):
        logging.info('running cross-evaulation round %s', i + 1)
        classifier.fit(data.features[train], data.labels[train])
        predictions = classifier.predict(data.features[test])

        if hasattr(classifier, 'decision_function'):
            probs = classifier.decision_function(data.features[test])
        else:
            probs = classifier.predict_proba(data.features[test])[:, 1]

        # remove duplicate results for the same relation,
        # keeping the most probable prediction only
        keep = DeduplicationIndex(uids[test], relations[test], probs)
        labels = data.labels[test][keep]
        probs = probs[keep]
        predictions = predictions[keep]

        # for ROC curve
        fpr, tpr, thresholds = roc_curve(labels, probs)
        mean_tpr += numpy.interp(mean_fpr, fpr, tpr)
        mean_tpr[0] = 0.0
        roc_auc = auc(fpr, tpr)
        roc_msg = 'ROC fold %d (area = %0.2f)' % (i + 1, roc_auc)
        logging.info(roc_msg)

        # for PR curve
        next_idx = idx + len(probs)
        all_labels = numpy.append(all_labels, labels)
        all_probs = numpy.append(all_probs, probs)
        idx = next_idx
        precision, recall, _ = precision_recall_curve(labels, probs)
        avrg_p = average_precision_score(labels, probs)
        pr_msg = 'PR curve %d (area = %0.2f)' % (i + 1, avrg_p)
        logging.info(pr_msg)

        if plot:
            roc_plot.plot(fpr, tpr, lw=1, label=roc_msg)
            pr_plot.plot(recall, precision, label=pr_msg)

        # for F-score
        for _, fun, results in scores:
            results[i] = fun(labels, predictions)

        LogBestFeatures(classifier, data)

    # ROC curve plot
    mean_tpr /= len(cross_evaluation)
    mean_tpr[-1] = 1.0
    mean_auc = auc(mean_fpr, mean_tpr)
    roc_msg = 'Mean ROC fold (area = %0.2f)' % mean_auc
    logging.info(roc_msg)

    # PR curve plot
    precision, recall, _ = precision_recall_curve(all_labels, all_probs)
    avrg_p = average_precision_score(all_labels, all_probs, average="micro")
    pr_msg = 'Micro PR curve (area = %0.2f)' % avrg_p
    logging.info(pr_msg)

    # show F-score
    for name, _, results in scores:
        print(name, '{:>2.1f} +/- {:.2f}'.format(results.mean() * 100, results.std() * 200))

    if plot:
        roc_plot.plot(mean_fpr, mean_tpr, 'k--', label=roc_msg, lw=2)
        pyplot.figure(1)
        ROCPlot()
        pr_plot.plot(recall, precision, 'k--', label=pr_msg, lw=2)
        pyplot.figure(2)
        pyplot.xlabel('Recall')
        pyplot.ylabel('Precision')
        pyplot.title('Precision Recall Curve')
        pyplot.legend(loc='lower left')
        pyplot.show()

def Evaluate(data, predictions, probabilities, plot=True):
    logging.info('evaluating the predictions')
    # Remove duplicate results for the same (UID, relation) pair,
    # keeping the entry with the max. probability only
    ddidx = DeduplicationIndex(data.uids, data.relations, probabilities)
    scores = []
    labels = data.labels[ddidx]
    predictions = predictions[ddidx]
    scores.append(('Precision', precision_score(labels, predictions)))
    scores.append(('Recall   ', recall_score(labels, predictions)))
    scores.append(('F1-Score ', f1_score(labels, predictions)))

    # show F-score
    for name, value in scores:
        print('{} {:>2.1f}'.format(name, value * 100))

    if plot:
        pyplot.figure()
        LayoutPlot()
        fpr, tpr, thresholds = roc_curve(data.labels, probabilities)
        roc_auc = auc(fpr, tpr)
        pyplot.plot(fpr, tpr, label='ROC curve (area = %0.2f)' % roc_auc)
        ROCPlot()
        pyplot.show()

def ROCPlot():
    pyplot.plot([0, 1], [0, 1], 'k--', color=(0.6, 0.6, 0.6), label='Random')
    pyplot.xlabel('False Positive Rate')
    pyplot.ylabel('True Positive Rate')
    pyplot.title('Receiver Operating Characteristic')
    pyplot.legend(loc='lower right')


def LayoutPlot():
    pyplot.xlim([-.05, 1.])
    pyplot.ylim([0., 1.05])


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
    help='a function to generate a feature dictionary: '
         '``def ffun(s:Sentence, *a:Annotation) -> dict`` The function takes a '
         'Sentence and as many Annotation instances as are required to form a '
         'relationship and return a feature dictionary of key:str, value:float pairs; '
         'required for working with models; without a feature function definition, '
         'co-ocurrence relationships are extracted (and no classifier is used)'
)
parser.add_argument(
    '-m', '--model', metavar='FILE',
    help='path to/for the pickled model file; without a ground truth, implies '
         'running classification on the input; with a ground truth, implies model '
         'training and defines the location where the trained model will be stored; '
         'requires a feature function'
)
parser.add_argument(
    '-t', '--truth', metavar='FILE', type=open,
    help='ground truth: per (doc_id, s_idx) relationships; '
         'only required for model training and/or classifier evaluation'
)
DENSE = ['svm', 'rf']
parser.add_argument(
    '-c', '--classifier', choices=['maxent', 'svm', 'naivebayes', 'rf'],
    help='the classifier to use (only required for training and/or evaluation); '
         'requires a ground truth file and a feature function'
)
parser.add_argument(
    '-p', '--plot', action='store_true',
    help='create evaluation plots'
)
parser.add_argument(
    '-e', '--evaluate', action='store_true',
    help='evaluate (only in conjunction a truth file and a trained model)'
)
parser.add_argument(
    '-x', '--cross-evaluations', metavar='N', action='store', type=int, default=1,
    help='do N-fold cross-evaluation (only in conjunction with a classifier)'
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

try:
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=args.loglevel)
    input = args.file if args.file else sys.stdin
    logging.info('reading data from %s', input.name)
    # TODO: add a commandline argument to define the relationship entities
    entities = ('FACTOR', 'TARGET')
    sentences = SentenceParser(input, entities)
    ground_truth = None
    classifier = None
    data = None
    model = None

    if args.truth:
        ground_truth = {}

        for key, value in GroundTruthParser(args.truth):
            if key in ground_truth:
                ground_truth[key].add(value)
            else:
                ground_truth[key] = {value}
    elif args.classifier:
        parser.error('classifier chosen, but no ground truth given')

    if args.feature_function:
        fg = FeatureGenerator(sentences, args.feature_function.read(), entities)
        data = Data(fg, ground_truth, sparse=not (args.classifier and args.classifier in DENSE))
        logging.info('data transformed to %s features', data.n_features)

        if args.truth:
            true_annotations = sum(len(v) for v in ground_truth.values())
            logging.info('data.labels has %s positive instances', data.n_positive)
            assert true_annotations <= data.n_positive
    elif args.model:
        parser.error('model file path, but no feature function given')

    if args.classifier:
        if not args.feature_function:
            parser.error('classifier chosen, but no feature function given')
        elif args.classifier == 'naivebayes':
            classifier = BernoulliNB(fit_prior=False, class_prior=(0.01, 0.09))
        elif args.classifier == 'rf':
            classifier = RandomForestClassifier(bootstrap=False, n_jobs=-1,
                                                verbose=(args.loglevel == logging.DEBUG))
        elif args.classifier == 'maxent':
            # params = dict(fit_intercept=False)  # high-recall
            params = dict(C=10.)  # high-precision
            classifier = LogisticRegression(class_weight='auto', **params)
        elif args.classifier == 'svm':
            params = dict(C=.1, loss='l1')  # high-recall
            # params = dict()  # high-precision
            classifier = LinearSVC(verbose=(args.loglevel == logging.DEBUG),
                                   class_weight='auto', **params)
        else:
            raise RuntimeError('unknown classifier %s' % args.classifier)

        if args.cross_evaluations > 1:
            CrossEvaluation(data, args.cross_evaluations, plot=args.plot)

        if args.model:
            # Fit a model to the given data and store it
            logging.info('fitting model to all data')
            classifier.fit(data.features, data.labels)
            LogBestFeatures(classifier, data)
            pipeline = Pipeline([('extractor', data.extractor), ('classifier', classifier)])
            logging.info('saving model to %s', args.model)

            with open(args.model, 'wb') as output_file:
                # noinspection PyArgumentList
                pickle.dump(pipeline, output_file)
    elif args.model and args.feature_function:
        logging.info('loading model for %s', args.model)
        # Do predictions on the given data using the model and feature function
        with open(args.model, 'rb') as input_file:
            # noinspection PyArgumentList
            pipeline = pickle.load(input_file)
            data.extractor = pipeline.named_steps['extractor']
            classifier = pipeline.named_steps['classifier']

        logging.info('making predictions using the loaded model')

        if args.evaluate and ground_truth:
            predictions = classifier.predict(data.features)
            probabilities = classifier.predict_proba(data.features)[:, 1]
            Evaluate(data, predictions, probabilities, plot=args.plot)

        for uid, relation in DetectRelations(data, pipeline):
            print('%s\t%s' % ('\t'.join(uid), '\t'.join(relation)))
    else:
        # Extract all co-occurrences of annotations in the given sentences
        logging.info('extracting co-occurrences only')
        for sid, rel in CoOccurrenceRelations(sentences, entities):
            print('%s\t%s' % ('\t'.join(sid), '\t'.join(rel)))
finally:
    for file in [args.file, args.feature_function, args.truth]:
        if file:
            file.close()