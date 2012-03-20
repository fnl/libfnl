from collections import OrderedDict
from hashlib import md5
from libfnl.couch.serializer import b64encode
from libfnl.nlp.text import Text
from mock import patch
from unittest import main, TestCase

__author__ = 'Florian Leitner'

class TextTests(TestCase):

    def testInitialization(self):
        text = Text('text')
        self.assertDictEqual(dict(), text.attributes)

    def testInitializationWithJunk(self):
        self.assertRaises(TypeError, Text, 10)
        self.assertRaises(TypeError, Text, object())
        self.assertRaises(TypeError, Text, tuple('string'))

    def testInitializationWithTags(self):
        tag1 = ('ns', 'key', (0, 1))
        tag2 = ('ns', 'key', (1, 2))
        tag3 = ('ns', 'key', (2, 3))
        tag4 = ('ns', 'key', (3, 4))
        tags = [tag1, tag2, tag3, tag4]
        text = Text('text', [(tag1, {'n': 'v'}), (tag2, [('dict', 'like')]),
                             (tag3, ['kv']), (tag4, {})])
        self.assertListEqual(tags, list(text))
        self.assertDictEqual({tag1: {'n': 'v'},
                              tag2: {'dict': 'like'},
                              tag3: {'k': 'v'}}, text.attributes['ns'])

    def testTagInitializationUnicode(self):
        tag1 = ('ns1', 'key1', (0, 3))
        tag2 = ('ns1', 'key1', (1, 2))
        tag3 = ('ns2', 'key2', (2, 3))
        tags = [tag1, tag2, tag3]
        text = Text('a\U0010ABCDb', [(tag1, {}), (tag2, {}), (tag3, {})])
        self.assertListEqual(tags, list(text))

    def testInitializationWithInvalidTagAttributes(self):
        tag = ('ns', 'key', (1, 2))
        self.assertRaises(ValueError, Text, 'text', [(tag, ['mist'])])
        self.assertRaises(ValueError, Text, 'text',
                          [(tag, [('fake', 'dict', 'like')])])
        self.assertRaises(TypeError, Text, 'text', [(tag, 1)])

    # Special and Private Methods

    def testContains(self):
        tag2, tag1 = ('ns', 'key', (1,2)), ('ns', 'key', (0,2))
        text = Text('n\U0010ABCDn', [(tag1, None)])
        self.assertTrue(tag1 in text)
        self.assertFalse(tag2 in text)
        self.assertFalse(('ns', 'key', object()) in text)
        self.assertFalse(('ns', object(), (1, 2)) in text)
        self.assertFalse((object(), 'key', (1, 2)) in text)

    def testDelitem(self):
        tag2, tag1 = ('ns', 'key', (1,3)), ('ns', 'key', (0,2))
        tag3 = ('ns', 'key', (2, 3))
        text = Text('n\U0010ABCDn', [(tag1, None), (tag2, {'a': 'v'})])
        del text[0]
        self.assertListEqual([(tag2, {'a': 'v'})], list(text.get()))
        text.add([(tag3, None)])
        del text[2]
        self.assertListEqual([], list(text.get()))
        self.assertListEqual([], list(text))
        self.assertDictEqual({}, text.attributes)


    def testEq(self):
        text1 = Text('n\U0010ABCDn', [(('ns', 'key', (0,3)), None)])
        text2 = Text(text1)
        text2.attributes[('ns', 'key', (0,3))] = {'a': 'v'}
        self.assertTrue(text1 == text2, '{!r} != {!r}'.format(text1, text2))
        self.assertFalse(text1 is text2,
                         '{!r} is not {!r}'.format(text1, text2))

    def testIter(self):
        tags = OrderedDict([
            (('a', 'a', (0,5)), None),
            (('a', 'a', (1,4)), None),
            (('a', 'b', (1,3)), {'n': 'v'}),
            (('a', 'a', (1,2)), None),
            (('a', 'a', (2,3)), {'a': 'b'}),
        ])
        text = Text('01234', [(t, a) for t, a in tags.items()])

        for expected, received in zip(list(tags.keys()),
                                      list(text)):
            self.assertTupleEqual(expected, received)

    def testGetitem(self):
        tag1, tag2 = ('ns', 'key1', (1,3)), ('ns', 'key2', (0,2))
        text = Text('n\U0010ABCDn', [(tag1, None), (tag2, None)])
        self.assertEqual([tag2, tag1], text[1])
        self.assertEqual([tag2, tag1], text[1:2])
        self.assertEqual([tag1], text[1:3:True])
        self.assertEqual([tag1], text[-1])

    def testGetitemSliceSorting(self):
        tags = [
            ('a', 'a', (0,5)),
            ('a', 'a', (1,4)),
            ('a', 'a', (1,3)),
            ('a', 'a', (1,2)),
            ('a', 'a', (2,3)),
            ('a', 'a', (15,19)),
        ]
        text = Text('0123456789ABDEFGHIJK', [(t, None) for t in tags])
        self.assertEqual(tags[:-1], text[1:3])
        self.assertEqual(tags[2:5], text[1:3:True])
        self.assertEqual(tags, text[0:])
        self.assertEqual(tags, text[0::True])

    def testLen(self):
        tag1 = ('ns1', 'id', (0, 3))
        tag2 = ('ns2', 'id', (1, 3))
        tag3 = ('ns3', 'id', (0, 2))
        text = Text('abc', [(tag1, None), (tag2, None), (tag3, None)])
        self.assertEqual(3, len(text))

    def testSetitem(self):
        tag, ms = ('ns', 'key', (0,2)), ('ms', 'k', (0,1,2,3))
        text = Text('n\U0010ABCDn')
        text[:-1] = 'ns', 'key'
        text[(0,1,2,3)] = 'ms' ,'k'
        self.assertEqual([ms, tag], list(text.tags()))

    def testStr(self):
        text = Text('abc')
        self.assertSequenceEqual('abc', str(text))

    # Tag Methods

    def testAdd(self):
        tag1 = ('ns1', 'key1', (0, 3))
        tag2 = ('ns1', 'key1', (1, 2))
        tag3 = ('ns2', 'key2', (2, 3))
        tags = [tag1, tag2, tag3]
        text = Text('a\U0010ABCDb', [(tag1, None)])
        self.assertListEqual([(tag1, None)], list(text.get()))
        attrs = {'n': {'x': 'y'}}
        text.add([(tag1, attrs), (tag2, None)], 'ns1')
        self.assertListEqual([(tag1, attrs), (tag2, None)], list(text.get()))
        text.add([(tag1, attrs), (tag2, attrs), (tag3, attrs)])
        self.assertListEqual(tags, list(text))
        self.assertListEqual([(tag1, attrs), (tag2, attrs)],
                             list(text.get('ns1')))
        self.assertListEqual([(tag3, attrs)], list(text.get('ns2')))

    def testAddUpdateAttributes(self):
        tag = ('ns1', 'key1', (0, 3))

        for first, update, result in [
            ('a', 'b', 'b'), ([1], [2], [1, 2]),
            ({1: 1}, {1: 3, 2: 2}, {1: 3, 2: 2})
        ]:
            text = Text('test')
            text.add([(tag, {'n': first})], 'ns1')
            self.assertEqual(first, text.attributes['ns1'][tag]['n'])
            text.add([(tag, {'n': update})], 'ns1')
            self.assertEqual(result, text.attributes['ns1'][tag]['n'])

    def testAddIllegalTags(self):
        text = Text('abcd')
        tag = ('ns', 'id', (0,2))
        self.assertRaises(TypeError, text.add, 1)
        self.assertRaises(TypeError, text.add, [(1, None)])
        self.assertRaises(TypeError, text.add, [(['ns', 'id', 'o'], {1: 2})])
        self.assertRaises(TypeError, text.add, [(tag, 1)])
        self.assertRaises(ValueError, Text('abcd').add,
                          [(tag, [('a', 'b', 'c')])])
        self.assertRaises(ValueError, Text('abcd').add, [tag])

    def testAddFromDict(self):
        text = Text('abcd')
        tags = {
            'ns1': { 'id1': { '0.1': { 'a': 'v' },
                              '1.2': None },
                     'id2': { '2.3': { 'x': 'y' }}},
            'ns2': { 'id1': { '0.4': { 'k': 'l' }}}
        }
        text.addFromDict(tags)
        self.assertListEqual([
            (('ns1', 'id1', (0, 1)), { 'a': 'v'}),
            (('ns1', 'id1', (1, 2)), None),
            (('ns1', 'id2', (2, 3)), { 'x': 'y'}),
            (('ns2', 'id1', (0, 4)), { 'k': 'l'}),
        ], list(text.get()))

    def testGet(self):
        tag1 = ('ns1', 'key1', (0, 3))
        tag2 = ('ns1', 'key2', (1, 2))
        tag3 = ('ns2', 'key1', (2, 3))
        text = Text('a\U0010ABCDb', [(tag1, {1:2}), (tag2, {3:4}),
                                     (tag3, {5:6})])
        self.assertListEqual([(tag1, {1:2}), (tag2, {3:4})],
                             list(text.get('ns1')))
        self.assertListEqual([(tag3, {5:6})], list(text.get('ns2')))

    def testGetIllegalTags(self):
        tag1 = ('ns1', 'key1', (0, 3))
        tag2 = ('ns2', 'key1', (2, 3))
        text = Text('a\U0010ABCDb', [(tag1, {}), (tag2, {})])
        self.assertRaises(KeyError, list, text.get('ns3'))

    def testNamespaces(self):
        tag1 = ('ns1', 'key1', (0, 3))
        tag2 = ('ns2', 'key2', (1, 2))
        tag3 = ('ns3', 'key1', (2, 3))
        text = Text('a\U0010ABCDb', [(tag1, None), (tag2, None), (tag3, None)])
        self.assertListEqual(['ns1', 'ns2', 'ns3'], list(text.namespaces))

    def testRemove(self):
        tag1 = ('ns1', 'key1', (0, 3))
        tag2 = ('ns1', 'key1', (1, 2))
        tag3 = ('ns2', 'key2', (2, 3))
        text = Text('a\U0010ABCDb', [(tag1, None), (tag2, {1:2}),
                                     (tag3, None)])
        self.assertListEqual([tag1, tag2, tag3], list(text))
        text.remove([tag1, tag3])
        self.assertListEqual([tag2], list(text))
        self.assertDictEqual({'ns1': {tag2: {1:2}}}, text.attributes)
        text.remove(None, 'ns1')
        self.assertListEqual([], list(text))
        self.assertDictEqual({}, text.attributes)

    def testTags(self):
        tag1 = ('ns1', 'id', (0, 3))
        tag2 = ('ns2', 'id', (1, 3))
        tag3 = ('ns3', 'id', (0, 2))
        text = Text('a\U0010ABCDb', [(tag1, None), (tag2, None), (tag3, None)])
        self.assertListEqual([tag1, tag3, tag2], text.tags())
        self.assertListEqual([tag1, tag2, tag3], text.tags(Text.ReverseKey))

    def testTagsMultispan(self):
        mstag = ('ns', 'key', (0, 1, 2, 3))
        tag = ('ns', 'key', (0, 3))
        text = Text('a\U0010ABCDb', [(mstag, None), (tag, None)])
        self.assertListEqual([mstag, tag], list(text.tags()))
        self.assertListEqual([mstag, tag], list(text.tags(Text.ReverseKey)))

    def testTagsAsDict(self):
        text = Text('abcd', [
            (('ns1', 'id1', (0, 1)), { 'a': 'v'}),
            (('ns1', 'id1', (1, 2)), None),
            (('ns1', 'id2', (2, 3)), { 'x': 'y'}),
            (('ns2', 'id1', (0, 4)), { 'k': 'l'}),
        ])
        self.assertDictEqual({
            'ns1': { 'id1': { '0.1': { 'a': 'v' },
                              '1.2': None },
                     'id2': { '2.3': { 'x': 'y' }}},
            'ns2': { 'id1': { '0.4': { 'k': 'l' }}}
        }, text.tagsAsDict())

    def testUpdate(self):
        text1 = Text('blabla', [(('ns', 'k', (1,2)),
                                 {'a1': 'v1', 'a2': 'v1'})])
        text2 = Text('blabla', [(('ns', 'k', (1,2)), {'a1': 'v2'}),
                                (('ns', 'k', (4,6)), {'a1': 'v1'})])
        text3 = Text('blahblah', [(('ns', 'k', (1,2)), {'a1': 'v1'})])
        text1.update(text2)
        self.assertListEqual([('ns', 'k', (1,2)),
                              ('ns', 'k', (4,6))], list(text1))
        self.assertDictEqual({'ns': {('ns', 'k', (1,2)): {'a1': 'v2',
                                                          'a2': 'v1'},
                                     ('ns', 'k', (4,6)): {'a1': 'v1'}}},
                             text1.attributes)
        self.assertRaises(ValueError, text1.update, text3)
        self.assertRaises(TypeError, text1.update, 'bla')

    # Byte Offset Maps

    def testUtf8Map(self):
        text = Text('aä\U0010ABCD!')
        self.assertTupleEqual((0, 1, 3, 7, 8), text.utf8)
        self.assertEqual(len('aä\U0010ABCD!'.encode('utf8')), text.utf8[-1])

    def testUtf16Map(self):
        text = Text('aä\U0010ABCD!')
        self.assertTupleEqual((2, 4, 6, 10, 12), text.utf16)
        self.assertEqual(len('aä\U0010ABCD!'.encode('utf16')), text.utf16[-1])

    @patch.object(Text, '_utf8')
    def testUtf8Calls(self, mock):
        self.assertUtfCalls(mock, 'utf8')

    @patch.object(Text, '_utf16')
    def testUtf16Calls(self, mock):
        self.assertUtfCalls(mock, 'utf16')

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

    def testEncode(self):
        check = 'aü\U0010ABCD'
        text = Text(check)
        self.assertEqual(check.encode(), text.encode())

    def testIter(self):
        string = 'abcd'
        offsets = [(0, 2), (1, 3), (2, 4)]
        text = Text(string, [(('n', 'i', off), {'a': off}) for off in offsets])
        self.assertListEqual([('i', string[off[0]:off[1]], {'a': off})
                              for off in offsets], list(text.iter('n')))
        text.add([(('ms', 'i', (0, 1, 3, 4)), None)])
        self.assertListEqual([('i', 'ad', None)], list(text.iter('ms')))

    def testString(self):
        check = 'aü\U0010ABCDb'
        text = Text(check)
        self.assertTupleEqual(('a', 'ü', '\U0010ABCD', 'b'),
                              tuple(text.string))
        self.assertEqual('\U0010ABCD', text.string[2:3])
        self.assertEqual('b\U0010ABCDüa', text.string[4:-5:-1])
        self.assertEqual('bü', text.string[4:-5:-2])
        self.assertTrue(isinstance(text.string, str))
        self.assertEqual('Aü\U0010ABCDb', text.string.capitalize())

    def testStringLen(self):
        text = Text('n\U0010ABCDn')
        self.assertEqual(3, len(text.string))

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
            'checksum': {
                'MD-5': md5(b'abcd').hexdigest(),
                'encoding': 'UTF-8'
            },
            'maps': {
                'UTF-8': (0, 1, 2, 3, 4),
                'UTF-16': (2, 4, 6, 8, 10),
            },
        }
        text = Text.fromJson(json)
        self.assertEqual('abcd', str(text))
        self.assertDictEqual({
            '_utf8': (0, 1, 2, 3, 4),
            '_utf16': (2, 4, 6, 8, 10),
        }, text._maps)

    def testFromJsonValueErrors(self):
        checksum = md5(b'abcd').hexdigest()
        self.assertRaises(ValueError, Text.fromJson, {'bla': 'bla'})
        self.assertRaises(ValueError, Text.fromJson, {'text': 'abcd'})
        self.assertRaises(ValueError, Text.fromJson,
                          {'text': 'abcd', 'checksum': checksum})
        self.assertRaises(ValueError, Text.fromJson,
                          {'text': 'abcd', 'checksum': {'md5': checksum}})
        self.assertRaises(ValueError, Text.fromJson,
                          {'text': 'abcd', 'checksum': {'junk': checksum,
                                                        'encoding': 'utf8'}})
        self.assertRaises(ValueError, Text.fromJson,
                          {'text': 'abcd', 'checksum': {'md5': checksum,
                                                        'encoding': 8}})
        self.assertRaises(ValueError, Text.fromJson,
                          {'text': 'abcd', 'checksum': {'md5': 'fantastic',
                                                        'encoding': 'utf8'}})
        self.assertRaises(ValueError, Text.fromJson,
                          {'text': 'abcd', 'checksum': {'md5': '123abc',
                                                        'encoding': 'utf8'}})


    def testToJson(self):
        text = Text('abcd', [(('ns', 'id', (0, 4)), {'a': 'v'})])
        json = {
            'text': 'abcd',
            'checksum': {'md5': md5(b'abcd').hexdigest(), 'encoding': 'utf8'},
            'maps': {
                'utf8': (0, 1, 2, 3, 4),
                'utf16': (2, 4, 6, 8, 10),
            },
        }
        self.assertDictEqual(json, text.toJson())

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        from random import randint
        import time
        string = "".join(chr(randint(1, 0xD7FE)) for _ in range(1000000))
        tokens = [('ns', str(randint(0, 10)), (randint(o, o+10), randint(o+11, o+20))) for o in range(0, 1000000 - 20, 5)]
        tags = [(t, {'a': 'b'}) for t in tokens]
        text = Text(string)
        start = time.time()
        text.add(tags, 'ns')
        print("added 200k tokens in {:.3f} sec".format(time.time() - start))
    else:
        main()
