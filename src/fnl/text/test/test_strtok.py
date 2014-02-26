import fnl.text.strtok as S

from random import randint
from time import time
from unicodedata import category
from unittest import main, TestCase


class TokenizerTests(TestCase):

    EXAMPLE = (
        "UUUΘΘΘ ᾈαα"
        "αˀⅣlllƻƻƻ8"
        "²88\u0903\u0488\u0300_\u002D"
        ")\u00BB\u00AB,($\u005E+@!"
        "\n\u2029\u0007\u00AD\u0092"
    )
    TAGS = (
        "AAABBBMBEE"  # 10 (10)
        "EGJDDDHHHI"  # 10 (20)
        "NIIabcde"    # _8 (28)
        "fghijklmno"  # 10 (38)
        "KL^`["       # _5 (43)
    )

    def setUp(self):
        self.text = self.EXAMPLE

    def assertResult(self, tokenizer, offsets):
        for idx, (start, end, tag, morph) in enumerate(
            tokenizer.tag(self.text)
        ):
            self.assertSequenceEqual(offsets[idx], (start, end))
            self.assertSequenceEqual(self.TAGS[start:end], morph)

    def testSeparator(self):
        offsets = [
            (0, 6),
            (6, 7),
            (7, 38),
            (38, 40),
            (40, 43),
        ]
        tokenizer = S.SpaceTokenizer()
        self.assertResult(tokenizer, offsets)

    def testWord(self):
        offsets = [
            (0, 6), (6, 7), (7, 12), (12, 13), (13, 19), (19, 20),
            (20, 21), (21, 23), (23, 24), (24, 25), (25, 26), (26, 27),
            (27, 28), (28, 29), (29, 30), (30, 31), (31, 32), (32, 33),
            (33, 34), (34, 35), (35, 36), (36, 37), (37, 38), (38, 40),
            (40, 41), (41, 42), (42, 43),
        ]
        tokenizer = S.WordTokenizer()
        self.assertResult(tokenizer, offsets)

    def testAlnum(self):
        offsets = [
            (0, 6), (6, 7), (7, 20), (20, 21), (21, 23), (23, 24),
            (24, 25), (25, 26), (26, 27), (27, 28), (28, 29), (29, 30),
            (30, 31), (31, 32), (32, 33), (33, 34), (34, 35), (35, 36),
            (36, 37), (37, 38), (38, 40), (40, 41), (41, 42), (42, 43),
        ]
        tokenizer = S.AlnumTokenizer()
        self.assertResult(tokenizer, offsets)

    def testTokenizingLargeArticleTakesLessThanOneSec(self):
        #noinspection PyUnusedLocal
        # faster on entire BMP, slower on random ASCII or sentences
        # string = "".join(chr(randint(1, 0xD7FE)) for i in range(100000))
        # string = "".join(chr(randint(1, 127)) for i in range(100000))
        text = "The fox jumped over - uhm, what? Hell, whatever. " * 2000
        # ^^ 50*2k = 100k chars, 22*2k = 44k tokens (one long article) ^^
        # This tokenizer is slightly faster than the others:
        # tokenizer = S.Separator()
        # these two tokenizers take about the same as long, word a tad slower
        tokenizer = S.WordTokenizer()
        # tokenizer = S.AlnumTokenizer()
        start = time()
        # Tagging without morphology (None) is about 30% faster, obviously.
        tags = list(tokenizer.tag(text))
        end = time()
        # on an average MBP (2.66 GHz) this should take less than half a sec
        # using the slowest configuration
        self.assertTrue(end - start < 1.0, "creating %i tokens took %.3f s" %
                        (len(tags), end - start))

        # make sure they are all good start/end-positioned
        last = 0

        for idx, (start, end, tag, morph) in enumerate(sorted(tags)):
            self.assertEqual(last, start)
            self.assertTrue(len(morph) == end - start)
            last = end


class CharIterTests(TestCase):

    def testSurrogateCharacter(self):
        result = list(S.CategoryIter('ab\uD800\uDC00cd'))
        expected = [ord('D'), ord('D'), ord('H'), ord('D'), ord('D')]
        self.assertListEqual(expected, result)


class GetCharCategoryTests(TestCase):

    def testNonRemappedCharacters(self):
        remapped_chars = ""

        for vals in S.REMAPPED_CHARACTERS.values():
            for chars in vals:
                if isinstance(chars[0], set):
                    remapped_chars += "".join(chars[0])
                else:
                    remapped_chars += chars[0]

        for i in range(0, 0xFFFF):
            char = chr(i)
            cat = category(char)

            if cat in ("Ll", "Lu", "Lt") and S.IsGreek(char):
                cat = "Lg" if cat == "Ll" else "LG"

            if char not in remapped_chars:
                result = S.GetCharCategoryValue(char)
                self.assertEqual(result, getattr(S.Category, cat),
                                 "char '%s' has cat=%s; but received=%s" %
                                 (char, cat, chr(result)))


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        text = "".join(chr(randint(1, 0xD7FE)) for dummy in range(100000))
        tokenizer = S.WordTokenizer()
        tokenizer.tag(text)
        print("tagged", len(text.string), "chars with", len(text), "tokens")
    else:
        main()
