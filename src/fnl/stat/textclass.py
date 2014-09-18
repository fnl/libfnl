"""
.. py:module:: fnl.stat.textclass
   :synopsis: Tools for developing a text classifier.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

from collections import defaultdict, namedtuple, Counter
from itertools import chain
from functools import partial

import numpy as np

from sklearn import metrics
from sklearn.externals import joblib, six
from sklearn.cross_validation import StratifiedKFold
from sklearn.externals.joblib import delayed
from sklearn.feature_extraction import DictVectorizer
from sklearn.grid_search import GridSearchCV

# Note: the minority label (always first, i.e., at index 0)
# should be used as the positive label to ensure
# precision and recall produce meaningful results
# and that the F-score is robust.
from fnl.text.sentence import SentenceParser, Sentence


METRICS = [
    ('Accuracy', metrics.accuracy_score),
    ('Precision', partial(metrics.precision_score, pos_label=0)),
    ('Recall', partial(metrics.recall_score, pos_label=0)),
    ('F1-score', partial(metrics.f1_score, pos_label=0)),
    ('MCC score', metrics.matthews_corrcoef),
]

# A scoring function that is robust against class-imbalances.
Scorer = metrics.make_scorer(metrics.matthews_corrcoef)

# A less restrictive stop-word list
# (compared to the built-in scikit-learn list).
STOP_WORDS = {
    'a',
    'about',
    'again',
    'all',
    'also',
    'an',
    'and',
    'any',
    'are',
    'as',
    'at',
    'be',
    'because',
    'been',
    'before',
    'being',
    'between',
    'both',
    'but',
    'by',
    'can',
    'could',
    'did',
    'do',
    'does',
    'during',
    'each',
    'for',
    'from',
    'further',
    'had',
    'has',
    'have',
    'having',
    'here',
    'how',
    'however',
    'i',
    'if',
    'in',
    'into',
    'is',
    'it',
    'its',
    'itself',
    'most',
    'no',
    'nor',
    'not',
    'of',
    'on',
    'or',
    'our',
    'should',
    'so',
    'some',
    'such',
    'than',
    'that',
    'the',
    'their',
    'theirs',
    'them',
    'then',
    'there',
    'therefor',
    'therefore',
    'these',
    'they',
    'this',
    'those',
    'through',
    'thus',
    'to',
    'very',
    'was',
    'we',
    'were',
    'what',
    'when',
    'which',
    'while',
    'with',
    'would',
}

# Contrary to the scikit-learn built in list,
# also add capitalized versions of all words
# to filter case-sensitive texts, too.
STOP_WORDS.update(w.capitalize() for w in list(STOP_WORDS))
STOP_WORDS = frozenset(STOP_WORDS)

# Words that are often classified as gene names.
UNMASK = frozenset({
    #'-',
    #'.',
    'Ab',
    'anti',
    'antibody',
    'antibodies',
    'binding',
    'ChIP',
    'Chromatin',
    'construct',
    'constructs',
    'enhancer',
    'element',
    'elements',
    'exon',
    'factor',
    'family',
    'Fig',
    'fragment',
    'gene',
    'genes',
    'GFP',
    'human',
    'islets',
    'isoform',
    'isoforms',
    'kb',
    'luciferase',
    'mouse',
    'motif',
    'mutant',
    'mutants',
    'mRNA',
    'proximal',
    'promoter',
    'promoters',
    'protein',
    'proteins',
    'rat',
    'reporter',
    'region',
    'regions',
    'repressor',
    'sequence',
    'sequences',
    'shRNA',
    'shRNAs',
    'siRNA',
    'siRNAs',
    'silencer',
    'site',
    'sites',
    'Table',
    'transcription',
})

# Reporting setup as chosen by the user.
Report = namedtuple('Report',
                    'parameters top worst fn fp classification folds')


def subAll(patterns, mask, lines):
    return [patterns.sub(mask, line) for line in lines]


def asDict(sentence: Sentence, ngrams=2):
    """Convert a :class:`fnl.text.sentence.Sentence` into a feature dictionary."""
    d = {'gene-count': sentence.countEntity('B-gene')}
    stems = list(sentence.maskedStems())
    pos = sentence.posTags()
    tokens = Counter('{}/{}'.format(s, t) for s, t in zip(stems, pos))
    d.update(tokens)

    if "TARGET/NN" in d and "FACTOR/NN" in d:
        d['has-all-entities'] = 1

    gram = list(stems)

    while ngrams > 1:
        ngrams =- 1
        tokens = Counter('{} {}'.format(s, g) for s, g in zip(stems, gram[1:]))
        d.update(tokens)

    return d


class Data:
    """
    The data object is a container for all data relevant to the classifiers.
    """

    def __init__(self, *files, columns=None, ngrams=2, decap=False, patterns=None, mask=None):
        """
        Create a new data object with the following attributes:

            * instances - list of raw text instances
            * labels - array of instance labels in same order as raw text
            * features - matrix of feature vectors per text instance
            * names - array of feature names in same order as features

        Both features and names are undefined until extracted
        using some Vectorizer.

        Exclusive options for either BIO-NER vs. plain-text input:

        1. **BIO-NER** paramters: Define a `columns` integer to define the number of disregarded
           columns and thereby declare that the input will be in BIO-NER format. In addtion, the
           `ngram` option can be set to define the ngram size of the tokens to generate.
           All other keyword parameter will be ignored.

        2. **plain-text** keyword parameters: Set `decap=True` to lower-case the first letter of
           each plain-text line. Use a list of regex `patterns` and a repacement string `mask` to
           "mask" pattern-matched words in regular (non-`column`) input.
        """
        try:
            if columns is None:
                inputs = [f.readlines() for f in files]

                if patterns and mask:
                    self.instances = []
                    splits = joblib.cpu_count()

                    for group in inputs:
                        group = tuple(group[i::splits] for i in range(splits))
                        group = joblib.Parallel(n_jobs=splits)(
                            delayed(subAll)(patterns, mask, lines) for lines in group
                        )
                        self.instances.append(list(enumerate(chain(*group))))
                else:
                    self.instances = [((num,), i) for num, i in enumerate(inputs, start=1)]

                if decap:
                    for group in self.instances:
                        for i in range(len(group)):
                            s = group[i]
                            group[i] = "{}{}".format(s[0].lower(), s[1:])
            else:
                self.instances = []

                for f in files:
                    # FIXME: instead of two hardcoded entity masks,
                    # FIXME: this has to be dynamic or generic...
                    sentences = SentenceParser(f, ('FACTOR', 'TARGET'), id_columns=columns)

                    if not columns:
                        sentences = map(lambda n, s: ((n,), s), enumerate(sentences, start=1))

                    data = list((sid, asDict(s, ngrams)) for sid, s in sentences)
                    self.instances.append(data)
        except UnicodeDecodeError as e:
            import sys
            print('decoding error:', e.reason, 'in input file')
            sys.exit(1)

        # ensure the minority label(s) come first (important for the evaluation, too!)
        self.instances = sorted(self.instances, key=len)

        self.classes = len(self.instances)
        self.labels = np.concatenate([
            (np.zeros(len(data), dtype=np.uint8) + i)
            for i, data in enumerate(self.instances)
        ])
        self.ids, self.instances = zip(*list(chain.from_iterable(self.instances)))
        self.features = None
        self.names = None

    def extract(self, vectorizer):
        """Extract the features from the instances using a Vectorizer."""
        self.features = vectorizer.fit_transform(self.instances, self.labels)
        self.names = np.asarray(vectorizer.get_feature_names())
        return self

    def transform(self, method):
        """Transform the features with a selection or transformation method."""
        self.features = method.fit_transform(self.features, self.labels)
        return self

    @property
    def n_features(self):
        """The number of features."""
        return self.features.shape[1]

    @property
    def n_instances(self):
        """The (total) number of instances."""
        return self.features.shape[0]

    @property
    def sizes(self):
        """Number of instances per class."""
        counter = {}
        for l in self.labels:
            try:
                counter[l] += 1
            except KeyError:
                counter[l] = 1

        return [counter[l] for l in sorted(counter.keys())]


class MinFreqDictVectorizer(DictVectorizer):
    """
    Add `text.CountVectorizer` min. document frequency filtering ability to the `DictVectorizer`.
    """

    def __init__(self, min_freq=1, **kwargs):
        super(MinFreqDictVectorizer, self).__init__(**kwargs)
        self.min_freq = min_freq

    def fit(self, X, y=None):
        features = defaultdict(int)

        for x in X:
            for f, v in six.iteritems(x):
                if isinstance(v, six.string_types):
                    f = "%s%s%s" % (f, self.separator, v)
                features[f] += 1

        if self.min_freq > 1:
            for name, count in list(features.items()):
                if count < self.min_freq:
                    del features[name]

        feature_names = sorted(features.keys())
        self.vocabulary_ = dict((f, i) for i, f in enumerate(feature_names))
        self.feature_names_ = feature_names
        return self


def GridSearch(data, pipeline, parameters, report):
    """Do a gird search for the `parameters` of a `pipeline`."""
    grid = GridSearchCV(pipeline, parameters, scoring=Scorer,
                        cv=report.folds, refit=False, n_jobs=4, verbose=1)
    grid.fit(data.instances, data.labels)

    print("best score:", grid.best_score_)
    for name, value in grid.best_params_.items():
        print('{}:\t{}'.format(name, repr(value)))


def Predict(data, pipeline, sep='\t'):
    """
    Predict and print the lables for `data` using a sklearn `pipeline`.
    In addition, a confidence value for each label is printed.
    The lines, the label, and the confidenve value are separated by `sep`.
    """
    labels = pipeline.predict(data.instances)

    # find an appropriate confidence score method given the predictor
    if hasattr(pipeline, "decision_function"):
        scorer = pipeline.decision_function
    elif hasattr(pipeline, "predict_log_proba"):
        scorer = pipeline.predict_log_proba
    elif hasattr(pipeline, "predict_proba"):
        scorer = pipeline.predict_proba
    else:
        # no known method; default to a "100%" confidence
        scorer = lambda X: [1.0] * len(X)

    scores = scorer(data.instances)

    for i, (l, s) in enumerate(zip(labels, scores)):
        # for multi-label problems, get the score of the final label
        s = s[l] if isinstance(s, np.ndarray) else s
        print(sep.join(data.ids[i]), l, s, sep=sep)


def Classify(data, classifier, report):
    """
    Classify `data` using some sklearn `classifier`,
    producing output as given by `report`.
    """
    results = {}
    scores = {n: np.zeros(report.folds) for n, f in METRICS}
    results[classifier.__class__.__name__] = scores
    cross_val = StratifiedKFold(data.labels, n_folds=report.folds, shuffle=True)
    test = None
    predictions = None
    targets = None

    if report.classification:
        print()

    for step, (train, test) in enumerate(cross_val):
        classifier.fit(data.features[train], data.labels[train])
        targets = data.labels[test]
        predictions = classifier.predict(data.features[test])

        for measure, scoring_function in METRICS:
            if data.classes > 2 and measure == 'MCC score':
                scores[measure][step] = 0.0
            else:
                scores[measure][step] = scoring_function(targets, predictions)

        if report.classification:
            print(metrics.classification_report(targets, predictions))

    if report.fn or report.fp:
        print()
        PrintErrors(test, predictions, targets, data, report)

    if (report.top or report.worst):
        print()
        PrintFeatures(classifier, data, report)

    print()
    EvaluationReport(results)


def PrintErrors(test, predictions, targets, data, report):
    """Reporting of FP and FN instances."""
    for i in range(predictions.shape[0]):
        if predictions[i] != targets[i]:
            if targets[i] == 0 and report.fn:
                print("FN:", "\t".join(data.ids[test[i]]))
            elif targets[i] != 0 and report.fp:
                print("FP:", "\t".join(data.ids[test[i]]))


def PrintFeatures(classifier, data, report):
    """Reporting of most/least significant features."""
    for i in range(classifier.coef_.shape[0]):
        if report.top:
            topN = np.argsort(classifier.coef_[i])[:report.top]
        else:
            topN = []

        if report.worst:
            worstN = np.argsort(classifier.coef_[i])[-report.worst:]
            worstN = worstN[::-1]
        else:
            worstN = []

        print('group {2} features (top-worst): "{0}", ... "{1}"'.format(
            '", "'.join(data.names[topN]),
            '", "'.join(data.names[worstN]), i + 1,
        ))


def EvaluationReport(results):
    """Evaluation result table for all classifiers."""
    classifiers = list(sorted(results.keys()))
    heading = '{:<10s}'
    cell = "{:5.1f} ± {:5.2f}"
    print('MEASURE   \t{}'.format('\t'.join(
        heading.format(c) for c in classifiers
    )))

    for m, f in METRICS:
        line = [heading.format(m)]

        for c in classifiers:
            s = results[c][m]
            line.append(cell.format(100 * s.mean(), 200 * s.std()))

        print('\t'.join(line))


def PrintParams(klass, report):
    """Reporting of classifier parameters."""
    if report.top or report.worst or report.classification or \
            report.fn or report.fp or report.parameters:
        text = "= {} =".format(klass.__class__.__name__)
        print('=' * len(text))
        print(text)
        print('=' * len(text))

    if report.parameters:
        print("\n".join(
            "{}: {}".format(k, v) for k, v in klass.get_params().items()
        ))
