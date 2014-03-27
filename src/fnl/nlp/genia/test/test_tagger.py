#/usr/bin/env python3
import os

from unittest import main, TestCase

from fnl.nlp.genia.tagger import GeniaTagger, Token, GENIATAGGER_DIR

assert os.path.exists(GENIATAGGER_DIR) and \
       os.access(GENIATAGGER_DIR, os.R_OK), \
    "GENIATAGGER_DIR %s invalid - skipping GENIA Tagger tests" % (
        GENIATAGGER_DIR
    )

class GeniaTaggerTests(TestCase):

    def setUp(self):
        self.tagger = GeniaTagger()
        self.sentence = "Inhibition of NF-kappa beta activation reversed " \
            "the anti-apoptotic effect of isochamaejasmin."
        self.tokens = [
            Token('Inhibition', 'Inhibition', 'NN', 'B-NP', 'O'),
            Token('of', 'of', 'IN', 'B-PP', 'O'),
            Token('NF-kappa', 'NF-kappa', 'NN', 'B-NP', 'B-protein'),
            Token('beta', 'beta', 'NN', 'I-NP', 'I-protein'),
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
            self.tagger.send(self.sentence)

            for idx, token in enumerate(iter(self.tagger)):
                self.assertTupleEqual(token, self.tokens[idx])

    def testBadPath(self):
        self.assertRaises(AssertionError, GeniaTagger, "/fail", "whatever")
        self.assertRaises(AssertionError, GeniaTagger, "whatever", "/fail")

if __name__ == '__main__': main()
