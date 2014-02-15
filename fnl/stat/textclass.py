"""
.. py:module:: fnl.stat.textclass
   :synopsis: Tools for developing a text classifier.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

from collections import namedtuple
from itertools import chain
from functools import partial

import numpy as np

from sklearn import metrics
from sklearn.cross_validation import StratifiedKFold
from sklearn.grid_search import GridSearchCV

# Note: the minority label (always first, i.e., at index 0)
# should be used as the positive label to ensure
# precision and recall produce meaningful results
# and that the F-score is robust.
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


class Data(object):
    """
    The data object is a container for all data relevant to the classifiers.
    """

    def __init__(self, *files, column=None, decap=False):
        """
        Create a new data object with the following attributes:

            * instances - list of raw text instances
            * labels - array of instance labels in same order as raw text
            * features - matrix of feature vectors per text instance
            * names - array of feature names in same order as features

        Both features and names are undefined until extracted
        using some Vectorizer.

        Use `decap=True` to lower-case the first letter of each sentence.
        """
        try:
            if column is None:
                self.instances = [f.readlines() for f in files]
                self.raw = self.instances
            else:
                read = ReadNERInput(column)
                self.raw, self.instances = zip(*[read(f) for f in files])
        except UnicodeDecodeError as e:
            import sys
            print('decoding error:', e.reason, 'in input file')
            sys.exit(1)

        if decap:
            for group in self.instances:
                for i in range(len(group)):
                    s = group[i]
                    group[i] = "{}{}".format(s[0].lower(), s[1:])

        # ensure the minority label(s) come first (evaluation!)
        self.instances = sorted(self.instances, key=len)

        self.classes = len(self.instances)
        self.raw = sorted(self.raw, key=len)
        self.labels = np.concatenate([
            (np.zeros(len(data), dtype=np.uint8) + i)
            for i, data in enumerate(self.instances)
        ])
        self.instances = list(chain.from_iterable(self.instances))
        self.raw = list(chain.from_iterable(self.raw))
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


class Line(object):

    def __init__(self):
        self.buffer = []
        self.raw = []
        self.entities = {}
        self._entity = []
        self._entity_type = None
        self._filter_fig = False

    def hasContent(self):
        return len(self.buffer) > 0

    def parsingEntity(self):
        return self._entity_type is not None

    def openEntity(self, name, token):
        if not self._entity_type == name:
            self.closeEntity()
            self.raw.append('<{}>'.format(name))
            self._entity_type = name

            if name not in self.entities:
                self.entities[name] = set()

        self._entity.append(token)

    def closeEntity(self):
        if self._entity_type:
            name = self._entity_type
            self.raw.append('</{}>'.format(name))
            self.entities[name].add(' '.join(self._entity))
            self._entity = []
            self._entity_type = None
            self.stopFilteringFigure()

    def filteringFigure(self):
        return self._filter_fig

    def startFilteringFigure(self):
        self._filter_fig = True

    def stopFilteringFigure(self):
        self._filter_fig = False

    def append(self, token, raw=None):
        self.buffer.append(token)

        if raw:
            self.raw.append(raw)
        else:
            self.raw.append(token)


def ReadNERInput(word_col=2):
    """
    Generate a function to read NER/IOB token files
    (with the token word in column `word_col`, 3rd by default).
    """
    def read(stream, tag_col=-1):
        """Read NER/IOB token files (with the NER tag in last column)."""
        data = Line()
        lines = []
        raw = []

        for line in stream:
            content = line.strip()

            if not content:
                if data.hasContent():
                    data.closeEntity()
                    entity_counts = ' '.join(
                        '{}-{}'.format(e_type, len(data.entities[e_type]))
                        for e_type in data.entities
                    )
                    lines.append('{} {}'.format(' '.join(data.buffer),
                                                entity_counts))
                    raw.append(' '.join(data.raw))
                    data = Line()
            else:
                items = content.split('\t')
                tag = items[tag_col]
                token = items[word_col]

                if tag == 'O':
                    data.closeEntity()
                    data.append(token)
                elif tag.startswith('B-') or \
                        tag.startswith('I-'):
                    if token in UNMASK:
                        data.closeEntity()

                        if token == 'Fig':
                            data.startFilteringFigure()
                        else:
                            data.stopFilteringFigure()

                        data.append(token)
                    elif data.filteringFigure():
                        data.append(token)
                    elif items[word_col] in ('.', '-'):
                        if not data.parsingEntity():
                            data.buffer.append(token)

                        data.raw.append(token)
                    else:
                        data.openEntity(tag[2:], token)
                        data.append(tag, raw=token)
                else:
                    raise ValueError('unknown IOB tag "%s" for "%s"' %
                                     (tag, token))

        return raw, lines
    return read


def GridSearch(data, pipeline, parameters, report):
    """Do a gird search for the `parameters` of a `pipeline`."""
    grid = GridSearchCV(pipeline, parameters, scoring=Scorer,
                        cv=report.folds, refit=False, n_jobs=4, verbose=1)
    grid.fit(data.instances, data.labels)

    print("best score:", grid.best_score_)
    for name, value in grid.best_params_.items():
        print('{}:\t{}'.format(name, repr(value)))


def Predict(data, pipeline):
    """Predict lables for `data` using a sklearn `pipeline`."""
    labels = pipeline.predict(data.instances)

    for i, l in enumerate(labels):
        print(data.raw[i].strip(), l, sep='\t')


def Classify(data, classifier, report):
    """
    Classify `data` using some sklearn `classifier`,
    producing output as given by `report`.
    """
    results = {}
    scores = {n: np.zeros(report.folds) for n, f in METRICS}
    results[classifier.__class__.__name__] = scores
    cross_val = StratifiedKFold(data.labels, n_folds=report.folds)

    for step, (train, test) in enumerate(cross_val):
        classifier.fit(data.features[train], data.labels[train])
        targets = data.labels[test]
        predictions = classifier.predict(data.features[test])

        for measure, scoring_function in METRICS:
            if data.classes > 2 and measure == 'MCC score':
                scores[measure][step] = 0.0
            else:
                scores[measure][step] = scoring_function(targets, predictions)

        if report.fn or report.fp:
            PrintErrors(test, predictions, targets, data, report)

        if report.classification:
            print(metrics.classification_report(targets, predictions))

    if (report.top or report.worst):
        PrintFeatures(classifier, data, report)

    if report.top or report.worst or report.classification or \
       report.fn or report.fp or report.parameters:
        print()

    EvaluationReport(results)


def PrintErrors(test, predictions, targets, data, report):
    """Reporting of FP and FN instances."""
    for i in range(predictions.shape[0]):
        if predictions[i] != targets[i]:
            if targets[i] == 0 and report.fn:
                print("FN:", data.raw[test[i]])
            elif targets[i] != 0 and report.fp:
                print("FP:", data.raw[test[i]])


def PrintFeatures(classifier, data, report):
    """Reporting of most/least significant features."""
    for i in range(classifier.coef_.shape[0]):
        if report.top:
            topN = np.argsort(classifier.coef_[i])[-report.top:]
        else:
            topN = []

        if report.worst:
            worstN = np.argsort(classifier.coef_[i])[:report.worst]
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
    cell = "{:>2.1f}+/-{:.2f}"
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
