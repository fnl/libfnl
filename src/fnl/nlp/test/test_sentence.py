from fnl.nlp.sentence import Sentence, Annotation, SentenceParser
from fnl.nlp.token import Token
from unittest import main, TestCase

__author__ = 'Florian Leitner'

TEST_TOKENS = [
	Token('word%d' % i, 'stem%d' % i, 'pos%d' % i,
	      ['B-NP', 'I-NP', 'O'][i % 3],
	      ['B-protein', 'I-protein', 'O'][i % 3]) for i in range(10)
]


class TestSentence(TestCase):

	def testInit(self):
		s = Sentence(TEST_TOKENS)
		self.assertEqual(len(s), len(TEST_TOKENS))
		self.assertEqual(list(s), TEST_TOKENS)

	def testCopyConstructor(self):
		s1 = Sentence(TEST_TOKENS)
		s1.addAnnotation("ann", 1)
		s2 = Sentence(s1)
		self.assertEqual(s2.getAnnotations("ann"), s1.getAnnotations("ann"))

	def testEquals(self):
		s1 = Sentence(TEST_TOKENS)
		s2 = Sentence(s1)
		self.assertEqual(s1, s1)
		self.assertNotEqual(s1, s2)

	def testAddAnnotation(self):
		s = Sentence(TEST_TOKENS)
		s.addAnnotation('type1', 2, 4)
		s.addAnnotation('type2', 6)
		s.addAnnotation('type2', 8, 9)
		self.assertEqual(len(s.annotations), 2)
		self.assertEqual(set(s.annotations.keys()), {'type1', 'type2'})
		self.assertTrue(all(isinstance(annotations, set) for
		                    annotations in s.annotations.values()))
		self.assertEqual(sum(len(annotations) for annotations in s.annotations.values()), 3)

	def testAddAnnotationsAreUnique(self):
		s = Sentence(TEST_TOKENS)
		s.addAnnotation('type1', 2, 4)
		s.addAnnotation('type1', 2, 4)
		self.assertEqual(len(s.annotations), 1)
		self.assertEqual(sum(len(annotations) for annotations in s.annotations.values()), 1)

	def testGetAnnotations(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('type1', 2, 4)
		a1 = s.addAnnotation('type2', 6)
		a2 = s.addAnnotation('type2', 8, 9)
		self.assertEqual(s.getAnnotations('type1'), {a})
		self.assertEqual(s.getAnnotations('type2'), {a1, a2})

	def testGetMaskedStems(self):
		s = Sentence(TEST_TOKENS)
		s.addAnnotation('type1', 2, 4)
		s.addAnnotation('type2', 6)
		s.addAnnotation('type2', 8, 9)
		self.assertListEqual(list(s.maskedStems(3, 7)), [
			'type1', 'stem4', 'stem5', 'type2'
		])

	def testGetMaskedWords(self):
		s = Sentence(TEST_TOKENS)
		s.addAnnotation('type1', 2, 4)
		s.addAnnotation('type2', 6)
		s.addAnnotation('type2', 8, 9)
		self.assertListEqual(list(s.maskedWords()), [
			'word0', 'word1', 'type1', 'type1', 'word4',
			'word5', 'type2', 'word7', 'type2', 'word9'
		])
		self.assertListEqual(list(s.maskedWords(7)), [
			'word7', 'type2', 'word9'
		])

	def testGetPhraseNumber(self):
		s = Sentence(TEST_TOKENS)
		tests = [1,1,0,2,2,0,3,3,0,4]

		for i, n in enumerate(tests):
			self.assertEqual(s.phraseNumber(i), n)

	def testGetPhraseNumbers(self):
		s = Sentence(TEST_TOKENS)
		self.assertListEqual(list(s.phraseNumbers()), [
			1, 2, 3, 4
		])
		self.assertListEqual(list(s.phraseNumbers(1, 6)), [
			1, 2
		])

	def testGetPhraseOffset(self):
		s = Sentence(TEST_TOKENS)
		tests = [(1,(0,2)), (2,(3,5)), (3,(6,8)), (4,(9,10))]

		for number, offset in tests:
			self.assertEqual(s.phraseOffsetFor(number), offset)

	def testGetPhraseTag(self):
		s = Sentence(TEST_TOKENS)

		for i in range(1, 5):
			self.assertEqual(s.phraseTagFor(i), 'NP')

	def testGetPhraseTagFailure(self):
		s = Sentence(TEST_TOKENS)
		self.assertRaises(KeyError, s.phraseTagFor, 0)
		self.assertRaises(KeyError, s.phraseTagFor, 5)

	def testGetPhraseTags(self):
		s = Sentence(TEST_TOKENS)
		self.assertListEqual(list(s.phraseTags()), [
			'NP', 'NP', 'NP', 'NP'
		])
		self.assertListEqual(list(s.phraseTags(1, 6)), [
			'NP', 'NP'
		])

	def testGetPoSTags(self):
		s = Sentence(TEST_TOKENS)
		s.addAnnotation('mask', 2, 4)
		s.addAnnotation('mask', 6)
		self.assertListEqual(list(s.posTags(3, 7)), [
			'pos3', 'pos4', 'pos5', 'pos6'
		])

	def testGetStems(self):
		s = Sentence(TEST_TOKENS)
		s.addAnnotation('mask', 2, 4)
		s.addAnnotation('mask', 6)
		self.assertListEqual(list(s.stems(3, 7)), [
			'stem3', 'stem4', 'stem5', 'stem6'
		])

	def testGetWords(self):
		s = Sentence(TEST_TOKENS)
		s.addAnnotation('mask', 2, 4)
		s.addAnnotation('mask', 6)
		s.addAnnotation('mask', 8, 9)
		self.assertListEqual(list(s.words()), [
			'word%d' % i for i in range(len(s))
		])
		self.assertListEqual(list(s.words(7)), [
			'word7', 'word8', 'word9'
		])


class TestAnnotation(TestCase):

	def testEquals(self):
		s = Sentence(TEST_TOKENS)
		a1 = Annotation(s, 1, 2)
		a2 = Annotation(s, 1, 2)
		self.assertEqual(a1, a2)

	def testComparator(self):
		s = Sentence(TEST_TOKENS)
		n = Annotation(s, 2, 5)

		for i in range(1, 7):
			self.assertTrue(n > Annotation(s, 0, i), i)

		for i in range(3, 7):
			self.assertTrue(n < Annotation(s, i, 7), i)

		self.assertTrue(n > Annotation(s, 1, 6))
		self.assertTrue(n < Annotation(s, 3, 4))
		self.assertTrue(n == Annotation(s, 2, 5))

	def testComparatorTypeError(self):
		s = Sentence(TEST_TOKENS)
		n = Annotation(s, 2, 5)
		self.assertRaises(TypeError, lambda: n < s)

	def testComparatorValueError(self):
		s1 = Sentence(TEST_TOKENS)
		n1 = Annotation(s1, 2, 5)
		s2 = Sentence(TEST_TOKENS)
		n2 = Annotation(s2, 2, 5)
		self.assertRaises(ValueError, lambda: n1 < n2)

	def testGetPhraseNumber(self):
		s = Sentence(TEST_TOKENS)
		a1 = s.addAnnotation('t', 8)
		a2 = s.addAnnotation('t', 0, 2)
		a3 = s.addAnnotation('t', 4)
		self.assertEqual(a1.getPhraseNumber_(), 0)
		self.assertEqual(a2.getPhraseNumber_(), 1)
		self.assertEqual(a3.getPhraseNumber_(), 2)

	def testGetPhraseNumberFailure(self):
		s = Sentence(TEST_TOKENS)
		a1 = s.addAnnotation('true', 0, 5)
		a2 = s.addAnnotation('true', 2, 9)
		self.assertRaises(ValueError, a1.getPhraseNumber_)
		self.assertRaises(ValueError, a2.getPhraseNumber_)

	def testGetPhraseOffset(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('mask', 1)
		self.assertEqual(a.getPhraseOffset(), (0, 2))

	def testGetPhraseOffsetMultiPhrase(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('mask', 4, 7)
		self.assertEqual(a.getPhraseOffset(), (4, 7))

	def testGetPhraseOffsetOutside(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('mask', 2)
		self.assertEqual(a.getPhraseOffset(), (2, 3))

	def testGetPhraseStems(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('mask', 3)
		self.assertListEqual(list(a.getPhraseStems()), ['mask', 'stem4'])

	def testGetPhraseStemsMultiPhrase(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('mask', 3, 8)
		self.assertListEqual(list(a.getPhraseStems()), ['mask']*5)

	def testGetPhraseTag(self):
		s = Sentence(TEST_TOKENS)
		a1 = s.addAnnotation('t', 2)
		a2 = s.addAnnotation('t', 0, 2)
		a3 = s.addAnnotation('t', 4)
		self.assertEqual(a1.getPhraseTag_(), 'O')
		self.assertEqual(a2.getPhraseTag_(), 'NP')
		self.assertEqual(a3.getPhraseTag_(), 'NP')

	def testGetPhraseTagFailure(self):
		s = Sentence(TEST_TOKENS)
		a1 = s.addAnnotation('true', 0, 5)
		a2 = s.addAnnotation('true', 2, 9)
		self.assertRaises(ValueError, a1.getPhraseTag_)
		self.assertRaises(ValueError, a2.getPhraseTag_)

	def testGetPhraseWords(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('mask', 1)
		self.assertListEqual(list(a.getPhraseWords()), ['word0', 'mask'])

	def testGetPhraseWordsOutside(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('mask', 2)
		self.assertListEqual(list(a.getPhraseWords()), ['mask'])

	def testGetPrepositionedNounPhrase(self):
		tokens = list(TEST_TOKENS)
		tokens[3] = tokens[3].replace(chunk="B-PP")
		tokens[4] = tokens[4].replace(chunk="I-PP")
		s = Sentence(tokens)
		s.addAnnotation('sentinel', 0)
		a = s.addAnnotation('type', 6)
		self.assertListEqual(list(a.getPrepositionedNounPhrase_()),
		                     ['sentinel', 'stem1'])

	def testIsInsidePhrase(self):
		s = Sentence(TEST_TOKENS)
		a1 = s.addAnnotation('true', 3)
		a2 = s.addAnnotation('true', 0, 2)
		a3 = s.addAnnotation('false', 8)
		self.assertTrue(a1.isInsidePhrase())
		self.assertTrue(a2.isInsidePhrase())
		self.assertTrue(a3.isInsidePhrase())

	def testIsNotInsidePhrase(self):
		s = Sentence(TEST_TOKENS)
		a1 = s.addAnnotation('false', 1, 3)
		self.assertFalse(a1.isInsidePhrase())

	def testPhraseDistanceOnDifferentSentences(self):
		s1 = Sentence(TEST_TOKENS)
		s2 = Sentence(TEST_TOKENS)
		a1 = s1.addAnnotation('type', 0, 2)
		a2 = s2.addAnnotation('type', 6, 8)
		self.assertRaises(ValueError, a1.phraseDistanceTo, a2)

	def testPhraseDistance(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('A', 0, 2)
		b = s.addAnnotation('B', 3)
		c = s.addAnnotation('C', 6, 8)
		d = s.addAnnotation('D', 9)
		e = s.addAnnotation('E', 3, 5)

		for other, dist in [(a, 1), (b, 1), (c, -1), (d, 0), (e, 0)]:
			self.assertEqual(c.phraseDistanceTo(other), dist, msg=repr(other))

	def testPhraseDistanceIfOverlapping(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('A', 0, 2)
		b = s.addAnnotation('B', 1)
		c = s.addAnnotation('C', 7)
		d = s.addAnnotation('D', 6, 8)
		self.assertEqual(a.phraseDistanceTo(b), 0)
		self.assertEqual(c.phraseDistanceTo(d), 0)

	def testPhraseDistanceIfSelfNotInPhrase(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('A', 2)
		b = s.addAnnotation('B', 9)
		self.assertEqual(a.phraseDistanceTo(b), 2)

	def testPhraseDistanceIfOtherNotInPhrase(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('A', 3, 5)
		b = s.addAnnotation('B', 8)
		self.assertEqual(a.phraseDistanceTo(b), 1)

	def testPhraseDistanceIfBothNotInPhrase(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('A', 2)
		b = s.addAnnotation('B', 5)
		self.assertEqual(a.phraseDistanceTo(b), 1)

	def testPhraseDistanceIfBothInOverlappingPhrase(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('A', 0, 5)
		b = s.addAnnotation('B', 6, 10)
		self.assertEqual(a.phraseDistanceTo(b), 0)

	def testPhraseNumbersTo(self):
		s = Sentence(TEST_TOKENS)
		a1 = s.addAnnotation('true', 5)
		a2 = s.addAnnotation('true', 0, 2)
		a3 = s.addAnnotation('true', 3, 5)
		a0 = s.addAnnotation('true', 0)
		a9 = s.addAnnotation('true', 9)
		self.assertEqual(list(a1.phraseNumbersBetween(a2)), [2])
		self.assertEqual(list(a1.phraseNumbersBetween(a1)), [])
		self.assertEqual(list(a2.phraseNumbersBetween(a3)), [])
		self.assertEqual(list(a0.phraseNumbersBetween(a9)), [1, 2, 3])

	def testPhraseTagsTo(self):
		s = Sentence(TEST_TOKENS)
		a1 = s.addAnnotation('true', 5)
		a2 = s.addAnnotation('true', 0, 2)
		a3 = s.addAnnotation('true', 3, 5)
		a0 = s.addAnnotation('true', 0)
		a9 = s.addAnnotation('true', 9)
		self.assertEqual(list(a1.phraseTagsBetween(a2)), ['NP'])
		self.assertEqual(list(a1.phraseTagsBetween(a1)), [])
		self.assertEqual(list(a2.phraseTagsBetween(a3)), [])
		self.assertEqual(list(a0.phraseTagsBetween(a9)), ['NP', 'NP', 'NP'])

	def testPosTagsTo(self):
		s = Sentence(TEST_TOKENS)
		a1 = s.addAnnotation('true', 5)
		a2 = s.addAnnotation('true', 0, 2)
		a3 = s.addAnnotation('true', 3, 5)
		a0 = s.addAnnotation('true', 0)
		a9 = s.addAnnotation('true', 9)
		self.assertEqual(list(a1.posTagsBetween(a2)), ['pos2', 'pos3', 'pos4'])
		self.assertEqual(list(a1.posTagsBetween(a1)), [])
		self.assertEqual(list(a2.posTagsBetween(a3)), ['pos2'])
		self.assertEqual(list(a0.posTagsBetween(a9)), ['pos%d' % i for i in range(1, 9)])

	def testTokenDistanceOnDifferentSentences(self):
		s1 = Sentence(TEST_TOKENS)
		s2 = Sentence(TEST_TOKENS)
		a1 = s1.addAnnotation('type', 0, 2)
		a2 = s2.addAnnotation('type', 6, 8)
		self.assertRaises(ValueError, a1.tokenDistanceTo, a2)

	def testTokenDistance(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('A', 0, 2)
		b = s.addAnnotation('B', 3)
		c = s.addAnnotation('C', 6, 8)
		d = s.addAnnotation('D', 8)
		e = s.addAnnotation('E', 4, 6)

		for other, dist in [(a, 4), (b, 2), (d, 0), (e, 0)]:
			self.assertEqual(c.tokenDistanceTo(other), dist)

	def testTokenDistanceIfEqual(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('A', 0, 2)
		b = s.addAnnotation('B', 0, 2)
		self.assertEqual(a.tokenDistanceTo(b), -2)

	def testTokenDistanceIfOverlapping(self):
		s = Sentence(TEST_TOKENS)
		a = s.addAnnotation('A', 2, 4)
		b = s.addAnnotation('B', 2, 3)
		c = s.addAnnotation('C', 1, 3)
		d = s.addAnnotation('D', 0, 2)
		e = s.addAnnotation('E', 1, 2)

		for other in [a, b, d, e]:
			self.assertEqual(c.tokenDistanceTo(other), -1)

	def testVerbPhraseBetween(self):
		tokens = list(TEST_TOKENS)
		tokens[3] = tokens[3].replace(chunk="B-VP", stem="sentinel1")
		tokens[4] = tokens[4].replace(chunk="I-VP", stem="sentinel2")
		s = Sentence(tokens)
		this = s.addAnnotation('this', 0)
		other = s.addAnnotation('other', 6)
		self.assertListEqual(list(this.verbPhraseBetween(other)),
		                     ['sentinel1', 'sentinel2'])

	def testVerbPhraseBetweenOverlaps(self):
		tokens = list(TEST_TOKENS)
		tokens[0] = tokens[0].replace(chunk="B-VP")
		tokens[1] = tokens[1].replace(chunk="I-VP", stem="sentinel")
		s = Sentence(tokens)
		this = s.addAnnotation('this', 0)
		other = s.addAnnotation('other', 3)
		self.assertListEqual(list(this.verbPhraseBetween(other)),
		                     ['this', 'sentinel'])

	def testVerbPhraseBetweenExactOverlap(self):
		tokens = list(TEST_TOKENS)
		tokens[0] = tokens[0].replace(chunk="B-VP")
		tokens[1] = tokens[1].replace(chunk="I-VP", stem="sentinel")
		s = Sentence(tokens)
		this = s.addAnnotation('this', 3)
		other = s.addAnnotation('other', 3)
		self.assertEqual(this.verbPhraseBetween(other), None)


class TestSentenceParser(TestCase):

	LINES = """
1406630	0	Selection	Selection	NN	B-NP	O	O	O	#  commentary stuff
1406630	0	of	of	IN	B-PP	O	O	O
1406630	0	optimal	optimal	JJ	B-NP	O	O	O
1406630	0	kappa	kappa	NN	I-NP	O	O	O
1406630	0	B	B	NN	I-NP	O	O	O
1406630	0	/	/	NN	I-NP	O	O	O
1406630	0	Rel	Rel	NN	I-NP	O	O	O
1406630	0	DNA	DNA	JJ	I-NP	O	O	O
1406630	0	binding	binding	JJ	I-NP	O	O	B-PBLD
1406630	0	.	.	.	O	O	O	O

1406630	1	Analysis	Analysis	NN	B-NP	O	O	O
1406630	1	of	of	IN	B-PP	O	O	O
1406630	1	the	the	DT	B-NP	O	O	O
1406630	1	p	p	NN	I-NP	B-gene	O	B-NFKB1
1406630	1	50	50	NN	I-NP	I-gene	O	I-NFKB1
1406630	1	and	and	CC	I-NP	O	O	O
1406630	1	p	p	NN	I-NP	B-gene	O	B-RELA
1406630	1	65	65	NN	I-NP	I-gene	O	I-RELA
1406630	1	subunits	subunit	NNS	I-NP	I-gene	O	O
1406630	1	.	.	.	O	O	O	O

1406630	2	In	In	IN	B-PP	O	O	O
1406630	2	addition	addition	NN	B-NP	O	O	B-EXTRA
1406630	2	,	,	,	O	O	O	O
1406630	2	the	the	DT	B-NP	O	O	O
1406630	2	product	product	NN	I-NP	O	O	O
1406630	2	of	of	IN	B-PP	O	O	O
1406630	2	the	the	DT	B-NP	O	O	O
1406630	2	proto	proto	NN	I-NP	O	O	O
1406630	2	oncogene	oncogene	NN	I-NP	O	O	O
1406630	2	.	.	.	O	O	O	O

1406630	3	However	However	RB	B-ADVP	O	O	O
1406630	3	,	,	,	O	O	O	O
1406630	3	these	these	DT	B-NP	O	O	O
1406630	3	studies	study	NNS	I-NP	O	O	O
1406630	3	have	have	VBP	B-VP	O	O	B-EXTRA
1406630	3	used	use	VBN	I-VP	O	O	O
1406630	3	a	a	DT	B-NP	O	O	O
1406630	3	limited	limit	VBN	I-NP	O	O	O
1406630	3	number	number	NN	I-NP	O	O	O
1406630	3	.	.	.	O	O	O	O

1406630	4	Using	Use	VBG	B-VP	O	O	O
1406630	4	purified	purify	VBN	B-NP	O	O	O
1406630	4	recombinant	recombinant	JJ	I-NP	O	O	O
1406630	4	p	p	NN	I-NP	B-gene	O	B-NFKB1
1406630	4	50	50	NN	I-NP	I-gene	O	I-NFKB1
1406630	4	,	,	,	O	O	O	O
1406630	4	p	p	NN	B-NP	B-gene	O	B-RELA
1406630	4	65	65	NN	I-NP	I-gene	O	I-RELA
1406630	4	,	,	,	O	O	O	O
1406630	4	.	.	.	O	O	O	O

1406630	5	Alignment	Alignment	NN	B-NP	O	O	O
1406630	5	of	of	IN	B-PP	O	O	O
1406630	5	the	the	DT	B-NP	O	O	O
1406630	5	selected	select	VBN	I-NP	O	O	O
1406630	5	sequences	sequence	NNS	I-NP	O	O	O
1406630	5	allowed	allow	VBD	B-VP	O	O	B-EXTRA
1406630	5	us	us	PRP	B-NP	O	O	O
1406630	5	to	to	TO	B-VP	O	O	O
1406630	5	predict	predict	VB	I-VP	O	O	O
1406630	5	.	.	.	O	O	O	O
""".split('\n')

	SENTENCE_IDS = [
		("1406630", "0"),
		("1406630", "1"),
		("1406630", "2"),
		("1406630", "3"),
		("1406630", "4"),
		("1406630", "5"),
	]

	def testSentenceParser(self):
		for i, (sent_id, sentence) in enumerate(SentenceParser(self.LINES, ("ENTITY_A", "ENTITY_B"))):
			self.assertEqual(len(sentence), 10)
			self.assertEqual(sentence.tokens[-1].pos, '.')
			self.assertEqual(sentence.tokens[-1].pos, '.')
			self.assertEqual(sent_id, self.SENTENCE_IDS[i])
			self.assertTrue(sentence.getAnnotations('ENTITY_B'), sent_id)
			self.assertFalse(sentence.getAnnotations('ENTITY_A'), sent_id)

if __name__ == '__main__':
	main()
