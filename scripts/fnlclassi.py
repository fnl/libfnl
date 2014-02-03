#!/usr/bin/env python3

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

__author__ = "Florian Leitner <florian.leitner@gmail.com>"
__verison__ = "1.0"

import warnings

from collections import namedtuple
from itertools import chain
from functools import partial

import numpy as np

from sklearn import metrics
from sklearn.cross_validation import StratifiedKFold
from sklearn.externals import joblib
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.grid_search import GridSearchCV
from sklearn.linear_model import RidgeClassifier
from sklearn.naive_bayes import BernoulliNB
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.feature_selection import SelectFpr, SelectKBest
from sklearn.feature_selection import chi2
from sklearn.feature_selection import f_classif

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


def GridSearch(data, pipeline, paramters, report):
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


if __name__ == '__main__':

    # Program Setup
    # =============

    import argparse
    import os.path
    parser = argparse.ArgumentParser(
        description="a text classification tool",
        usage="%(prog)s [OPTIONS] CLASS GROUP [GROUP [...]]"
    )

    parser.add_argument("classifier", metavar='CLASS',
                        help="choices: ridge, svm, multinomial, bernoulli, "
                        "or load a saved model FILE")
    parser.add_argument("groups", metavar='GROUP', nargs='+', type=open,
                        help="file containing all the instances "
                        "for one particular class")

    parser.add_argument("--column", metavar='COL', type=int, default=None,
                        help="input files are NER tagged in BIO-format "
                        "with the (BIO-) tag in the last column and "
                        "the real token in column COL; "
                        "tagged tokens will be masked using its (BIO-) tag")
    parser.add_argument("--decapitalize", action='store_true',
                        help="lowercase first letter of each instance")
    parser.add_argument("--feature-grid-search", action='store_true',
                        help="run a grid search for the "
                        "optimal feature parameters")
    parser.add_argument("--classifier-grid-search", action='store_true',
                        help="run a grid search for the "
                        "optimal classifier parameters")
    parser.add_argument("--save", metavar='FILE', type=str,
                        help="store the fitted classifier pipeline on disk")

    feats = parser.add_argument_group('feature extraction/selection options')
    feats.add_argument("--all-words", action='store_true',
                       help="extract symbol tokens, too")
    feats.add_argument("--anova", action='store_true',
                       help="use ANOVA F-values for feature weighting; "
                       "default: chi^2")
    feats.add_argument("--cutoff", default=3, type=int,
                       help="min. doc. frequency required "
                       "to use a token as a feature; "
                       "value must be a positive integer; "
                       "defaults to 3 (use almost all tokens)")
    feats.add_argument("--real-case", action='store_true',
                       help="do not lower-case all letters")
    feats.add_argument("--max-fpr", metavar='FPR', default=1.0, type=float,
                       help="select features having a min. FPR in (0,1]; "
                       "default 1.0 - use all features")
    feats.add_argument("--num-features", metavar='NUM', default=0, type=int,
                       help="select a number of features to use")
    feats.add_argument("--n-grams", metavar='N', default=3, type=int,
                       help="use token n-grams of size N; "
                       "default: 3 - trigrams")
    feats.add_argument("--stop-words", action='store_true',
                       help="filter (English) stop-words")
    feats.add_argument("--tfidf", action='store_true',
                       help="re-rank token counts using "
                       "a regularized TF-IDF score")

    evrep = parser.add_argument_group('evaluation and report')
    evrep.add_argument("--parameters", action='store_true',
                       help="report classification setup parameters")
    evrep.add_argument("--features", action='store_true',
                       help="report feature size counts")
    evrep.add_argument("--top", metavar='N', default=0, type=int,
                       help="list the N most significant features")
    evrep.add_argument("--worst", metavar='N', default=0, type=int,
                       help="list the N least significant features")
    evrep.add_argument("--false-negatives", action='store_true',
                       help="report false negative classifications")
    evrep.add_argument("--false-positives", action='store_true',
                       help="report false positive classifications")
    evrep.add_argument("--classification-reports", action='store_true',
                       help="print per-fold classification reports")
    evrep.add_argument("--folds", metavar='N', default=5, type=int,
                       help="use N-fold cross-validation for evaluation; "
                       "n must be an integer > 1; "
                       "defaults to 5")

    # Argument Parsing
    # ================

    args = parser.parse_args()

    if 2 > args.folds:
        parser.error("the CV fold value must be > 1")

    if 1 > args.cutoff:
        parser.error("the cutoff value must be positive")

    if 1 > args.n_grams:
        parser.error("the n-gram value must be positive")

    if args.column is not None and 0 > args.column:
        parser.error("column index must be non-negative")

    if not (0.0 < args.max_fpr <= 1.0):
        parser.error("max. FPR must be in (0,1] range")

    data = Data(*args.groups, column=args.column, decap=args.decapitalize)
    classifier = None
    pipeline = []
    parameters = {}
    grid_search = args.feature_grid_search or args.classifier_grid_search

    # Classifier Setup
    # ================

    if args.classifier == 'ridge':
        classifier = RidgeClassifier(alpha=0.1, tol=0.01, solver='sparse_cg')

        if args.classifier_grid_search:
            parameters['classifier__alpha'] = [1.0, 1e-1, 1e-2, 1e-3]
            parameters['classifier__solver'] = ['lsqr', 'sparse_cg']
            parameters['classifier__tol'] = [1e-1, 1e-2, 1e-3, 1e-4]
    elif args.classifier == 'svm':
        classifier = LinearSVC(loss='l2', penalty='l2', dual=True,
                               C=0.05, tol=0.01)

        if args.classifier_grid_search:
            parameters['classifier__C'] = [1.0, 0.5, 1e-1, 5e-2, 1e-2]
            parameters['classifier__tol'] = [1.0, 0.5, 1e-1, 5e-2, 1e-2]
    elif args.classifier == 'multinomial':
        classifier = MultinomialNB(alpha=.01)

        if args.classifier_grid_search:
            parameters['classifier__alpha'] = [1.0, 1e-1, 1e-2, 1e-3]
    elif args.classifier == 'bernoulli':
        classifier = BernoulliNB(alpha=.01, binarize=False)

        if args.classifier_grid_search:
            parameters['classifier__alpha'] = [0.1, 0.05, 0.01, 0.05, 0.001]
            parameters['classifier__binarize'] = [True, False]
    elif os.path.isfile(args.classifier):
        Predict(data, joblib.load(args.classifier))
        import sys
        sys.exit(0)
    else:
        parser.error("unrecognized classifier '%s'" % args.classifier)

    report = Report(args.parameters, args.top, args.worst,
                    args.false_negatives, args.false_positives,
                    args.classification_reports, args.folds)

    # Feature Extraction
    # ==================

    token_pattern = r'\b\w[\w-]+\b' if not args.all_words else r'\S+'
    stop_words = STOP_WORDS if args.stop_words else None
    vec = CountVectorizer(ngram_range=(1, args.n_grams),
                          token_pattern=token_pattern,
                          stop_words=stop_words,
                          strip_accents='unicode',
                          lowercase=not args.real_case,
                          min_df=args.cutoff)

    pipeline.append(('extract', vec))

    if args.feature_grid_search:
        parameters['extract__lowercase'] = [True, False]
        parameters['extract__min_df'] = [1, 2, 3, 5]
        parameters['extract__ngram_range'] = [(1, 1), (1, 2), (1, 3)]
        parameters['extract__stop_words'] = [None, STOP_WORDS]
        parameters['extract__token_pattern'] = [r'[^ ]+', r'\b\w[\w-]+\b']

    if report.parameters:
        PrintParams(vec, report)

    if not grid_search:
        data.extract(vec)

    # Feature Transformation
    # ======================

    if args.tfidf:
        tfidf = TfidfTransformer(norm='l2',
                                 sublinear_tf=True,
                                 smooth_idf=True,
                                 use_idf=True)

        if report.parameters:
            print()
            PrintParams(tfidf, report)

        pipeline.append(('transform', tfidf))

        if args.feature_grid_search:
            parameters['transform__norm'] = [None, 'l1', 'l2']
            parameters['transform__use_idf'] = [True, False]
            parameters['transform__smooth_idf'] = [True, False]
            parameters['transform__sublinear_tf'] = [True, False]

        if not grid_search:
            data.transform(tfidf)

    # Feature Selection
    # =================

    if args.max_fpr != 1.0:
        # False-Positive Rate
        fprs = SelectFpr(chi2 if not args.anova else f_classif,
                         alpha=args.max_fpr)
        pipeline.append(('select', fprs))
        num_feats = 0 if grid_search else data.n_features

        if report.parameters:
            print()
            PrintParams(fprs, report)
            print()

        if not grid_search:
            with warnings.catch_warnings():
                # suppress the irrelevant duplicate p-values warning
                warnings.simplefilter("ignore")
                data.transform(fprs)

            if args.features:
                print('pruned {}/{} features'.format(
                    num_feats - data.n_features, num_feats
                ))
        elif args.feature_grid_search:
            parameters['select__alpha'] = [1.0, 0.5, 0.25, 0.1, 0.05, 0.01]
    elif args.num_features != 0:
        # K-Best Features
        kbest = SelectKBest(chi2 if not args.anova else f_classif,
                            k=args.num_features)
        pipeline.append(('select', kbest))

        if report.parameters:
            print()
            PrintParams(kbest, report)
            print()

        if not grid_search:
            with warnings.catch_warnings():
                # suppress the irrelevant duplicate p-values warning
                warnings.simplefilter("ignore")
                data.transform(kbest)
        elif args.feature_grid_search:
            parameters['select__k'] = [1e2, 1e3, 1e4, 1e5]

    elif report.parameters:
        print()

    if not grid_search and args.features:
        print('group sizes:', ', '.join(map(str, data.sizes)))
        print('extracted {} features from {} instances\n'.format(
            data.n_features, data.n_instances
        ))

    # Classification
    # ==============

    pipeline.append(('classifier', classifier))
    pipeline = Pipeline(pipeline)

    if report.parameters:
        PrintParams(classifier, report)

    if grid_search:
        print("\nGrid Search:")
        print('\n'.join(
            '{}: {}'.format(k, repr(v)) for k, v in parameters.items()
        ))
        GridSearch(data, pipeline, parameters, report)
    else:
        Classify(data, classifier, report)

    if args.save:
        joblib.dump(pipeline, args.save)
