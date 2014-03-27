import unittest

from fnl.text.dictionary import Dictionary, Node
from fnl.text.strtok import WordTokenizer


class NodeTests(unittest.TestCase):

    def testCreateNode(self):
        n = Node('leaf', token='dummy')
        self.assertEqual(n.leafs, ['leaf'])
        self.assertEqual(n.edges, {'token': 'dummy'})

    def testCreateOrGetNode(self):
        n = Node(token='dummy')
        self.assertEqual(n.createOrGet('token'), 'dummy')

    def testSetLeaf(self):
        n = Node((1, 'a'))
        n.setLeaf('c', 3)
        n.setLeaf('b', 2)
        self.assertEqual(n.leafs, [(1, 'a'), (2, 'b'), (3, 'c')])

    def testKey(self):
        n = Node((1, 'a'))
        self.assertEqual(n.key, 'a')


class DictionaryTests(unittest.TestCase):

    tokenizer = WordTokenizer(skipTags='space')

    def testCreateDictionary(self):
        d = Dictionary([('key', 'The Term', 42, 21)], DictionaryTests.tokenizer)
        n = Node(The=Node(Term=Node(([42, 21], 'key'))))
        self.assertEqual(d.root, n)

    def testWalk(self):
        d = Dictionary([('key', 'the term', 42)], DictionaryTests.tokenizer)
        s = "Here is the term we're looking for."
        tokens = [s[start:end] for start, end, tag, morph in DictionaryTests.tokenizer.tag(s)]
        result = list(d.walk(tokens))
        O = Dictionary.O
        B = Dictionary.B % 'key'
        I = Dictionary.I % 'key'
        expected = [O, O, B, I, O, O, O, O, O, O]
        self.assertEqual(result, expected)

    def testFullWalk(self):
        d = Dictionary(
            [('alt', 'the term we', 84),
             ('key', 'the term we', 42),
             ('apo', "'", 1),
             ('part', 'term we', 21)],
            DictionaryTests.tokenizer
        )
        s = "Here is the term we're looking for."
        tokens = [s[start:end] for start, end, tag, morph in DictionaryTests.tokenizer.tag(s)]
        result = list(d.walk(tokens))
        O = Dictionary.O
        B = Dictionary.B % 'key'
        I = Dictionary.I % 'key'
        A = Dictionary.B % 'apo'
        expected = [O, O, B, I, I, A, O, O, O, O]
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
