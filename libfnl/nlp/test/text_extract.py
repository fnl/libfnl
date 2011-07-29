from unittest import main, TestCase
from libfnl.nlp.extract import HtmlExtractor

__author__ = 'Florian Leitner'

class ExtractHtmlTests(TestCase):

    def setUp(self):
        self.ex = HtmlExtractor()

    def testMetaReplacement(self):
        self.ex.feed('<meta name="key" content="value">')
        self.assertEqual('key: value\n', self.ex.string)
        self.assertTrue(('html', 'meta', (0, 10)) in self.ex.tags,
                        list(self.ex.tags.keys()))
        self.assertEqual({}, self.ex.tags[('html', 'meta', (0, 10))])

    def testBrReplacement(self):
        self.ex.feed('<br>')
        self.assertEqual('\n', self.ex.string)
        self.assertFalse(self.ex.tags, list(self.ex.tags.keys()))

    def testHrReplacement(self):
        self.ex.feed('<hr>')
        self.assertEqual('\n\n', self.ex.string)
        self.assertFalse(self.ex.tags, list(self.ex.tags.keys()))

    def testImageReplacement(self):
        self.ex.feed('<img alt="sentinel" title="title" href="reference">')
        self.assertEqual('sentinel (title) ', self.ex.string)
        self.assertTrue(('html', 'img', (0, 17)) in self.ex.tags,
                        list(self.ex.tags.keys()))
        self.assertEqual({'href': 'reference'},
                         self.ex.tags[('html', 'img', (0, 17))])

    def testImageGreekAltReplacment(self):
        self.ex.feed('<img alt="alpha">')
        self.assertEqual('α', self.ex.string)
        self.assertTrue(('html', 'img', (0, 1)) in self.ex.tags,
                        list(self.ex.tags.keys()))
        self.assertEqual({}, self.ex.tags[('html', 'img', (0, 1))])
        self.ex.reset()
        self.ex.feed('<img alt="ALPHA">')
        self.assertEqual('α', self.ex.string)
        self.ex.reset()
        self.ex.feed('<img alt="Alpha">')
        self.assertEqual('Α', self.ex.string)

    def testBaseUrlReplacement(self):
        self.ex.feed("""
        <head><base href='http://www.example.com/path/page.html'></head>
        <body>
            <a href='other.html'>link1</a>
            <a href='http://www.other.com/path/page.html'>link2</a>
            <a href='#'>same</a>
        </body>
        """)
        self.assertEqual('http://www.example.com/path/page.html', self.ex.url)
        self.assertEqual('link1 link2 same', self.ex.string)
        self.assertTrue(('html', 'a', (0, 5)) in self.ex.tags,
                        list(self.ex.tags.keys()))
        self.assertEqual({'href': 'http://www.example.com/path/other.html'},
                         self.ex.tags[('html', 'a', (0, 5))])
        self.assertTrue(('html', 'a', (6, 11)) in self.ex.tags,
                        list(self.ex.tags.keys()))
        self.assertEqual({'href': 'http://www.other.com/path/page.html'},
                         self.ex.tags[('html', 'a', (6, 11))])
        self.assertTrue(('html', 'a', (12, 16)) in self.ex.tags,
                        list(self.ex.tags.keys()))
        self.assertEqual({'href': 'http://www.example.com/path/page.html'},
                         self.ex.tags[('html', 'a', (12, 16))])


if __name__ == '__main__':
    main()