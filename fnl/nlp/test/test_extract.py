from html.parser import HTMLParseError
from unittest import main, TestCase
from libfnl.nlp.extract import HtmlExtractor, GREEK_LOWER, GREEK_UPPER

__author__ = 'Florian Leitner'

class ExtractHtmlTests(TestCase):

    def setUp(self):
        self.ex = HtmlExtractor()

    def testBasicExtraction(self):
        self.ex.namespace = 'test'
        self.ex.feed("""
<html>
  <body>
    <p>
      <span>Hel<wbr>lo World<wbr>!</span>
    </p>
  </body>
</html>
        """)
        self.ex.close()
        self.assertEqual('Hello World!', self.ex.string)
        self.assertDictEqual({
            ('test', 'html', (0, 12)): {},
            ('test', 'body', (0, 12)): {},
            ('test', 'p', (0, 12)): {},
            ('test', 'span', (0, 12)): {},
        }, self.ex.tags)

    def testTagAttributes(self):
        self.ex.feed('<span key=value>data</span>')
        self.ex.close()
        self.assertEqual('data', self.ex.string)
        tag = (self.ex.namespace, 'span', (0, 4))
        self.assertEqual({tag: {'key': 'value'}}, self.ex.tags)

    def testIncompleteHtml(self):
        self.ex.feed("<tag")
        self.assertRaises(HTMLParseError, self.ex.close)
        self.ex.reset()
        self.ex.feed("<p>hiho")
        self.ex.close()
        self.assertRaises(HTMLParseError, lambda: self.ex.string)

    def testCharacterRef(self):
        self.ex.feed("&#{};".format(ord("a")))
        self.ex.close()
        self.assertEqual('a', self.ex.string)
        self.ex.reset()
        self.ex.feed("&#x{:x};".format(ord("a")))
        self.ex.close()
        self.assertEqual('a', self.ex.string)
        self.ex.reset()
        self.ex.feed("&#x{:x};".format(ord("Z")).upper())
        self.ex.close()
        self.assertEqual('Z', self.ex.string)
        self.ex.reset()
        self.ex.feed("&#x110000;")
        self.ex.close()
        self.assertEqual(HtmlExtractor.REPLACEMENT, self.ex.string)

    def testIgnoredTags(self):
        self.ex.feed("<script key=value />")
        self.ex.close()
        self.assertEqual('', self.ex.string)
        self.assertEqual({}, self.ex.tags)
        self.ex.reset()
        self.ex.feed('<script>ignore</script>')
        self.ex.close()
        self.assertEqual('', self.ex.string)
        self.assertEqual({}, self.ex.tags)


    def testEntityReferences(self):
        self.ex.feed("&lt;")
        self.ex.close()
        self.assertEqual('<', self.ex.string)
        self.ex.reset()
        self.ex.feed("&lt;".upper())
        self.ex.close()
        self.assertEqual('<', self.ex.string)
        self.ex.reset()
        self.ex.feed("&junk;")
        self.ex.close()
        self.assertEqual(HtmlExtractor.REPLACEMENT, self.ex.string)

    def testComment(self):
        self.ex.feed("<!-- comment -->")
        self.ex.close()
        self.assertEqual('', self.ex.string)

    def testDeclaration(self):
        self.ex.feed("<!declaration bla bla>sentinel")
        self.ex.close()
        self.assertEqual('sentinel', self.ex.string)

    def testProcessInstruction(self):
        self.ex.feed("<?proc bla bla>sentinel")
        self.ex.close()
        self.assertEqual('sentinel', self.ex.string)

    def testImageAndAreaTags(self):
        for t in ('img', 'area'):
            self.ex.feed("<{}>".format(t))
            self.ex.close()
            self.assertEqual(HtmlExtractor.OBJECT_REPLACEMENT, self.ex.string)
            self.assertEqual({(self.ex.namespace, t, (0, 1)): {}},
                             self.ex.tags)
            self.ex.reset()
            self.ex.feed("<{} title='a' alt='b'>".format(t))
            self.ex.close()
            self.assertEqual('b', self.ex.string)
            self.assertEqual({(self.ex.namespace, t, (0, 1)): {'title': 'a'}},
                             self.ex.tags)
            self.ex.reset()
            self.ex.feed("<{} title='a'>".format(t))
            self.ex.close()
            self.assertEqual('a', self.ex.string)
            self.assertEqual({(self.ex.namespace, t, (0, 1)): {}},
                             self.ex.tags)
            self.ex.reset()
            self.ex.feed("<{} key='val'>".format(t))
            self.ex.close()
            self.assertEqual(HtmlExtractor.OBJECT_REPLACEMENT, self.ex.string)
            self.assertEqual({(self.ex.namespace, t, (0, 1)): {'key': 'val'}},
                             self.ex.tags)
            self.ex.reset()

    def testIgnoreUnknownElement(self):
        self.ex.feed('<tag>data</tag>')
        self.ex.close()
        self.assertEqual('', self.ex.string)
        self.assertEqual({}, self.ex.tags)

    def testImageGreekCharacerAlt(self):
        for n in ('alpha', 'AlPhA', 'ALPHA'):
            self.ex.reset()
            self.ex.feed('<img alt="{}">'.format(n))
            self.ex.close()
            self.assertEqual(GREEK_LOWER[n.lower()], self.ex.string)

        self.ex.reset()
        self.ex.feed('<img alt="Alpha">')
        self.ex.close()
        self.assertEqual(GREEK_UPPER['Alpha'], self.ex.string)

    def testBrHr(self):
        self.ex.feed("<br>a")
        self.ex.close()
        self.assertEqual("\na", self.ex.string)
        self.assertEqual({(self.ex.namespace, 'br', (0, 1)): {}}, self.ex.tags)
        self.ex.reset()
        self.ex.feed("<hr>a")
        self.ex.close()
        self.assertEqual("\n\na", self.ex.string)
        self.assertEqual({(self.ex.namespace, 'hr', (0, 2)): {}}, self.ex.tags)

    def testMinorContent(self):
        self.ex.feed("""
<html a=1>
  <head b=2>
    <title c=3>title</title>
  </head>
  <body d=4>
    <h1 e=5>heading</h1>

    <div f=6>
      <ol g=7>
        <li h=8>1</li>
        <li i=9>2</li>
      </ol>
    </div>

    <p j=0>footer</p>
  </body>
</html>
        """)
        self.ex.close()
        self.assertEqual("title\n\nheading\n\n1\n2\n\nfooter",
                         self.ex.string)
        self.assertDictEqual({
            (self.ex.namespace, 'html',   (0, 27)): {'a': '1'},
            (self.ex.namespace, 'head',   (0,  7)): {'b': '2'},
            (self.ex.namespace, 'title',  (0,  7)): {'c': '3'},
            (self.ex.namespace, 'body',   (7, 27)): {'d': '4'},
            (self.ex.namespace, 'h1',     (7, 16)): {'e': '5'},
            (self.ex.namespace, 'div',   (16, 21)): {'f': '6'},
            (self.ex.namespace, 'ol',    (16, 21)): {'g': '7'},
            (self.ex.namespace, 'li',    (16, 18)): {'h': '8'},
            (self.ex.namespace, 'li',    (18, 20)): {'i': '9'},
            (self.ex.namespace, 'p',     (21, 27)): {'j': '0'},
        }, self.ex.tags)

    def testDropEmptyTag(self):
        self.ex.feed("a <span style=fun> \n </span> b")
        self.ex.close()
        self.assertEqual('a b', self.ex.string)
        self.assertEqual({}, self.ex.tags)

    def testAddTag(self):
        self.ex.feed("<i a=1 accesskey=x><i b=2 style=y>data</i></i>")
        self.ex.close()
        self.assertEqual({
            (self.ex.namespace, 'em', (0, 4)): {'a': '1', 'b': '2'}
        }, self.ex.tags)

    def testNormalWhitespace(self):
        self.ex.feed(" \n<span>  a  b &nbsp; \n c  </span> \n&nbsp;\n")
        self.ex.close()
        self.assertEqual("a b \u00a0c", self.ex.string)
        self.assertEqual({(self.ex.namespace, 'span', (0, 6)): {}},
                         self.ex.tags)
        self.ex.reset()
        self.ex.feed("a\nb c\td e\ff g\rh")
        self.ex.close()
        self.assertEqual("a b c d e f g h", self.ex.string)
        self.ex.reset()
        self.ex.feed("\u00a0a\u00a0\u00a0b\u00a0")
        self.ex.close()
        self.assertEqual("a b", self.ex.string)
        self.ex.reset()
        self.ex.feed("a\n")
        self.ex.feed("b")
        self.ex.close()
        self.assertEqual("a b", self.ex.string)

if __name__ == '__main__':
    main()