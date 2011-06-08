import libfnl.nlp.strtok as S

from random import randint
from time import time
from unicodedata import category
from unittest import main, TestCase

ALL_TAGS = (
    S.Tag.ALNUM_DIGIT, S.Tag.ALNUM_LOWER, S.Tag.ALNUM_NUMERAL,
    S.Tag.ALNUM_OTHER, S.Tag.ALNUM_UPPER, S.Tag.ALPHANUMERIC,
    S.Tag.BAD, S.Tag.BREAKS,
    S.Tag.CAMELCASED, S.Tag.CAPITALIZED, S.Tag.CONTROL,
    S.Tag.DIGITS,
    S.Tag.LETTERS, S.Tag.LOWERCASED,
    S.Tag.MARK, S.Tag.MIXEDCASED,
    S.Tag.NUMBER, S.Tag.NUMERAL,
    S.Tag.PUNCT,
    S.Tag.SPACES, S.Tag.STOP, S.Tag.SYMBOL,
    S.Tag.UPPERCASED
)
MULTICHAR_TAGS = (S.Tag.LETTERS, S.Tag.DIGITS, S.Tag.SPACES, S.Tag.BREAKS)
SINGLE_CHAR_TAGS = (t for t in ALL_TAGS if t not in MULTICHAR_TAGS)
GREEK_CHARS = ("".join(chr(x) for x in range(0x370, 0x3FF)) + 
               "".join(chr(x) for x in range(0x1F00, 0x1FFF)))

class YieldNewTokenTests(TestCase):

    def testUnequalTags(self):
        for t1 in ALL_TAGS:
            for t2 in ALL_TAGS:
                if t1 == t2: continue
                self.assertEqual(S.YieldNewToken(t1, t2), True,
                                 "unequal tags must always return True")

    def testEqualTagsButNotWordNumericWhitespace(self):
        for tag in SINGLE_CHAR_TAGS:
            self.assertEqual(S.YieldNewToken(tag, tag), True,
                             "%s does not return True" % S.Tag.toStr(tag))

    def testEqualWordNumericWhitespaceTags(self):
        for tag in MULTICHAR_TAGS:
            self.assertEqual(S.YieldNewToken(tag, tag), False,
                             "%s does not return False" % S.Tag.toStr(tag))

class GetTagValueTests(TestCase):

    def testStopCharacters(self):
        for char in S.STOP_CHARS:
            tag = S.GetTagValue(char, S.Category.Po)
            self.assertEqual(tag, S.Tag.STOP,
                             "'%s' (0x%x) is %s, not STOP" %
                             (char, ord(char), S.Tag.toStr(tag)))

class GetCharCategoryTests(TestCase):

    def testNonRemappedCharacters(self):
        remapped_chars = ""

        for vals in S.REMAPPED_CHARACTERS.values():
            for chars in vals.keys():
                remapped_chars += chars

        for i in range(0, 0xFFFF):
            char = chr(i)
            cat = category(char)

            if cat in ("Ll", "Lu") and char in GREEK_CHARS:
                cat = "Lg" if cat == "Ll" else "LG"

            if char not in remapped_chars:
                result = S.GetCharCategoryValue(char)
                self.assertEqual(result, getattr(S.Category, cat),
                                 "char '%s' has cat=%s; but received=%s" % 
                                 (char, cat, chr(result)))

    def testRemappedCharacters(self):
        for chars, cat in (
            ("\n\f\r\u0085\u008D", S.Category.Zl),
            ("\t\v", S.Category.Zs),
            ("\u0091\u0092", S.Category.Co),
            ("#&@\uFE5F\uFE60\uFE6B\uFF03\uFF06\uFF20",
             S.Category.So),
            ("%\u2030\u2031\uFE6A\uFF05", S.Category.Sm),
            ("\u201A\u201E\u301D", S.Category.Pi),
        ):
            for c in chars:
                result = S.GetCharCategoryValue(c)
                self.assertEqual(result, cat,
                                 "char '%s' (0x%x) has cat=%i; received=%i" % 
                                 (c, ord(c), cat, result))

class CodepointIterTests(TestCase):

    def testRegularString(self):
        expected = ((0, 1, S.Category.Ll, S.Tag.LETTERS),
                    (1, 2, S.Category.Nd, S.Tag.DIGITS),
                    (2, 3, S.Category.Zl, S.Tag.BREAKS))

        for idx, result in enumerate(S.CodepointIter("a1\n")):
            self.assertTupleEqual(expected[idx], result)

    def testBadString(self):
        expected = ((0, 1, S.Category.Ll, S.Tag.LETTERS),
                    (1, 2, S.Category.Cs, S.Tag.BAD),
                    (2, 3, S.Category.Zl, S.Tag.BREAKS))

        for idx, result in enumerate(S.CodepointIter("a\uD800\n")):
            self.assertTupleEqual(expected[idx], result)

    def testSurrogateString(self):
        expected = ((0, 1, S.Category.Ll, S.Tag.LETTERS),
                    (1, 3, S.Category.Lo, S.Tag.LETTERS),
                    (3, 4, S.Category.Zl, S.Tag.BREAKS))

        for idx, result in enumerate(S.CodepointIter("a\uD800\uDC00\n")):
            self.assertTupleEqual(expected[idx], result)

class CasetagTests(TestCase):

    def testAlnumCategory(self):
        self.assertEqual(S.CasetagAlphanumeric(b"ll1"), S.Tag.ALNUM_LOWER)
        self.assertEqual(S.CasetagAlphanumeric(b"Ul1"), S.Tag.ALNUM_UPPER)
        self.assertEqual(S.CasetagAlphanumeric(b"1l1"), S.Tag.ALNUM_DIGIT)
        self.assertEqual(S.CasetagAlphanumeric(b"2l1"), S.Tag.ALNUM_NUMERAL)
        self.assertEqual(S.CasetagAlphanumeric(b"Ll1"), S.Tag.ALNUM_OTHER)

    def testBadAlnumCategory(self):
        self.assertRaises(RuntimeError, S.CasetagAlphanumeric, b"mmmm")
        self.assertRaises(RuntimeError, S.CasetagAlphanumeric, b"xll1")

    def testLetterCategory(self):
        self.assertEqual(S.CasetagLetters(b"llll"), S.Tag.LOWERCASED)
        self.assertEqual(S.CasetagLetters(b"UUUU"), S.Tag.UPPERCASED)
        self.assertEqual(S.CasetagLetters(b"lUlU"), S.Tag.MIXEDCASED)
        self.assertEqual(S.CasetagLetters(b"UlUl"), S.Tag.CAMELCASED)
        self.assertEqual(S.CasetagLetters(b"Ulll"), S.Tag.CAPITALIZED)
        self.assertEqual(S.CasetagLetters(b"Llll"), S.Tag.LETTERS)

    def testBadLetterCategory(self):
        self.assertRaises(RuntimeError, S.CasetagLetters, b"mmmC")
        self.assertRaises(RuntimeError, S.CasetagLetters, b"xlll")

class CategoryTests(TestCase):

    def testToStr(self):
        for i in range(0, 128):
            self.assertEqual(chr(i), S.Category.toStr(bytes([i])))

class TagTests(TestCase):

    def testToStr(self):
        self.assertEqual(S.Tag.toStr(S.Tag.BREAKS), "BREAKS")

class TokenizeTests(TestCase):

    def testRegularExampleString(self):
        example = "\u0001\u00ADx\u02B0\u01BB\u01C5X111[$]?"
        cats = (b"^", b"%", b"lmLTU", b"111", b"(", b"$", b")", b".")

        for idx, token in enumerate(S.Tokenize(example)):
            self.assertEqual(cats[idx], token.cats)

    def testAlnumExampleString(self):
        """

        """
        example = "A defAult Sentence, with SoMe “20%” Bl1a-1blA αrecⅣ!"
        cats_b = b"UslllUlllsUlllllll.sllllsUlUls<11+>sUl1l-1llUsglll2."
        tok_list = [
            "A", " ", "defAult", " ",
            "Sentence", ",", " ", "with",
            " ", "SoMe", " ", "“",
            "20", "%", "”", " ",
            "Bl1a", "-", "1blA", " ",
            "αrecⅣ", "!"
        ]
        tag_list = [
            S.Tag.UPPERCASED, S.Tag.SPACES, S.Tag.MIXEDCASED, S.Tag.SPACES,
            S.Tag.CAPITALIZED, S.Tag.PUNCT, S.Tag.SPACES, S.Tag.LOWERCASED,
            S.Tag.SPACES, S.Tag.CAMELCASED, S.Tag.SPACES, S.Tag.PUNCT,
            S.Tag.DIGITS, S.Tag.SYMBOL, S.Tag.PUNCT, S.Tag.SPACES,
            S.Tag.ALNUM_UPPER, S.Tag.PUNCT, S.Tag.ALNUM_DIGIT, S.Tag.SPACES,
            S.Tag.ALNUM_LOWER, S.Tag.STOP
        ]
        tokens = list(S.TokenizeAlphanumeric(example, case_tags=True))
        self.assertEqual(len(tokens), len(tok_list))
        #noinspection PyArgumentList
        cats = bytearray()

        for i, t in enumerate(tokens):
            self.assertEqual(t.string, tok_list[i],
                             "expected '%s', found '%s' at position %i" % 
                             (tok_list[i], t.string, i))
            self.assertEqual(t.tag, tag_list[i],
                             "expected %s for '%s', found %s at position %i" % 
                             (S.Tag.toStr(tag_list[i]), t.string,
                              S.Tag.toStr(t.tag), i))
            self.assertEqual(len(t.string), len(t.cats))
            for c in t.cats: cats.append(c.real)

        self.assertSequenceEqual(cats_b, bytes(cats))

    def testTaggingModifierAlnumString(self):
        example = "\u02B0\u02B011"
        cats = (b"mm11",)

        for idx, token in enumerate(S.TokenizeAlphanumeric(example, True)):
            self.assertEqual(cats[idx], token.cats)
            self.assertEqual(S.Tag.ALNUM_DIGIT, token.tag)

    def testTokenizing100kRandomCharsTakesLessThanOneSec(self):
        #noinspection PyUnusedLocal
        string = "".join(chr(randint(1, 0xCFFE)) for i in range(100000))
        start = time()
        # Note that case tagging has no significant influence on the speed.
        tokens = len(tuple(S.Tokenize(string)))
        end = time()
        self.assertTrue(end - start < 1.0, "creating %i tokens took %.3f s" % 
                        (tokens, end - start))

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        string = "".join(chr(randint(1, 0xCFFE)) for dummy in range(100000))
        print("generated %i tokens" % len(tuple(S.Tokenize(string))))
    else:
        main()
