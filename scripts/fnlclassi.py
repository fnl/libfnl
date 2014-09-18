#!/usr/bin/env python3

"""classi is a tool for text classification"""

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

import argparse
import os.path
import re
import warnings

from sklearn.externals import joblib
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.linear_model import RidgeClassifier, LogisticRegression
from sklearn.naive_bayes import BernoulliNB
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.feature_selection import SelectFpr, SelectKBest
from sklearn.feature_selection import chi2
from sklearn.feature_selection import f_classif

from fnl.stat.textclass import \
    Classify, Data, GridSearch, Predict, \
    PrintParams, Report, STOP_WORDS, PrintFeatures, MinFreqDictVectorizer


__author__ = "Florian Leitner <florian.leitner@gmail.com>"
__verison__ = "1.0"

# Program Setup
# =============

parser = argparse.ArgumentParser(
    description="a text classification tool",
    usage="%(prog)s [OPTIONS] CLASS GROUP [GROUP [...]]"
)

parser.add_argument("classifier", metavar='CLASS',
                    help="choices: ridge, svm, maxent, multinomial, bernoulli, "
                    "or load a saved model FILE")
parser.add_argument("groups", metavar='GROUP', nargs='+', # using type=open a BadIdeaTM in 3.4...
                    help="file containing all the instances "
                    "for one particular class (in plain text or NER-BIO format)")

parser.add_argument("--column", metavar='COL', type=int, default=None,
                    help="input files are NER tagged tokens in BIO-format "
                    "with the token in column COL (one-based count), "
                    "the stem in COL + 1, the PoS tag in COL + 2, the phrase tag in COL + 3, "
                    "and any (BIO-) entity tags in COL + 4 and beyond; "
                    "entity tagged tokens will be masked using the first applicable BIO-tag")
parser.add_argument("--decapitalize", action='store_true',
                    help="lowercase first letter of each instance")
parser.add_argument("--feature-grid-search", action='store_true',
                    help="run a grid search for the optimal feature parameters")
parser.add_argument("--classifier-grid-search", action='store_true',
                    help="run a grid search for the optimal classifier parameters")
parser.add_argument("--save", metavar='FILE', type=str,
                    help="store the fitted classifier pipeline on disk")

pt_feats = parser.add_argument_group('feature generation from plain-text files')
pt_feats.add_argument("--token-pattern", default=r"(?u)\b\w\w+\b",
                      help="define a RegEx pattern for tokenization [\\b\\w\\w+\\b]")
pt_feats.add_argument("--patterns", metavar='FILE', type=open,
                      help="a file containing regex patterns that will mask (raw input) text")
pt_feats.add_argument("--mask", default='M_A_S_K',
                      help='replacement string for matched regex patterns ["M_A_S_K"]')
pt_feats.add_argument("--real-case", action='store_true',
                      help="do not lower-case all letters")
pt_feats.add_argument("--stop-words", action='store_true',
                      help="filter (English) stop-words")
pt_feats.add_argument("--tfidf", action='store_true',
                      help="re-rank token counts using a regularized TF-IDF score")

bio_feats = parser.add_argument_group('feature generation from BIO-NER files')

selects = parser.add_argument_group('feature selection options')
selects.add_argument("--n-grams", metavar='N', default=2, type=int,
                     help="use token n-grams of size N; default: 2 - bigrams")
selects.add_argument("--cutoff", default=3, type=int,
                     help="min. doc. frequency required to use a feature; "
                     "value must be a positive integer; defaults to 3 "
                     "(only use features seen at least in 3 documents)")
selects.add_argument("--max-fpr", metavar='FPR', default=1.0, type=float,
                     help="select features having a min. FPR in (0,1]; "
                     "default 1.0 - use all features")
selects.add_argument("--num-features", metavar='NUM', default=0, type=int,
                     help="limit to a number NUM of best features only; default: all")
selects.add_argument("--anova", action='store_true',
                     help="use ANOVA F-values for feature weighting; default: chi^2")

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
                   help="do N-fold cross-validation for internal evaluations; "
                   "N must be an integer > 1; defaults to 5")

# Argument Parsing
# ================

args = parser.parse_args()

if 2 > args.folds:
    parser.error("the CV fold value must be > 1")

if 1 > args.cutoff:
    parser.error("the cutoff value must be positive")

if 1 > args.n_grams:
    parser.error("the n-gram value must be positive")

if not (0.0 < args.max_fpr <= 1.0):
    parser.error("max. FPR must be in (0,1] range")


patterns = None

if args.patterns:
    patterns = re.compile('|'.join(l.strip('\n\r') for l in args.patterns))
    args.patterns.close()

filehandles = []

for path in args.groups:
    try:
        filehandles.append(open(path))
    except Exception as e:
        parser.error('failed to open "{}": {}'.format(path, e))

data = Data(*filehandles,
            columns=args.column, ngrams=args.n_grams,  # BIO-NER input
            decap=args.decapitalize, patterns=patterns, mask=args.mask)  # plain-text input

for fh in filehandles:
    fh.close()

classifier = None
pipeline = []
parameters = {}
grid_search = args.feature_grid_search or args.classifier_grid_search

# Classifier Setup
# ================

# TODO: defining all classifier parameters as opt-args for this script

if args.classifier == 'ridge':
    classifier = RidgeClassifier()

    if args.classifier_grid_search:
        parameters['classifier__alpha'] = [10., 1., 0., .1, .01]
        parameters['classifier__normalize'] = [True, False]
        parameters['classifier__solver'] = ['svd', 'cholesky', 'lsqr', 'sparse_cg']
        parameters['classifier__tol'] = [.1, .01, 1e-3, 1e-6]
elif args.classifier == 'svm':
    classifier = LinearSVC(loss='l1')  # prefer Hinge loss (slower, but "better")

    if args.classifier_grid_search:
        parameters['classifier__C'] = [100., 10., 1., .1, .01]
        parameters['classifier__class_weight'] = ['auto', None]
        parameters['classifier__intercept_scaling'] = [10., 5., 1., .5]
        parameters['classifier__penalty'] = ['l1', 'l2']
        parameters['classifier__tol'] = [.1, .01, 1e-4, 1e-8]
elif args.classifier == 'maxent':
    classifier = LogisticRegression(class_weight='auto')

    if args.classifier_grid_search:
        parameters['classifier__C'] = [100., 10., 1., .1, .01]
        parameters['classifier__class_weight'] = ['auto', None]
        parameters['classifier__intercept_scaling'] = [10., 5., 1., .5]
        parameters['classifier__penalty'] = ['l1', 'l2']
        parameters['classifier__tol'] = [.1, .01, 1e-4, 1e-8]
elif args.classifier == 'multinomial':
    classifier = MultinomialNB()

    if args.classifier_grid_search:
        parameters['classifier__alpha'] = [10., 1., 0., .1, .01]
        parameters['classifier__fit_prior'] = [True, False]
elif args.classifier == 'bernoulli':
    classifier = BernoulliNB()

    if args.classifier_grid_search:
        parameters['classifier__alpha'] = [10., 1., 0., .1, .01]
        parameters['classifier__binarize'] = [True, False]
        parameters['classifier__fit_prior'] = [True, False]
elif os.path.isfile(args.classifier):

    # Prediction [with an existing pipeline]
    # ==========
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

if args.column is None:
    # token_pattern = r'\b\w[\w-]+\b' if not args.token_pattern else r'\S+'
    stop_words = STOP_WORDS if args.stop_words else None
    vec = CountVectorizer(binary=False,
                          lowercase=not args.real_case,
                          min_df=args.cutoff,
                          ngram_range=(1, args.n_grams),
                          stop_words=stop_words,
                          strip_accents='unicode',
                          token_pattern=args.token_pattern)

    if args.feature_grid_search:
        parameters['extract__binary'] = [True, False]
        parameters['extract__lowercase'] = [True, False]
        parameters['extract__min_df'] = [1, 2, 3, 5]
        parameters['extract__ngram_range'] = [(1, 1), (1, 2), (1, 3)]
        parameters['extract__stop_words'] = [None, STOP_WORDS]
else:
    vec = MinFreqDictVectorizer(min_freq=args.cutoff)

    if args.feature_grid_search:
        parameters['extract__min_freq'] = [1, 2, 3, 5]


pipeline.append(('extract', vec))

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

    if not grid_search:
        with warnings.catch_warnings():
            # suppress the irrelevant duplicate p-values warning
            warnings.simplefilter("ignore")
            data.transform(fprs)

        if args.features:
            print('\npruned {}/{} features'.format(
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

    if not grid_search:
        with warnings.catch_warnings():
            # suppress the irrelevant duplicate p-values warning
            warnings.simplefilter("ignore")
            data.transform(kbest)
    elif args.feature_grid_search:
        parameters['select__k'] = [1e2, 1e3, 1e4, 1e5]

if not grid_search and args.features:
    print('\ngroup sizes:', ', '.join(map(str, data.sizes)))
    print('extracted {} features from {} instances'.format(
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
    if (report.top or report.worst):
        print()
        PrintFeatures(classifier, data, report)

    joblib.dump(pipeline, args.save)