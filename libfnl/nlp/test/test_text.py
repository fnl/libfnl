from hashlib import sha256
from libfnl.nlp.text import Binary, Unicode, AnnotatedContent
from unittest import main, TestCase

__author__ = 'Florian Leitner'


class AnnotatedContentTests(TestCase):

    def setUp(self):
        self.doc = AnnotatedContent()

    def testCreateUnnamedDoc(self):
        self.assertEqual(self.doc._tags, {})

    def testDelOnlyTag(self):
        self.doc._tags = {"ns": {(1,): "val"}}
        self.doc.delTag("ns", 1)
        self.assertDictEqual(self.doc._tags, {})

    def testDelTagOfMany(self):
        self.doc._tags = {"ns": {(1,): "val", (1,2): "val"}}
        self.doc.delTag("ns", 1, 2)
        self.assertDictEqual(self.doc._tags, {"ns": {(1,): "val"}})

    def testDelNonExistingTag(self):
        self.doc._tags = {"ns": {(1,): "val", (1,2): "val"}}
        self.assertRaises(KeyError, self.doc.delTag, "ns", 2)
        self.assertRaises(KeyError, self.doc.delTag, "wrong", 1)

    def testGetTags(self):
        self.doc._tags = {"ns": {(1,): "val", (1,2): "val"}}
        ns = self.doc.getTags("ns")
        self.assertDictEqual(ns, {(1,): "val", (1,2): "val"})

    def testGetValue(self):
        self.doc._tags = {"ns": {(1,2): "val"}}
        self.assertSequenceEqual(self.doc.getValue("ns", 1, 2), "val")

    def testIterNamespaces(self):
        self.doc._tags = {"ns": {(1,): "val"}, "nb": {(1,): "val"}}
        nss = sorted(tuple(self.doc.iterNamespaces()))
        self.assertSequenceEqual(nss, ("nb", "ns"))

    def testIterTags(self):
        self.doc._tags = {"ns": {(1,): "val", (1,2): "val"}}
        anns = tuple(self.doc.iterTags("ns"))
        self.assertSequenceEqual(anns, (((1,2), "val"), ((1,), "val")))

    def testIterTagsOrdering(self):
        self.doc._tags = {"ns": {
            (2,): "v", (1,2,5,6): "v", (1,3,5): "v", (1,5): "v"
        }}
        anns = tuple(self.doc.iterTags("ns"))
        self.assertSequenceEqual(
            anns, ( ((1,2,5,6), "v"), ((1,3,5), "v"), ((1,5), "v"), ((2,), "v") )
        )

    def testTags(self):
        self.doc._tags = {
            "ns1": {
                (2,): "v1", (1,2,5,6): "v2", (1,3,5): "v3", (1,4,5): "v4"
            },
            "ns2": {
                (3,): "v5", (1,6): "v6", (1,4): "v7", (3,5): "v8"
            }
        }
        self.assertListEqual(self.doc.tags(), [
                ((1,2,5,6), "ns1", "v2"),
                ((1,6),     "ns2", "v6"),
                ((1,3,5),   "ns1", "v3"),
                ((1,4,5),     "ns1", "v4"),
                ((1,4),     "ns2", "v7"),
                ((2,),      "ns1", "v1"),
                ((3,5),     "ns2", "v8"),
                ((3,),      "ns2", "v5"),
        ])


class BinaryTests(TestCase):

    def setUp(self):
        self.binary = Binary("test", "latin1")

    def testCreateBinary(self):
        self.assertEqual(self.binary.encoding, "latin1")
        self.assertEqual(self.binary._digest, None)
        self.assertEqual(self.binary._str_alignment, dict())

    def testLen(self):
        self.assertEqual(len(self.binary), 4)

    def testAddTag(self):
        self.binary.addTag("ns", "val", 1)
        self.assertDictEqual(self.binary._tags, {"ns": {(1,): "val"}})

    def testAddTagWithMultipleOffsets(self):
        self.binary.addTag("ns", "val", 1, 2, 3, 4)
        self.assertDictEqual(self.binary._tags, {"ns": {(1,2,3,4): "val"}})

    def assertAddRaisesAssertionError(self, *args):
        self.assertRaises(AssertionError, self.binary.addTag, *args)

    def testAddDuplicateTag(self):
        self.binary.addTag("ns", "val", 1)
        self.assertAddRaisesAssertionError("ns", "val", 1)

    def testAddTagAfterLenOfContent(self):
        self.assertAddRaisesAssertionError("ns", "val", 5)
        self.assertAddRaisesAssertionError("ns", "val", 0, 5)

    def testAddTagWithEndBeforeStart(self):
        self.assertAddRaisesAssertionError("ns", "val", 2, 1)

    def testAddTagWithNegativeStart(self):
        self.assertAddRaisesAssertionError("ns", "val", -2)

    def testAddTagWithBadOffsets(self):
        self.assertAddRaisesAssertionError("ns", "val", 0, 1, 2)

    def testDigest(self):
        self.assertEqual(self.binary.digest,
                         sha256("test".encode("latin1")).digest())

    def testHexdigest(self):
        self.assertEqual(self.binary.hexdigest,
                         sha256("test".encode("latin1")).hexdigest())

    def testToText(self):
        text = self.binary.toUnicode()
        binary = text.toBinary("latin1")
        self.assertSequenceEqual(binary, self.binary)
        self.assertDictEqual(binary._tags, self.binary._tags)

    def testToTextWithTags(self):
        self.binary = Binary(b'\xc3\xa4\xc4\xb5\xce\x95\xf0\x90\x80\x80a',
                             "utf-8")
        # bytes    \xc3\xa4\xc4\xb5\xce\x95\xf0\x90\x80\x80a
        # binary   0   1   2   3   4   5   6   7   8   9   0 len(11)
        # unicode  ä       ĵ       Epsilon \uD800  \uDC00  a
        # text     0       1       2       3       4*surr  5 len(6)
        self.binary._tags = {
            "ns1": {
                (2,): "v1", (0,2,4,10): "v2", (4,6): "v3", (6,10): "v4"
            },
            "ns2": {
                (0,4): "v5", (2,6): "v6", (4,10): "v7", (6,11): "v8"
            }
        }
        binary = self.binary.toUnicode().toBinary("utf-8")
        self.assertSequenceEqual(binary, self.binary)
        self.assertDictEqual(binary._tags, self.binary._tags)


class TextTests(TestCase):

    def setUp(self):
        self.text = Unicode("test")

    def testLen(self):
        self.assertEqual(len(self.text), 4)

    def testAddTag(self):
        self.text.addTag("ns", "val", 1)
        self.assertDictEqual(self.text._tags, {"ns": {(1,): "val"}})

    def testAddTagWithMultipleOffsets(self):
        self.text.addTag("ns", "val", 1, 2, 3, 4)
        self.assertDictEqual(self.text._tags, {"ns": {(1,2,3,4): "val"}})

    def assertAddRaisesAssertionError(self, *args):
        self.assertRaises(AssertionError, self.text.addTag, *args)

    def testAddDuplicateTag(self):
        self.text.addTag("ns", "val", 1)
        self.assertAddRaisesAssertionError("ns", "val", 1)

    def testAddTagAfterLenOfContent(self):
        self.assertAddRaisesAssertionError("ns", "val", 5)
        self.assertAddRaisesAssertionError("ns", "val", 0, 5)

    def testAddTagWithEndBeforeStart(self):
        self.assertAddRaisesAssertionError("ns", "val", 2, 1)

    def testAddTagWithNegativeStart(self):
        self.assertAddRaisesAssertionError("ns", "val", -2)

    def testAddTagWithBadOffsets(self):
        self.assertAddRaisesAssertionError("ns", "val", 0, 1, 2)

    def testGetMultispan(self):
        self.assertSequenceEqual(
            self.text.getMultispan(0, 1, 2, 4), ["t", "st"]
        )

    def testGetMultispanWithBadOffsetKey(self):
        self.assertRaises(AssertionError, self.text.getMultispan, 0, 1, 2)

    def testGetSpan(self):
        self.assertSequenceEqual(self.text[1:3], "es")

    def testToBinary(self):
        text = self.text.toBinary("latin1").toUnicode()
        self.assertSequenceEqual(text, self.text)
        self.assertDictEqual(text._tags, self.text._tags)


if __name__ == '__main__':
    main()
