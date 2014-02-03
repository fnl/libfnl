#!/usr/bin/env python3

# this script segments text into sentences given a probabilistic model
# (from fnlpsttrain.py)

# Auhtor: Florian Leitner <florian.leitner@gmail.com>
# (C) 2013. All rights reserved.
# License: Apache License v2 <https://www.apache.org/licenses/LICENSE-2.0.html>

import fileinput
import pickle
import sys

from os.path import basename
from nltk.tokenize.punkt import PunktSentenceTokenizer

if len(sys.argv) == 1 or (len(sys.argv) == 2 and
                          sys.argv[1] in ('-h', '--help')):
    print('usage: {} MODEL < TEXT > SENTENCES'.format(basename(sys.argv[0])))
    sys.exit(1)

with open(sys.argv[1], 'rb') as f:
    params = pickle.load(f)

pst = PunktSentenceTokenizer(params)

for text in fileinput.input():
    for sentence in pst.tokenize(text.strip()):
        if sentence:
            print(sentence)
