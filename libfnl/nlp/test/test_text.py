from _collections import defaultdict
from collections import OrderedDict
from hashlib import md5
from libfnl.couch.serializer import b64encode
from libfnl.nlp.text import Text
from mock import patch
from unittest import main, TestCase

__author__ = 'Florian Leitner'

T = Text.Tag

class TextTests(TestCase):

    def testInitialization(self):
        text = Text('text')
        self.assertListEqual(list(), list(text.tags))
        self.assertDictEqual(dict(), text.attributes)

    def testInitializationWithJunk(self):
        self.assertRaises(TypeError, Text, 10)
        self.assertRaises(TypeError, Text, object())
        self.assertRaises(TypeError, Text, tuple('string'))

    @staticmethod
    def buildTagtree(tags):
        return TextTests._build(tags, lambda t: (t[0], t[1]))

    @staticmethod
    def buildOffsets(tags):
        return TextTests._build(tags, lambda t: (t[2][0], t[2][-1]))

    @staticmethod
    def _build(tags, Keys):
        tree = defaultdict(dict)

        for tag in tags:
            k1, k2 = Keys(tag)
            node = tree[k1]
            if k2 in node: node[k2].add(T(*tag))
            else: node[k2] = {T(*tag)}

        return dict(tree)

    def compareTrees(self, expected, received):
        for k1, values in received.items():
            self.assertTrue(k1 in expected, 'missing outer key {}'.format(k1))
            evalues = expected[k1]

            for k2, tags in values.items():
                self.assertTrue(k2 in evalues,
                                'missing inner key {}'.format(k2))
                self.assertSetEqual(evalues[k2], set(tags))

    def testInitializationWithTagAttributes(self):
        tag1 = ('ns', 'key', (0, 1))
        tag2 = ('ns', 'key', (1, 2))
        tag3 = ('ns', 'key', (2, 3))
        tag4 = ('ns', 'key', (3, 4))
        tags = [T(*tag1), T(*tag2), T(*tag3), T(*tag4)]
        text = Text('text', {tag1: {'n': 'v'}, tag2: [('dict', 'like')],
                             tag3: ['kv'], tag4: None})
        self.assertListEqual(tags, list(text.tags))
        self.compareTrees(self.buildTagtree(tags), text.tagtree)
        self.compareTrees(self.buildOffsets(tags), text.offsets)
        self.assertDictEqual({T(*tag1): {'n': 'v'},
                              T(*tag2): {'dict': 'like'},
                              T(*tag3): {'k': 'v'}}, text.attributes)

    def testTagInitializationUnicode(self):
        tag1 = ('ns1', 'key1', (0, 3))
        tag2 = ('ns1', 'key1', (1, 2))
        tag3 = ('ns2', 'key2', (2, 3))
        tags = [T(*tag1), T(*tag2), T(*tag3)]
        text = Text('a\U0010ABCDb', [tag1, tag2, tag3, tag1, tag2])
        self.assertListEqual(tags, list(text.tags))
        self.compareTrees(self.buildTagtree(tags), text.tagtree)
        self.compareTrees(self.buildOffsets(tags), text.offsets)

    def testInitializationWithInvalidTagAttributes(self):
        tag = ('ns', 'key', (1, 2))
        self.assertRaises(ValueError, Text, 'text', {tag: ['mist']})
        self.assertRaises(ValueError, Text, 'text',
                          {tag: [('fake', 'dict', 'like')]})
        self.assertRaises(TypeError, Text, 'text',
                          {tag: 1})

    # Special and Private Methods

    def testContains(self):
        tag2, tag1 = T('ns', 'key', (1,2)), T('ns', 'key', (0,2))
        text = Text('n\U0010ABCDn', [tag1])
        self.assertTrue(tag1 in text)
        self.assertFalse(tag2 in text)
        self.assertFalse(('ns', 'key', object()) in text)
        self.assertFalse(('ns', object(), (1, 2)) in text)
        self.assertFalse((object(), 'key', (1, 2)) in text)

    def testDelitem(self):
        tag2, tag1 = T('ns', 'key', (1,3)), T('ns', 'key', (0,2))
        text = Text('n\U0010ABCDn', [tag1, tag2])
        del text[0]
        self.assertEqual([tag2], list(text.tags))

    def testEq(self):
        text1 = Text('n\U0010ABCDn', [('ns', 'key', (0,3))])
        text2 = Text(text1)
        text2.attributes[('ns', 'key', (0,3))] = {'a': 'v'}
        self.assertEqual(text1, text2)
        self.assertFalse(text1 is text2)

    def testIter(self):
        tags = OrderedDict([
            (T('a', 'a', (0,5)), None),
            (T('a', 'a', (1,4)), None),
            (T('a', 'b', (1,3)), {'n': 'v'}),
            (T('a', 'a', (1,2)), None),
            (T('a', 'a', (2,3)), {'a': 'b'}),
        ])
        text = Text('01234', tags)

        for expected, received in zip([(k, tags[k]) for k in tags.keys()],
                                      list(iter(text))):
            self.assertTupleEqual(expected, received)
        tags.move_to_end(('a', 'a', (1, 2)))
        msg = '\n' + '\n'.join(repr(i) for i in list(reversed(text)))
        self.assertEqual(list(tags.items()), list(reversed(text)), msg=msg)

    def testLen(self):
        text = Text('n\U0010ABCDn')
        self.assertEqual(3, len(text))

    def testGetitem(self):
        tag2, tag1 = T('ns', 'key', (1,3)), T('ns', 'key', (0,2))
        text = Text('n\U0010ABCDn', [tag1, tag2])
        self.assertEqual([tag1, tag2], text[1])
        self.assertEqual([tag1, tag2], text[1:2])
        self.assertEqual([tag2], text[1:3:True])
        self.assertEqual([tag2], text[-1])

    def testGetitemSliceSorting(self):
        tags = [
            T('a', 'a', (0,5)),
            T('a', 'a', (1,4)),
            T('a', 'a', (1,3)),
            T('a', 'a', (1,2)),
            T('a', 'a', (2,3)),
            T('a', 'a', (15,19)),
        ]
        text = Text('0123456789ABDEFGHIJK', tags)
        self.assertEqual(tags[:-1], text[1:3])
        self.assertEqual(tags[2:5], text[1:3:True])
        self.assertEqual(tags, text[0:])
        self.assertEqual(tags, text[0::True])

    def testSetitem(self):
        tag, ms = T('ns', 'key', (0,2)), T('ms', 'k', (0,1,2,3))
        text = Text('n\U0010ABCDn')
        text[:-1] = 'ns:key'
        text[(0,1,2,3)] = 'ms:k'
        self.assertEqual([ms, tag], list(text.tags))
        self.compareTrees(self.buildTagtree([ms, tag]), text.tagtree)
        self.compareTrees(self.buildOffsets([ms, tag]), text.offsets)

    def testStr(self):
        text = Text('abc')
        self.assertSequenceEqual('abc', str(text))

    # Tag Properties and Methods

    def testAdd(self):
        tag1 = T('ns1', 'key1', (0, 3))
        tag2 = T('ns1', 'key1', (1, 2))
        tag3 = T('ns2', 'key2', (2, 3))
        tags = [tag1, tag2, tag3]
        text = Text('a\U0010ABCDb', [tag1, tag1])
        self.assertListEqual([tag1], list(text.tags))
        text.add([tag2, tag1, tag2])
        self.assertListEqual([tag1, tag2], list(text.tags))
        text.add([tag1, tag2, tag3])
        self.assertListEqual(tags, list(text.tags))
        self.compareTrees(self.buildTagtree(tags), text.tagtree)
        self.compareTrees(self.buildOffsets(tags), text.offsets)

    def testAddIllegalTags(self):
        text = Text('abcd')
        #self.assertRaises(ValueError, text.add, [('ns', 'key', (1,))])
        self.assertRaises(ValueError, text.add, [('ns', 'key', (3,2))])
        self.assertRaises(ValueError, text.add, [('ns', 'key', ())])
        self.assertRaises(ValueError, text.add, [('ns', 'key', (1,2,3))])
        self.assertRaises(ValueError, text.add, [('ns', 'key', (-1,2))])
        self.assertRaises(ValueError, text.add, [('ns', 'key', (0,5))])
        self.assertRaises(TypeError, text.add,  ['123'])
        self.assertRaises(TypeError, text.add, [('ns', 'key', 1, 2)])
        self.assertRaises(TypeError, text.add, [('ns', 'key', 1)])
        self.assertRaises(TypeError, text.add, 'tag')
        self.assertRaises(TypeError, text.add, 1)

    def testGet(self):
        tag1 = T('ns1', 'key1', (0, 3))
        tag2 = T('ns1', 'key2', (1, 2))
        tag3 = T('ns2', 'key1', (2, 3))
        text = Text('a\U0010ABCDb', [tag1, tag2, tag3])
        self.assertListEqual([tag1, tag2], list(sorted(text.get('ns1'))))
        self.assertListEqual([tag3], text.get('ns2', 'key1'))
        self.assertRaises(KeyError, text.get, 'ns3')
        self.assertRaises(KeyError, text.get, 'ns1', 'key3')

    def testRemove(self):
        tag1 = T('ns1', 'key1', (0, 3))
        tag2 = T('ns1', 'key1', (1, 2))
        tag3 = T('ns2', 'key2', (2, 3))
        text = Text('a\U0010ABCDb', [tag1, tag2, tag3])
        self.assertListEqual([tag1, tag2, tag3], list(text.tags))
        text.remove([tag1, tag3])
        self.assertListEqual([tag2], list(text.tags))
        self.compareTrees(self.buildTagtree([tag2]), text.tagtree)
        self.compareTrees(self.buildOffsets([tag2]), text.offsets)

    def testUpdate(self):
        text1 = Text('blabla', {('ns', 'k', (1,2)): {'a1': 'v1'}})
        text2 = Text('blabla', {('ns', 'k', (1,2)): {'a2': 'v2'},
                                ('ns', 'k', (4,6)): {'a1': 'v1'}})
        text3 = Text('blahblah', [('ns', 'k', (1,2))])
        text1.update(text2)
        self.assertListEqual([T('ns', 'k', (1,2)),
                              T('ns', 'k', (4,6))], list(text1.tags))
        self.assertDictEqual({'a1': 'v1', 'a2': 'v2'},
                             text1.attributes[('ns', 'k', (1,2))])
        self.assertRaises(ValueError, text1.update, text3)
        self.assertRaises(TypeError, text1.update, 'bla')

    def testMultispanTags(self):
        mstag = T('ns', 'key', (0, 1, 2, 3))
        tag = T('ns', 'key', (1, 3))
        text = Text('a\U0010ABCDb', [mstag, tag])
        self.assertListEqual([mstag, tag], list(text.tags))
        self.compareTrees(self.buildTagtree([mstag, tag]), text.tagtree)
        self.compareTrees(self.buildOffsets([mstag, tag]), text.offsets)

    def testRemoveMultispan(self):
        mstag = T('ns', 'key', (0, 1, 2, 3))
        tag = T('ns', 'key', (1, 3))
        text = Text('a\U0010ABCDb', [mstag, tag])
        text.remove([mstag])
        self.assertListEqual([tag], list(text.tags))
        self.compareTrees(self.buildTagtree([tag]), text.tagtree)
        self.compareTrees(self.buildOffsets([tag]), text.offsets)

    # Byte Offset Maps

    def testUtf8Map(self):
        text = Text('aä\U0010ABCD!')
        self.assertTupleEqual((0, 1, 3, 7), text.utf8)

    def testUtf16Map(self):
        text = Text('aä\U0010ABCD!')
        self.assertTupleEqual((0, 2, 4, 8), text.utf16)

    def testUtf32Map(self):
        text = Text('aä\U0010ABCD!')
        self.assertTupleEqual((0, 4, 8, 12), text.utf32)

    @patch.object(Text, '_utf8')
    def testUtf8Calls(self, mock):
        self.assertUtfCalls(mock, 'utf8')

    @patch.object(Text, '_utf16')
    def testUtf16Calls(self, mock):
        self.assertUtfCalls(mock, 'utf16')

    @patch.object(Text, '_utf32')
    def testUtf32Calls(self, mock):
        self.assertUtfCalls(mock, 'utf32')

    def assertUtfCalls(self, mock, attr):
        text = Text('aä\U0010ABCD!')
        text._maps['_' + attr] = None
        mock.return_value = iter((True,))
        self.assertTupleEqual((True,), getattr(text, attr))
        self.assertTupleEqual((True,), getattr(text, attr))
        self.assertEqual(1, mock.call_count)
        text._maps['_' + attr] = None
        mock.return_value = iter((True,))
        self.assertTupleEqual((True,), getattr(text, attr))
        self.assertEqual(2, mock.call_count)

    # String methods

    def testString(self):
        check = 'aü\U0010ABCDb'
        text = Text(check)
        self.assertEqual('\U0010ABCD', text.string[2:3])
        self.assertEqual('b\U0010ABCDüa', text.string[4:-5:-1])
        self.assertEqual('bü', text.string[4:-5:-2])

    def testEncode(self):
        check = 'aü\U0010ABCD'
        text = Text(check)
        self.assertEqual(check.encode(), text.encode())

    def testCharIter(self):
        text = Text('n\U0010ABCDn')
        self.assertTupleEqual(('n', '\U0010ABCD', 'n'), tuple(text.iter()))

    # Text identity

    def testBase64Digest(self):
        check = 'aü\U0010ABCD'
        text = Text(check)
        b64digest = b64encode(md5(check.encode()).digest())[:-2].decode()
        self.assertEqual(b64digest, text.base64digest)

    def testDigest(self):
        check = 'aü\U0010ABCD'
        text = Text(check)
        self.assertEqual(md5(check.encode()).digest(), text.digest)

    @patch.object(Text, 'encode')
    def testDigestCallsEncodeOnce(self, mock):
        check = 'aü\U0010ABCD'
        mock.return_value = check.encode()
        text = Text(check)
        digest = text.digest
        self.assertEqual(digest, text.digest)
        self.assertEqual(mock.call_count, 1)

    # Text serialization

    def testFromJson(self):
        json = {
            'text': 'abcd',
            'checksum': ['md5', md5(b'abcd').hexdigest()],
            'maps': {
                'utf8': (0, 1, 2, 3),
                'utf16': (0, 2, 4, 6),
                'utf32': (0, 4, 8, 12)
            },
            'tags': [[['ns', 'key', [0, 4]], {'a': 'v'}]],
        }
        text = Text.fromJson(json)
        self.assertEqual('abcd', str(text))
        self.assertEqual([('ns', 'key', (0, 4))], list(text.tags))
        self.assertEqual({('ns', 'key', (0, 4)): {'a': 'v'}}, text.attributes)
        self.assertEqual({
                '_utf8': (0, 1, 2, 3),
                '_utf16': (0, 2, 4, 6),
                '_utf32': (0, 4, 8, 12),
        }, text._maps)

    def testToJson(self):
        text = Text('abcd', {('ns', 'key', (0, 4)): {'a': 'v'}})
        json = {
            'text': 'abcd',
            'checksum': ('md5', md5(b'abcd').hexdigest()),
            'maps': {
                'utf8': (0, 1, 2, 3),
                'utf16': (0, 2, 4, 6),
                'utf32': (0, 4, 8, 12),
            },
            'tags': [(Text.Tag('ns', 'key', (0, 4)), {'a': 'v'})],
        }
        self.assertEqual(json, text.toJson())

if __name__ == '__main__':
    import sys
    from random import randint

    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        string = "".join(chr(randint(1, 0xD7FE)) for _ in range(1000000))
        tokens = [(str(randint(0, 10)), str(randint(0, 10)), (randint(o, o+10), randint(o+11, o+20))) for o in range(0, 1000000 - 20, 5)]
        text = Text(string)
        text.tags = tokens
        print("added 200k tokens")
    else:
        main()
