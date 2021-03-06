import unittest

from fnl.nlp.dictionary import Dictionary, Node
from fnl.nlp.strtok import WordTokenizer


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
	tokenizer = WordTokenizer(skipTags={'space'}, skipOrthos={'e'})

	def testCreateDictionary(self):
		d = Dictionary([('key', 'The Term', 42, 21)], DictionaryTests.tokenizer)
		n = Node(The=Node(Term=Node(([42, 21], 'key'))))
		self.assertEqual(d.root, n)

	def testWalk(self):
		d = Dictionary([('key', 'the term', 42)], DictionaryTests.tokenizer)
		s = "Here is the term we're looking for."
		tokens = [s[start:end] for start, end, tag, ortho in DictionaryTests.tokenizer.tokenize(s)]
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
		tokens = [s[start:end] for start, end, tag, ortho in DictionaryTests.tokenizer.tokenize(s)]
		result = list(d.walk(tokens))
		O = Dictionary.O
		B = Dictionary.B % 'key'
		I = Dictionary.I % 'key'
		A = Dictionary.B % 'apo'
		expected = [O, O, B, I, I, A, O, O, O, O]
		self.assertEqual(result, expected)

	def testCapitalizationAlts(self):
		d = Dictionary(
			[('NEUROD1', 'NEUROD', 100),
			 ('NEUROD2', 'NEUROD2', 100)],
			DictionaryTests.tokenizer
		)
		s = "Transfection of vectors expressing neuroD and neuroD2 into P19 cells."
		tokens = [s[start:end] for start, end, tag, ortho in DictionaryTests.tokenizer.tokenize(s)]
		result = list(d.walk(tokens))
		O = Dictionary.O
		B = Dictionary.B % 'NEUROD'
		I = Dictionary.I % 'NEUROD'
		expected = [O, O, O, O, B + "1", I + "1", O, B + "2", I + "2", I + "2", O, O, O, O, O]
		self.assertEqual(result, expected)

	def testExamples(self):
		d = Dictionary(
			[('NR1D1', 'rev erb α', 1),
			 ('NR1D1', 'rev erb alpha', 1),
			 ('PPARA', 'PPAR', 1)],
			DictionaryTests.tokenizer
		)
		O = Dictionary.O
		B = Dictionary.B
		I = Dictionary.I
		sentences = [
			("A functional Rev-erb alpha responsive element located in the human Rev-erb alpha promoter mediates a repressing activity.",
			 [O, O, B % 'NR1D1', I % 'NR1D1', I % 'NR1D1', O, O, O, O, O, O, B % 'NR1D1', I % 'NR1D1', I % 'NR1D1', O, O, O, O, O, O]),
			("A positive PPAR-response element in the human apoA-I promoter nonfunctional in rats.",
			 [O, O, B % 'PPARA', O, O, O, O, O, O, O, O, O, O, O, O, O])
			]

		for s, e in sentences:
			r = list(d.walk([s[start:end] for start, end, tag, ortho in DictionaryTests.tokenizer.tokenize(s)]))
			self.assertEqual(len(r), len(e))
			self.assertEqual(r, e)


if __name__ == '__main__':
	unittest.main()
