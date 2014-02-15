#!/usr/bin/env python3
"""
Create a probablistic model of sentence boundaries from the input text.
"""

# Author: Florian Leitner <florian.leitner@gmail.com>
# (C) 2013. All rights reserved.
# License: Apache License v2 <https://www.apache.org/licenses/LICENSE-2.0.html>

# The algorithm for the sentence segmenter is described in:
# Kiss, Tibor and Strunk, Jan (2006): Unsupervised Multilingual Sentence
# Boundary Detection. Computational Linguistics 32: 485-525.

import fileinput
import pickle
import sys

from os.path import basename
from nltk.tokenize.punkt import PunktTrainer

__author__ = 'Florian Leitner'

if len(sys.argv) == 2 and sys.argv[1] in ('-h', '--help'):
    print('usage: {} < TEXT > MODEL'.format(basename(sys.argv[0])))
    sys.exit(1)

trainer = PunktTrainer()
# configuration
trainer.ABBREV = 0.3  # cut-off value whether a ‘token’ is an abbreviation
trainer.ABBREV_CUTOFF = 5  # upper cut-off for Mikheev’s (2002) abbreviation detection algorithm
trainer.COLLOCATION = 7.88  # minimal log-likelihood value that two tokens need to be considered as a collocation
trainer.IGNORE_ABBREV_PENALTY = False  # disables the abbreviation penalty heuristic, which exponentially disadvantages words that are found at times without a final period
trainer.INCLUDE_ABBREV_COLLOCS = True  # include as potential collocations all word pairs where the first word is an abbreviation - such collocations override the orthographic heuristic, but not the sentence starter heuristic
trainer.INCLUDE_ALL_COLLOCS = False  # this includes as potential collocations all word pairs where the first word ends in a period - it may be useful in corpora where there is a lot of variation that makes abbreviations like Mr difficult to identify
trainer.MIN_COLLOC_FREQ = 3  # minimum bound on the number of times a bigram needs to appear before it can be considered a collocation - useful when INCLUDE_*_COLLOCS are used
trainer.SENT_STARTER = 30  # minimal log-likelihood value that a token requires to be considered as a frequent sentence starter

for line in fileinput.input():
    trainer.train(line)
    #print(line)

#trainer.freq_threshold()
trainer.finalize_training()
params = trainer.get_params()
pickle.dump(params, sys.stdout.buffer)
