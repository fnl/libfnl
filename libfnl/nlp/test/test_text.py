from hashlib import md5
from libfnl.couch.serializer import b64encode
from libfnl.nlp.text import Binary, Unicode, Annotated
from sys import maxsize
from unittest import main, TestCase

__author__ = 'Florian Leitner'

class AnnotatedContentTests(TestCase):

    def setUp(self):
        self.doc = Annotated()
        self.tags = {"ns": {"tag": [(1,)]}}

    def testCreateUnnamedDoc(self):
        self.assertEqual(self.doc._tags, {})

    def testFetchingTagsCopiesEntireStructure(self):
        self.doc._tags = self.tags
        real = self.tags
        orig = self.doc._tags
        copied = self.doc.tags
        # new section_ns dictionary
        self.assertEqual(id(real), id(orig))
        self.assertNotEqual(id(copied), id(orig))
        # new key dictionary
        self.assertEqual(id(real["ns"]), id(orig["ns"]))
        self.assertNotEqual(id(copied["ns"]), id(orig["ns"]))
        # new offset list
        self.assertEqual(id(real["ns"]["tag"]), id(orig["ns"]["tag"]))
        self.assertNotEqual(id(copied["ns"]["tag"]), id(orig["ns"]["tag"]))
        # BUT: no new offset tuples!!
        self.assertEqual(id(real["ns"]["tag"][0]), id(orig["ns"]["tag"][0]))
        self.assertEqual(id(copied["ns"]["tag"][0]), id(orig["ns"]["tag"][0]))

    def testDelNamespace(self):
        self.doc.tags = self.tags
        self.doc.delNamespace("ns")
        self.assertDictEqual(self.doc._tags, {})

    def testDelNonExistingNamespace(self):
        self.doc.tags = self.tags
        self.assertRaises(KeyError, self.doc.delNamespace, "ns2")

    def testDelOnlyKey(self):
        self.doc.tags = self.tags
        self.doc.delKey("ns", "tag")
        self.assertDictEqual(self.doc._tags, {})

    def testDelKeyOfMany(self):
        self.doc.tags = {"ns": {"tag": [(1,)], "tag2": [(2,)]}}
        self.doc.delKey("ns", "tag2")
        self.assertDictEqual(self.doc._tags, self.tags)

    def testDelOnlyKeyInMultinamespace(self):
        self.doc.tags = {"ns": {"tag": [(1,)]}, "ns2": {"tag2": [(2,)]}}
        self.doc.delKey("ns2", "tag2")
        self.assertDictEqual(self.doc._tags, self.tags)

    def testDelNonExistingTag(self):
        self.doc.tags = self.tags
        self.assertRaises(KeyError, self.doc.delKey, "ns", "tag2")

    def testDelOffset(self):
        self.doc.tags = self.tags
        self.doc.delOffset("ns", "tag", (1,))
        self.assertDictEqual(self.doc._tags, {})

    def testDelOffsetOfMany(self):
        self.doc.tags = {"ns": {"tag": [(1,), (2,)]}}
        self.doc.delOffset("ns", "tag", (2,))
        self.assertDictEqual(self.doc._tags, self.tags)

    def testDelOnlyOffsetInMultikey(self):
        self.doc.tags = {"ns": {"tag": [(1,)], "tag2": [(2,)]}}
        self.doc.delOffset("ns", "tag2", (2,))
        self.assertDictEqual(self.doc._tags, self.tags)

    def testNamespaces(self):
        self.doc._tags = {"ns": {"tag": [(1,)]}, "ns2": {"tag2": [(2,)]}}
        ns = list(sorted(self.doc.namespaces()))
        self.assertListEqual(["ns", "ns2"], ns)

    def testKeys(self):
        self.doc._tags = {"ns": {"tag": [(1,)], "tag2": [(2,)]}}
        keys = list(sorted(self.doc.keys("ns")))
        self.assertListEqual(["tag", "tag2"], keys)

    def testOffsets(self):
        self.doc._tags = {"ns": {"tag": [(2,), (1,)]}}
        offsets = self.doc.offsets("ns", "tag")
        self.assertListEqual([(2,), (1,)], offsets)

    def testOffsetsSorted(self):
        self.doc._tags = {"ns": {"tag": [(2,), (1,)]}}
        offsets = list(self.doc.offsets("ns", "tag", sort=True))
        self.assertListEqual([(1,), (2,)], offsets)

    def testSort(self):
        self.doc._tags = {"ns": {"tag": [(2,), (1,)]}}
        self.doc.sort()
        offsets = self.doc.offsets("ns", "tag")
        self.assertListEqual([(1,), (2,)], offsets)

    def testSortNamespace(self):
        self.doc._tags = {"ns": {"tag": [(2,), (1,)]}}
        self.doc.sort("ns")
        offsets = self.doc.offsets("ns", "tag")
        self.assertListEqual([(1,), (2,)], offsets)

    def testSortKey(self):
        self.doc._tags = {"ns": {"tag": [(2,), (1,)]}}
        self.doc.sort("ns", "tag")
        offsets = self.doc.offsets("ns", "tag")
        self.assertListEqual([(1,), (2,)], offsets)

    def testIterTags(self):
        self.doc._tags = {
            "ns1": { "k1": [(1,), (2,)] },
            "ns2": { "k2": [(3,)], "k3": [(4,)] }
        }
        self.assertListEqual(list(sorted(self.doc.iterTags())), [
            ("ns1", "k1", (1,)),
            ("ns1", "k1", (2,)),
            ("ns2", "k2", (3,)),
            ("ns2", "k3", (4,)),
        ])


class BinaryTests(TestCase):

    def setUp(self):
        self.binary = Binary("test", "latin1")

    def testCreateBinary(self):
        self.assertDictEqual(self.binary._tags, {})
        self.assertEqual(self.binary.encoding, "latin1")
        self.assertEqual(self.binary._digest, None)
        self.assertEqual(self.binary._str_alignment, dict())

    def testLen(self):
        self.assertEqual(len(self.binary), 4)

    def testAddTag(self):
        self.binary.addTag("ns", "key", (1,))
        self.assertDictEqual(self.binary._tags, {"ns": {"key": [(1,)]}})

    def testAddDuplicateTag(self):
        self.binary.addTag("ns", "val", (1,))
        self.binary.addTag("ns", "val", (1,))
        self.assertDictEqual(self.binary._tags, {"ns": {"val": [(1,), (1,)]}})

    def assertAddRaisesAssertionError(self, *args):
        self.assertRaises(AssertionError, self.binary.addTag, *args)

    def testAddTagAfterLenOfContent(self):
        self.assertAddRaisesAssertionError("ns", "val", (5,))
        self.assertAddRaisesAssertionError("ns", "val", (0, 5))

    def testAddTagWithEndBeforeStart(self):
        self.assertAddRaisesAssertionError("ns", "val", (2, 1))

    def testAddTagWithNegativeStart(self):
        self.assertAddRaisesAssertionError("ns", "val", (-2,))

    def testAddTagWithBadOffsets(self):
        self.assertAddRaisesAssertionError("ns", "val", (0, 1, 2))

    def testDigest(self):
        self.assertEqual(self.binary.digest(),
                         md5("test".encode("latin1")).digest())

    def testBase64digest(self):
        expected = b64encode(
            md5("test".encode("latin1")).digest()
        )[:-2].decode('ascii')
        self.assertEqual(expected, self.binary.base64digest())

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
                "key1": [(2,), (0,2,4,10), (4,6), (6,10)]
            },
            "ns2": {
                "key2": [(0,4), (2,6), (4,10), (6,11)]
            }
        }
        binary = self.binary.toUnicode().toBinary("utf-8")
        self.assertSequenceEqual(binary, self.binary)
        self.assertDictEqual(binary._tags, self.binary._tags)

    def testUnicodeError(self):
        self.binary = Binary(b'\xc3\xa4\xc4\xb5\xce\x95\xf0\x90\x80\x80a',
                             "utf-8")
        self.binary._tags = {"ns1": {"key1": [(1,)]}}
        self.assertRaises(UnicodeDecodeError, self.binary.toUnicode)


class TextTests(TestCase):

    def setUp(self):
        self.text = Unicode("test")

    def testLen(self):
        self.assertEqual(len(self.text), 4)

    def testAddTag(self):
        self.text.addTag("ns", "val", (1,))
        self.assertDictEqual(self.text._tags, {"ns": {"val": [(1,)]}})

    def testAddDuplicateTag(self):
        self.text.addTag("ns", "val", (1,))
        self.text.addTag("ns", "val", (1,))
        self.assertDictEqual(self.text._tags, {"ns": {"val": [(1,), (1,)]}})

    def assertAddRaisesAssertionError(self, *args):
        self.assertRaises(AssertionError, self.text.addTag, *args)

    def testAddTagAfterLenOfContent(self):
        self.assertAddRaisesAssertionError("ns", "val", (5,))
        self.assertAddRaisesAssertionError("ns", "val", (0, 5))

    def testAddTagWithEndBeforeStart(self):
        self.assertAddRaisesAssertionError("ns", "val", (2, 1))

    def testAddTagWithNegativeStart(self):
        self.assertAddRaisesAssertionError("ns", "val", (-2,))

    def testAddTagWithBadOffsets(self):
        self.assertAddRaisesAssertionError("ns", "val", (0, 1, 2))

    def testGetMultispan(self):
        self.assertSequenceEqual(
            self.text.getMultispan((0, 1, 2, 4)), ["t", "st"]
        )

    def testGetMultispanWithBadOffsetKey(self):
        self.assertRaises(AssertionError, self.text.getMultispan, (0, 1, 2))

    def testGetSpan(self):
        self.assertSequenceEqual(self.text[1:3], "es")

    def testToBinary(self):
        text = self.text.toBinary("latin1").toUnicode()
        self.assertSequenceEqual(text, self.text)
        self.assertDictEqual(text._tags, self.text._tags)

    def testUnicodeError(self):
        if maxsize == 0x7FFFFFFF:
            self.text = Binary(b'\xc3\xa4\xc4\xb5\xce\x95\xf0\x90\x80\x80a',
                               "utf-8").toUnicode()
            self.text._tags = {"ns1": {"key1": [(4,)]}}
            self.assertRaises(UnicodeEncodeError, self.text.toBinary, "utf-8")


if __name__ == '__main__':
    main()
