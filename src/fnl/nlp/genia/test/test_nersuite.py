#/usr/bin/env python3
import os

from unittest import main, TestCase

from fnl.nlp.genia.nersuite import NerSuite
from fnl.text.token import Token

NERSUITE_MODEL = 'var/nersuite/models/bc2gm.iob2.no_dic.m'

assert os.path.exists(NERSUITE_MODEL) and \
       os.access(NERSUITE_MODEL, os.R_OK), \
    "no NER Suite model at %s - skipping NER Suite tagger tests" % (
        NERSUITE_MODEL
    )

NERSUITE_PATH = '/usr/local/bin/nersuite'

assert os.path.exists(NERSUITE_PATH) and \
       os.access(NERSUITE_PATH, os.R_OK), \
    "no NER Suite at path %s - skipping NER Suite tagger tests" % (
        NERSUITE_PATH
    )

class NerSuiteTests(TestCase):

    def setUp(self):
        self.tagger = NerSuite(NERSUITE_MODEL, NERSUITE_PATH)
        self.sentence = "Inhibition of NF-kappa beta activation reversed " \
            "the anti-apoptotic effect of isochamaejasmin."
        self.tokens = [
            Token('Inhibition', 'Inhibition', 'NN', 'B-NP', 'O'),
            Token('of', 'of', 'IN', 'B-PP', 'O'),
            Token('NF-kappa', 'NF-kappa', 'NN', 'B-NP', 'B-gene'),
            Token('beta', 'beta', 'NN', 'I-NP', 'I-gene'),
            Token('activation', 'activation', 'NN', 'I-NP', 'O'),
            Token('reversed', 'reverse', 'VBD', 'B-VP', 'O'),
            Token('the', 'the', 'DT', 'B-NP', 'O'),
            Token('anti-apoptotic', 'anti-apoptotic', 'JJ', 'I-NP', 'O'),
            Token('effect', 'effect', 'NN', 'I-NP', 'O'),
            Token('of', 'of', 'IN', 'B-PP', 'O'),
            Token('isochamaejasmin', 'isochamaejasmin', 'NN', 'B-NP', 'O'),
            Token('.', '.', '.', 'O', 'O')
        ]

    def tearDown(self):
        del self.tagger

    def testTagger(self):
        for dummy in range(2):
            self.tagger.send(self.tokens)

            for idx, token in enumerate(iter(self.tagger)):
                self.assertTupleEqual(token, self.tokens[idx])

    def testBadPath(self):
        self.assertRaises(AssertionError, NerSuite, "asldkfjalkclkase")
        self.assertRaises(FileNotFoundError, NerSuite, NERSUITE_MODEL, "asldkfjalkclkase")
        self.assertRaises(AssertionError, NerSuite, NERSUITE_MODEL, "/asldkfjalkclkase")

if __name__ == '__main__': main()
