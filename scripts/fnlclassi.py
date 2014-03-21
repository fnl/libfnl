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
import warnings

from sklearn.externals import joblib
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.linear_model import RidgeClassifier
from sklearn.naive_bayes import BernoulliNB
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.feature_selection import SelectFpr, SelectKBest
from sklearn.feature_selection import chi2
from sklearn.feature_selection import f_classif

from fnl.stat.textclass import \
    Classify, Data, GridSearch, Predict, \
    PrintParams, Report, STOP_WORDS

__author__ = "Florian Leitner <florian.leitner@gmail.com>"
__verison__ = "1.0"

# Program Setup
# =============

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
                    "the real token in column COL (zero-based count); "
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
