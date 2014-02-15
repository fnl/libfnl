from libfnl.stat.kappa import Fleiss
from unittest import main, TestCase

__author__ = 'Florian Leitner'

class FleissTests(TestCase):

    def testReturnsAFloat(self):
        self.assertEqual(type(Fleiss([[1,1]])), float)

    def testUsingWikipediaExample(self):
        M = [
            [0,0,0,0,14],
            [0,2,6,4,2],
            [0,0,3,5,6],
            [0,3,9,2,0],
            [2,2,8,1,1],
            [7,7,0,0,0],
            [3,2,6,3,0],
            [2,5,3,2,2],
            [6,5,2,1,0],
            [0,2,2,3,7]
        ]
        k = Fleiss(M)
        self.assertEqual(round(k, 7), 0.2099307)

    def testUsingWrongNumberOfRaters(self):
        self.assertRaises(AssertionError, Fleiss, [ [ 1, 2 ], [ 2, 2 ] ])

    def testUsingDifferentSizedRows(self):
        self.assertRaises(AssertionError, Fleiss, [ [ 1, 1 ], [ 1, 0, 1 ] ])

if __name__ == '__main__':
    main()
