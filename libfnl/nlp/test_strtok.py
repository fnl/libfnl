from libfnl.nlp.strtok import Tokenize, TokenizeAlphanumeric, CasetagAlphanumeric, CasetagLetters, Tag, Category, CodepointIter, GetCharCategoryValue, GetTagValue, YieldNewToken, REMAPPED_CHARACTERS, STOP_CHARS
from random import randint
from time import time
from unicodedata import category
from unittest import main, TestCase

ALL_TAGS = (
    Tag.ALNUM_DIGIT, Tag.ALNUM_LOWER, Tag.ALNUM_NUMERAL, Tag.ALNUM_OTHER, Tag.ALNUM_UPPER,
    Tag.ALPHANUMERIC,
    Tag.BAD, Tag.BREAKS,
    Tag.CAMELCASED, Tag.CAPITALIZED, Tag.CONTROL,
    Tag.DIGITS,
    Tag.LETTERS, Tag.LOWERCASED,
    Tag.MARK, Tag.MIXEDCASED,
    Tag.NUMBER, Tag.NUMERAL,
    Tag.PUNCT,
    Tag.SPACES, Tag.STOP, Tag.SYMBOL,
    Tag.UPPERCASED
)
MULTICHAR_TAGS = (Tag.LETTERS, Tag.DIGITS, Tag.SPACES, Tag.BREAKS)
SINGLE_CHAR_TAGS = (t for t in ALL_TAGS if t not in MULTICHAR_TAGS)
GREEK_CHARS = ("".join(chr(x) for x in range(0x370, 0x3FF)) + 
               "".join(chr(x) for x in range(0x1F00, 0x1FFF)))

class YieldNewTokenTests(TestCase):

    def testUnequalTags(self):
        for t1 in ALL_TAGS:
            for t2 in ALL_TAGS:
                if t1 == t2: continue
                self.assertEqual(YieldNewToken(t1, t2), True,
                                 "unequal tags must always return True")

    def testEqualTagsButNotWordNumericWhitespace(self):
        for tag in SINGLE_CHAR_TAGS:
            self.assertEqual(YieldNewToken(tag, tag), True,
                             "%s does not return True" % Tag.toStr(tag))

    def testEqualWordNumericWhitespaceTags(self):
        for tag in MULTICHAR_TAGS:
            self.assertEqual(YieldNewToken(tag, tag), False,
                             "%s does not return False" % Tag.toStr(tag))

class GetCharCategoryTests(TestCase):

    def testNonRemappedCharacters(self):
        remapped_chars = ""

        for vals in REMAPPED_CHARACTERS.values():
            for chars in vals.keys():
                remapped_chars += chars

        for i in range(0, 0xFFFF):
            char = chr(i)
            cat = category(char)

            if cat in ("Ll", "Lu") and char in GREEK_CHARS:
                cat = "Lg" if cat == "Ll" else "LG"

            if char not in remapped_chars:
                result = GetCharCategoryValue(char)
                self.assertEqual(result, getattr(Category, cat),
                                 "char '%s' has cat=%s; but received=%s" % 
                                 (char, cat, chr(result)))

    def testRemappedCharacters(self):
        for chars, cat in (
            ("\n\f\r\u0085\u008D", Category.Zl),
            ("\t\v", Category.Zs),
            ("\u0091\u0092", Category.Co),
            ("#&@\uFE5F\uFE60\uFE6B\uFF03\uFF06\uFF20",
             Category.So),
            ("%\u2030\u2031\uFE6A\uFF05", Category.Sm),
            ("\u201A\u201E\u301D", Category.Pi),
        ):
            for c in chars:
                result = GetCharCategoryValue(c)
                self.assertEqual(result, cat,
                                 "char '%s' (0x%x) has cat=%i; received=%i" % 
                                 (c, ord(c), cat, result))

class GetTagValueTests(TestCase):

    def testStopCharacters(self):
        for char in STOP_CHARS:
            tag = GetTagValue(char, Category.Po)
            self.assertEqual(tag, Tag.STOP,
                             "'%s' (0x%x) is %s, not STOP" % 
                             (char, ord(char), Tag.toStr(tag)))

class CodepointIterTests(TestCase):

    def testRegularString(self):
        expected = ((0, 1, Category.Ll, Tag.LETTERS),
                    (1, 2, Category.Nd, Tag.DIGITS),
                    (2, 3, Category.Zl, Tag.BREAKS))

        for idx, result in enumerate(CodepointIter("a1\n")):
            self.assertTupleEqual(expected[idx], result)

    def testBadString(self):
        expected = ((0, 1, Category.Ll, Tag.LETTERS),
                    (1, 2, Category.Cs, Tag.BAD),
                    (2, 3, Category.Zl, Tag.BREAKS))

        for idx, result in enumerate(CodepointIter("a\uD800\n")):
            self.assertTupleEqual(expected[idx], result)

    def testSurrogateString(self):
        expected = ((0, 1, Category.Ll, Tag.LETTERS),
                    (1, 3, Category.Lo, Tag.LETTERS),
                    (3, 4, Category.Zl, Tag.BREAKS))

        for idx, result in enumerate(CodepointIter("a\uD800\uDC00\n")):
            self.assertTupleEqual(expected[idx], result)

class CasetagTests(TestCase):

    def testAlnumCategory(self):
        self.assertEqual(CasetagAlphanumeric(b"ll1"), Tag.ALNUM_LOWER)
        self.assertEqual(CasetagAlphanumeric(b"Ul1"), Tag.ALNUM_UPPER)
        self.assertEqual(CasetagAlphanumeric(b"1l1"), Tag.ALNUM_DIGIT)
        self.assertEqual(CasetagAlphanumeric(b"2l1"), Tag.ALNUM_NUMERAL)
        self.assertEqual(CasetagAlphanumeric(b"Ll1"), Tag.ALNUM_OTHER)

    def testBadAlnumCategory(self):
        self.assertRaises(RuntimeError, CasetagAlphanumeric, b"xll11")

    def testLetterCategory(self):
        self.assertEqual(CasetagLetters(b"llll"), Tag.LOWERCASED)
        self.assertEqual(CasetagLetters(b"UUUU"), Tag.UPPERCASED)
        self.assertEqual(CasetagLetters(b"lUlU"), Tag.MIXEDCASED)
        self.assertEqual(CasetagLetters(b"UlUl"), Tag.CAMELCASED)
        self.assertEqual(CasetagLetters(b"Ulll"), Tag.CAPITALIZED)
        self.assertEqual(CasetagLetters(b"Llll"), Tag.LETTERS)

    def testBadLetterCategory(self):
        self.assertRaises(RuntimeError, CasetagLetters, b"xll11")

class CategoryTests(TestCase):

    def assertCategoryTests(self, cats, IsCatMethod):
        tests = 0

        for i in range(0, 128):
            if i in cats:
                self.assertTrue(IsCatMethod(bytes([i])))
                tests += 1
            else:
                self.assertFalse(IsCatMethod(bytes([i])))

        self.assertEqual(tests, len(cats))

    def testIsUppercase(self):
        self.assertCategoryTests(Category.UPPERCASE_LETTERS,
                                 Category.isUppercase)

    def testIsLowercase(self):
        self.assertCategoryTests(Category.LOWERCASE_LETTERS,
                                 Category.isLowercase)

    def testIsNumeric(self):
        self.assertCategoryTests(Category.NUMBERS,
                                 Category.isNumber)

    def testIsPunctuation(self):
        self.assertCategoryTests(Category.PUNCTUATION,
                                 Category.isPunctuation)

    def testIsSymbol(self):
        self.assertCategoryTests(Category.SYMBOLS,
                                 Category.isSymbol)

    def testIsSeparator(self):
        self.assertCategoryTests(Category.SEPARATORS,
                                 Category.isSeparator)

class TagTests(TestCase):

    def testToStr(self):
        self.assertEqual(Tag.toStr(Tag.BREAKS), "BREAKS")

class TokenizeTests(TestCase):

    def testRegularExampleString(self):
        example = "\u0001\u00ADx\u02B0\u01BB\u01C5X111[$]?"
        cats = (b"^", b"%", b"lmLTU", b"111", b"(", b"$", b")", b".")

        for idx, token in enumerate(Tokenize(example)):
            self.assertEqual(cats[idx], token.cats)

    def testAlnumExampleString(self):
        """

        """
        example = "A defAult Sentence, with SoMe “20%” Bl1a-1blA αrecⅣ!"
        cats_b = b"UslllUlllsUlllllll.sllllsUlUls<11+>sUl1l-1llUsglll2."
        tok_list = ["A", " ", "defAult", " ", "Sentence", ",", " ", "with",
            " ", "SoMe", " ", "“", "20", "%", "”", " ", "Bl1a", "-",
            "1blA", " ", "αrecⅣ", "!"]
        tag_list = [Tag.UPPERCASED,
                    Tag.SPACES,
                    Tag.MIXEDCASED,
                    Tag.SPACES,
                    Tag.CAPITALIZED,
                    Tag.PUNCT,
                    Tag.SPACES,
                    Tag.LOWERCASED,
                    Tag.SPACES,
                    Tag.CAMELCASED,
                    Tag.SPACES,
                    Tag.PUNCT,
                    Tag.DIGITS,
                    Tag.SYMBOL,
                    Tag.PUNCT,
                    Tag.SPACES,
                    Tag.ALNUM_UPPER,
                    Tag.PUNCT,
                    Tag.ALNUM_DIGIT,
                    Tag.SPACES,
                    Tag.ALNUM_LOWER,
                    Tag.STOP]
        tokens = list(TokenizeAlphanumeric(example, case_tags=True))
        self.assertEqual(len(tokens), len(tok_list))
        #noinspection PyArgumentList
        cats = bytearray()
        for i, t in enumerate(tokens):
            self.assertEqual(t.string, tok_list[i],
                             "expected '%s', found '%s' at position %i" % 
                             (tok_list[i], t.string, i))
            self.assertEqual(t.tag, tag_list[i],
                             "expected %s for '%s', found %s at position %i" % 
                             (Tag.toStr(tag_list[i]), t.string,
                              Tag.toStr(t.tag), i))
            self.assertEqual(len(t.string), len(t.cats))
            for c in t.cats: cats.append(c.real)
        self.assertSequenceEqual(cats_b, bytes(cats))

    def testTaggingModifierAlnumString(self):
        example = "\u02B0\u02B011"
        cats = (b"mm11",)

        for idx, token in enumerate(TokenizeAlphanumeric(example, True)):
            self.assertEqual(cats[idx], token.cats)
            self.assertEqual(Tag.ALNUM_DIGIT, token.tag)

    def testTokenizing100kRandomCharsTakesLessThanOneSec(self):
        #noinspection PyUnusedLocal
        string = "".join(chr(randint(1, 0xCFFE)) for i in range(100000))
        start = time()
        # Note that case tagging has no significant influence on the speed.
        tokens = len(tuple(Tokenize(string)))
        end = time()
        self.assertTrue(end - start < 1.0, "creating %i tokens took %.3f s" % 
                        (tokens, end - start))

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        string = "".join(chr(randint(1, 0xCFFE)) for dummy in range(100000))
        print("generated %i tokens" % len(tuple(Tokenize(string))))
    else:
        main()
