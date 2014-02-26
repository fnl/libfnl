"""
.. py: module:: strtok
   : synopsis: An offset-based string tokenizer for any Unicode text.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http: //www.gnu.org/licenses/agpl.html)
"""
from io import StringIO
from types import FunctionType
from unicodedata import category

__author__ = "Florian Leitner"

#################
# CONFIGURATION #
#################

NAMESPACE = "strtok"
"""
The default namespace for the tags added to a text by the tokenizers.
"""

STOP_CHARS = frozenset({
    "\u0021",  # EXCLAMATION MARK
    "\u002E",  # FULL STOP
    "\u003F",  # QUESTION MARK
    "\u037E",  # GREEK QUESTION MARK
    "\u055C",  # ARMENIAN EXCLAMATION MARK
    "\u055E",  # ARMENIAN QUESTION MAR
    "\u0589",  # ARMENIAN FULL STOP
    "\u05C3",  # HEBREW PUNCTUATION SOF PASUQ
    "\u061F",  # ARABIC QUESTION MARK
    "\u06D4",  # ARABIC FULL STOP
    "\u0700",  # SYRIAC END OF PARAGRAPH
    "\u0701",  # SYRIAC SUPRALINEAR FULL STOP
    "\u0702",  # SYRIAC SUBLINEAR FULL STOP
    "\u0964",  # DEVANAGARI DANDA
    "\u0965",  # DEVANAGARI DOUBLE DANDA
    "\u0F08",  # TIBETAN MARK SBRUL SHAD
    "\u0F0D",  # TIBETAN MARK SHAD
    "\u0F0E",  # TIBETAN MARK NYIS SHAD
    "\u0F0F",  # TIBETAN MARK TSHEG SHAD
    "\u0F10",  # TIBETAN MARK NYIS TSHEG SHAD
    "\u0F11",  # TIBETAN MARK RIN CHEN SPUNGS SHAD
    "\u0F12",  # TIBETAN MARK RGYA GRAM SHAD
    "\u104A",  # MYANMAR SIGN LITTLE SECTION
    "\u104B",  # MYANMAR SIGN SECTION
    "\u1362",  # ETHIOPIC FULL STOP
    "\u1367",  # ETHIOPIC QUESTION MARK
    "\u1368",  # ETHIOPIC PARAGRAPH SEPARATOR
    "\u166E",  # CANADIAN SYLLABICS FULL STOP
    "\u1803",  # MONGOLIAN FULL STOP
    "\u1809",  # MONGOLIAN MANCHU FULL STOP
    "\u1944",  # LIMBU EXCLAMATION MARK
    "\u1945",  # LIMBU QUESTION MARK
    "\u203C",  # DOUBLE EXCLAMATION MARK
    "\u203D",  # INTERROBANG (? + ! combined)
    "\u2047",  # DOUBLE QUESTION MARK
    "\u2048",  # QUESTION EXCLAMATION MARK
    "\u2049",  # EXCLAMATION QUESTION MARK
    "\u3002",  # IDEOGRAPHIC FULL STOP
    "\uFE12",  # PRESENTATION FORM FOR VERTICAL IDEOGRAPHIC FULL STOP
    "\uFE15",  # PRESENTATION FORM FOR VERTICAL EXCLAMATION MARK
    "\uFE16",  # PRESENTATION FORM FOR VERTICAL QUESTION MARK
    "\uFE52",  # SMALL FULL STOP
    "\uFE56",  # SMALL QUESTION MARK
    "\uFE57",  # SMALL EXCLAMATION MARK
    "\uFF01",  # FULLWIDTH EXCLAMATION MARK
    "\uFF0E",  # FULLWIDTH FULL STOP
    "\uFF1F",  # FULLWIDTH QUESTION MARK
    "\uFF61",  # HALFWIDTH IDEOGRAPHIC FULL STOP
})
"""
An assembly of the more specific sentence stop markers found in Unicode in
one of the following languages: Latin, Arabic, Chinese, Japanese, Korean,
Greek, Devanagari, Syriac, Hebrew, Armenian, Tibetan, Myanmar, Ethiopic.
These characters are assigned the : attr:`.Category.Ts`.

Potential sentence terminals, such as semicolon, colon, or ellipsis, are
not included.
"""


class Category:
    """
    Integer values for the Unicode categories that correspond to single ASCII
    characters. In other words, a category value always will be in the
    [1..127] range. This is useful to create a "morphology representation" that
    encodes the characters found in the string being tokenized.

    Three additional categories are added that are not found in UniCode:
    : attr:`.Lg`, :attr:`.LG`, and :attr:`.Ts`.

    Next, logical groupings of the categories are provided, too.

    Finally, a few class methods help identifying character assignments.
    """

    # 65 - 90 (A-Z)
    Lu = ord('A')
    "``A`` - upper-case letter"
    LG = ord('B')
    "``B`` - upper-case Greek character -- a non-standard Unicode category"
    Lt = ord('C')
    "``C`` - title-case letter only (East European glyphs, sans Greek)"
    Ll = ord('D')
    "``D`` - lower-case character"
    Lg = ord('E')
    "``E`` - lower-case Greek character -- a non-standard Unicode category"
    LC = ord('F')
    "``F`` - case character (no characters in this category)"
    Lm = ord('G')
    "``G`` - character modifier"
    Lo = ord('H')
    "``H`` - letter, other (symbols without a case)"
    Nd = ord('I')
    "``I`` - digit number"
    Nl = ord('J')
    "``J`` - letter number (Roman, Greek, etc. - aka. numerals)"
    Zl = ord('K')
    "``K`` - line separator; breaks"
    Zp = ord('L')
    "``L`` - paragraph separator"
    Zs = ord('M')
    "``M`` - space separator"
    No = ord('N')
    "``N`` - other number (superscript, symbol-like numbers, etc.)"

    # 97 - 122 (a-z)
    Mc = ord('a')
    "``a`` - combining space mark (East European glyphs, musical symbols)"
    Me = ord('b')
    "``b`` - combining, enclosing mark (Cyrillic number signs, etc.)"
    Mn = ord('c')
    "``c`` - non-spacing, combining mark (accent, tilde, actue, etc.)"
    Pc = ord('d')
    "``d`` - connector punctuation"
    Pd = ord('e')
    "``e`` - dash punctuation"
    Pe = ord('f')
    "``f`` - punctuation end (brackets, etc., sans two quotation marks)"
    Pf = ord('g')
    "``g`` - final quotation mark (like ``»``; ``>`` itself is in Sm)"
    Pi = ord("h")
    "``h`` - initial quotation mark (like ``«``; ``<`` itself is in Sm)"
    Po = ord('i')
    """``i`` - other punctuation (,, \*, ", ', /, : , ;, etc.), but
    excluding the sentence : data:`.STOP_CHARS` that are in :attr:`.Ts`, and
    sans characters that should be in other (@, #, &) or math (%) symbols."""
    Ps = ord('j')
    "``j`` - punctuation start (brackets, etc., sans three quotation marks)"
    Sc = ord('k')
    "``k`` - currency symbol"
    Sk = ord('l')
    "``l`` - modifier symbol"
    Sm = ord('m')
    "``m`` - math symbol"
    So = ord('n')
    "``n`` - other symbol (``|`` itself is in Sm)"
    Ts = ord('o')
    """``o`` - sentence terminals (., !, ?, etc.), a special category reserved
    specifically for the : data:`.STOP_CHARS`."""

    # 91 - 96
    Cs = ord('_')
    "``_`` - surrogate character (encoding error)"
    Cc = ord('^')
    "``^`` - control character (sans separators (Z?) and two Co chars)"
    Cf = ord('`')
    "````` - formatting character"
    Cn = ord(']')
    "``]`` - not assigned (no characters in this category)"
    Co = ord('[')
    "``[`` - other, private use"

    CONTROLS = frozenset({Cc, Cf, Cn, Co, Cs})
    WORD = frozenset({Lu, Ll, LG, Lg, Lt, LC, Lm, Lo, Nd, Nl, Zl, Zp, Zs})
    ALNUM = frozenset({Lu, Ll, Nd, Nl, LG, Lg, Lt, LC, Lm, Lo})
    LETTERS = frozenset({Lu, LG, Lt, Ll, Lg, LC, Lm, Lo})
    UPPERCASE_LETTERS = frozenset({Lu, LG, Lt})
    LOWERCASE_LETTERS = frozenset({Ll, Lg})
    OTHER_LETTERS = frozenset({LC, Lm, Lo})
    NUMBERS = frozenset({Nd, Nl, No})
    NUMERIC = frozenset({Nd, Nl})
    MARKS = frozenset({Mc, Me, Mn})
    PUNCTUATION = frozenset({Pc, Pd, Pe, Pf, Pi, Po, Ps, Ts})
    SYMBOLS = frozenset({Sc, Sk, Sm, So})
    SEPARATORS = frozenset({Zl, Zp, Zs})
    BREAKS = frozenset({Zl, Zp, })

    @classmethod
    def control(cls, cat: int) -> bool:
        """``True`` if *cat* is any control character category (C?)."""
        #return cat in cls.CONTROLS
        return 90 < cat < 97

    @classmethod
    def word(cls, cat: int) -> bool:
        """``True`` if *cat* is any letter, digit, numeral, or separator."""
        # category (L?, Nd, Nl, Z?).
        #return cat in cls.WORD
        return cat < 78

    @classmethod
    def alnum(cls, cat: int) -> bool:
        """``True`` if *cat* is any letter, digit, or numeral category"""
        # (L?, Nd, Nl).
        #return cat in cls.ALNUM
        return cat < 75

    @classmethod
    def letter(cls, cat: int) -> bool:
        """``True`` if *cat* is any letter category (L?)."""
        #return cat in cls.LETTERS
        return cat < 73

    @classmethod
    def uppercase(cls, cat: int) -> bool:
        """``True`` if *cat* is any upper-case letter category."""
        # (LG, Lt, Lu).
        return cat in cls.UPPERCASE_LETTERS

    @classmethod
    def lowercase(cls, cat: int) -> bool:
        """``True`` if *cat* is any lower-case letter category (Lg, Ll)."""
        return cat in cls.LOWERCASE_LETTERS

    @classmethod
    def other_letter(cls, cat: int) -> bool:
        """``True`` if *cat* is any non-upper- or -lower-case letter."""
        # (LC, Lm, Lo).
        return cat in cls.OTHER_LETTERS

    @classmethod
    def number(cls, cat: int) -> bool:
        """``True`` if *cat* is any number category (N?)."""
        return cat in cls.NUMBERS

    @classmethod
    def numeric(cls, cat: int) -> bool:
        """``True`` if *cat* is any numeric value (Nd, Nl)."""
        return cat in cls.NUMERIC

    @classmethod
    def digit(cls, cat: int) -> bool:
        """``True`` if *cat* is digit (Nd)."""
        return cat == Category.Nd

    @classmethod
    def numeral(cls, cat: int) -> bool:
        """``True`` if *cat* is numeral (Nl)."""
        return cat == Category.Nl

    @classmethod
    def mark(cls, cat: int) -> bool:
        """``True`` if *cat* is any mark category (M?)."""
        return cat in cls.MARKS

    @classmethod
    def punctuation(cls, cat: int) -> bool:
        """``True`` if *cat* is any punctuation category (P?)."""
        return cat in cls.PUNCTUATION

    @classmethod
    def symbol(cls, cat: int) -> bool:
        """``True`` if *cat* is any symbol character category (S?)."""
        return cat in cls.SYMBOLS

    @classmethod
    def separator(cls, cat: int) -> bool:
        """``True`` if *cat* is any separator category (Z?)."""
        return cat in cls.SEPARATORS

    @classmethod
    def breaker(cls, cat: int) -> bool:
        """``True`` if *cat* is any breaker separator category (Zl, Zp)."""
        return cat in cls.BREAKS

    @classmethod
    def space(cls, cat: int) -> bool:
        """``True`` if *cat* is a space (Zs)."""
        return cat == Category.Zs

    @classmethod
    def not_separator(cls, cat: int) -> bool:
        """``True`` if *cat* is not any separator category (Z?)."""
        return cat not in cls.SEPARATORS


GREEK_REMAPPED = frozenset({Category.Ll, Category.Lu, Category.Lt})
"""
Categories that contain Greek characters that will be remapped.
"""

CATEGORY_MAP = {
    "Lu": Category.Lu,
    "LG": Category.LG,
    "Lt": Category.Lt,
    "Ll": Category.Ll,
    "Lg": Category.Lg,
    "LC": Category.LC,
    "Lm": Category.Lm,
    "Lo": Category.Lo,
    "Nd": Category.Nd,
    "Nl": Category.Nl,
    "Zl": Category.Zl,
    "Zp": Category.Zp,
    "Zs": Category.Zs,
    "No": Category.No,
    "Mc": Category.Mc,
    "Me": Category.Me,
    "Mn": Category.Mn,
    "Pc": Category.Pc,
    "Pd": Category.Pd,
    "Pe": Category.Pe,
    "Pf": Category.Pf,
    "Pi": Category.Pi,
    "Po": Category.Po,
    "Ps": Category.Ps,
    "Sc": Category.Sc,
    "Sk": Category.Sk,
    "Sm": Category.Sm,
    "So": Category.So,
    "Ts": Category.Ts,
    "Cs": Category.Cs,
    "Cc": Category.Cc,
    "Cf": Category.Cf,
    "Cn": Category.Cn,
    "Co": Category.Co
}
"""
Mapping of Unicode category names to :class:`Category` attributes.
"""

REMAPPED_CHARACTERS = {
    # NOTE: Lt, Lu and Ll can not be remapped
    # (see GetCharCategoryValue and GREEK_REMAPPED)
    Category.Cc: {
        "\n": Category.Zl,
        "\f": Category.Zl,
        "\r": Category.Zl,
        "\u0085": Category.Zl,  # NEXT LINE (is in \s of regexes)
        # "\u008D": Category.Zl, # REVERSE LINE FEED (isn't in \s of regexes!)
        "\t": Category.Zs,
        "\v": Category.Zs,
        "\u0091": Category.Co,  # Private
        "\u0092": Category.Co,  # Private
    },
    Category.Po: {
        "#": Category.So,
        "&": Category.So,
        "@": Category.So,
        # Variants of #, &, @
        "\uFE5F": Category.So,
        "\uFE60": Category.So,
        "\uFE6B": Category.So,
        "\uFF03": Category.So,
        "\uFF06": Category.So,
        "\uFF20": Category.So,
        "%": Category.Sm,
        # Variants of %
        "\u0609": Category.Sm,
        "\u060A": Category.Sm,
        "\u066A": Category.Sm,
        "\u2030": Category.Sm,
        "\u2031": Category.Sm,
        "\uFE6A": Category.Sm,
        "\uFF05": Category.Sm,
        # STOP_CHARS
        "\u0021": Category.Ts,  # EXCLAMATION MARK
        "\u002E": Category.Ts,  # FULL STOP
        "\u003F": Category.Ts,  # QUESTION MARK
        "\u037E": Category.Ts,  # GREEK QUESTION MARK
        "\u055C": Category.Ts,  # ARMENIAN EXCLAMATION MARK
        "\u055E": Category.Ts,  # ARMENIAN QUESTION MAR
        "\u0589": Category.Ts,  # ARMENIAN FULL STOP
        "\u05C3": Category.Ts,  # HEBREW PUNCTUATION SOF PASUQ
        "\u061F": Category.Ts,  # ARABIC QUESTION MARK
        "\u06D4": Category.Ts,  # ARABIC FULL STOP
        "\u0700": Category.Ts,  # SYRIAC END OF PARAGRAPH
        "\u0701": Category.Ts,  # SYRIAC SUPRALINEAR FULL STOP
        "\u0702": Category.Ts,  # SYRIAC SUBLINEAR FULL STOP
        "\u0964": Category.Ts,  # DEVANAGARI DANDA
        "\u0965": Category.Ts,  # DEVANAGARI DOUBLE DANDA
        "\u0F08": Category.Ts,  # TIBETAN MARK SBRUL SHAD
        "\u0F0D": Category.Ts,  # TIBETAN MARK SHAD
        "\u0F0E": Category.Ts,  # TIBETAN MARK NYIS SHAD
        "\u0F0F": Category.Ts,  # TIBETAN MARK TSHEG SHAD
        "\u0F10": Category.Ts,  # TIBETAN MARK NYIS TSHEG SHAD
        "\u0F11": Category.Ts,  # TIBETAN MARK RIN CHEN SPUNGS SHAD
        "\u0F12": Category.Ts,  # TIBETAN MARK RGYA GRAM SHAD
        "\u104A": Category.Ts,  # MYANMAR SIGN LITTLE SECTION
        "\u104B": Category.Ts,  # MYANMAR SIGN SECTION
        "\u1362": Category.Ts,  # ETHIOPIC FULL STOP
        "\u1367": Category.Ts,  # ETHIOPIC QUESTION MARK
        "\u1368": Category.Ts,  # ETHIOPIC PARAGRAPH SEPARATOR
        "\u166E": Category.Ts,  # CANADIAN SYLLABICS FULL STOP
        "\u1803": Category.Ts,  # MONGOLIAN FULL STOP
        "\u1809": Category.Ts,  # MONGOLIAN MANCHU FULL STOP
        "\u1944": Category.Ts,  # LIMBU EXCLAMATION MARK
        "\u1945": Category.Ts,  # LIMBU QUESTION MARK
        "\u203C": Category.Ts,  # DOUBLE EXCLAMATION MARK
        "\u203D": Category.Ts,  # INTERROBANG (? + ! combined)
        "\u2047": Category.Ts,  # DOUBLE QUESTION MARK
        "\u2048": Category.Ts,  # QUESTION EXCLAMATION MARK
        "\u2049": Category.Ts,  # EXCLAMATION QUESTION MARK
        "\u3002": Category.Ts,  # IDEOGRAPHIC FULL STOP
        "\uFE12": Category.Ts,  # PRESENTATION FORM FOR VERTICAL
                                # IDEOGRAPHIC FULL STOP
        "\uFE15": Category.Ts,  # PRESENTATION FORM FOR VERTICAL
                                # EXCLAMATION MARK
        "\uFE16": Category.Ts,  # PRESENTATION FORM FOR VERTICAL QUESTION MARK
        "\uFE52": Category.Ts,  # SMALL FULL STOP
        "\uFE56": Category.Ts,  # SMALL QUESTION MARK
        "\uFE57": Category.Ts,  # SMALL EXCLAMATION MARK
        "\uFF01": Category.Ts,  # FULLWIDTH EXCLAMATION MARK
        "\uFF0E": Category.Ts,  # FULLWIDTH FULL STOP
        "\uFF1F": Category.Ts,  # FULLWIDTH QUESTION MARK
        "\uFF61": Category.Ts,  # HALFWIDTH IDEOGRAPHIC FULL STOP
    },
    Category.Ps: {
        "\u201A": Category.Pi,  # SINGLE LOW-9 QUOTATION MARK
        "\u201E": Category.Pi,  # DOUBLE LOW-9 QUOTATION MARK
        "\u301D": Category.Pf,  # RIGHT DOUBLE QUOTATION MARK
    },
    Category.Pe: {
        "\u301E": Category.Pf,  # DOUBLE PRIME QUOTATION MARK
        "\u301F": Category.Pf,  # LOW DOUBLE PRIME QUOTATION MARK
    }
}
"""
Remapped Unicode character categories: ``{ from_cat: { char: to_cat } }``.

This mapping is mostly to correct special cases that, from a linguistic
perspective, are better represented by another Category.
"""


##################
# IMPLEMENTATION #
##################
class Tokenizer:
    """
    Abstract tokenizer implementing the actual procedure.
    """

    def tag(self, text: str):
        """
        Tokenize the given *text* by yielding offset tags.

        A Token is a tuple of the start/end offsets, the token tag,
        and a morphological representation of the token.

        :param text: The string to tokenize.
        :return: An iterator over (start, end, tag, morphology) tag tuples.
        """
        cats = None
        morph = None
        start = 0
        State = lambda c: False  # the tag (aka lexer "state")

        for end, cat in enumerate(CategoryIter(text)):
            if State(cat):
                if not cats:
                    cats = StringIO()
                    cats.write(morph)

                cats.write(chr(cat))
            else:
                if end:
                    morph = cats.getvalue() if cats else morph
                    yield start, end, State.__name__, morph

                cats = None
                morph = chr(cat)
                start = end
                State = self._findState(cat)

        if cats or morph:
            morph = cats.getvalue() if cats else morph
            yield start, len(text), State.__name__, morph

    @staticmethod
    def _findState(cat: int) -> FunctionType:
        """
        Abstract method that should define the state of the iteration
        thorough a string and thereby the token boundaries.

        The implementing method should return the appropriate function that
        evaluates to ``True`` if the same category (or category group) is
        sent to it.
        """
        raise NotImplementedError("abstract")


class SpaceTokenizer(Tokenizer):
    """
    A tokenizer that only separates `Z?` category characters (line- and
    paragraph-breaks, as well as spaces) from all others.

    Produces the following tags:

        * separator (Z?)+
        * not_separator (all others)+
    """

    @staticmethod
    def _findState(cat: int) -> FunctionType:
        if Category.separator(cat):
            return Category.separator
        else:
            return Category.not_separator


class WordTokenizer(Tokenizer):
    """
    A tokenizer that creates single character tokens for all non-letter,
    -digit, -numeral, and -separator character, while it joins the others
    as long as the next character is of that same category, too.

    Produces the following tags:

        * breaker (Zl, Zp)+
        * digit (Nd)+
        * letter (L?)+
        * numeral (Nl)+
        * space (Zs)+
        * glyph (all others){1}
    """

    @staticmethod
    def glyph(_) -> bool:
        return False

    @staticmethod
    def _findState(cat: int) -> FunctionType:
        if not Category.word(cat):
            return WordTokenizer.glyph

        for State in (Category.letter, Category.space, Category.digit,
                      Category.breaker, Category.numeral):
            if State(cat):
                return State

        raise RuntimeError("no State for cat='%s'" % chr(cat))


class AlnumTokenizer(Tokenizer):
    """
    A tokenizer that creates single character tokens for all non-separator
    and -alphanumeric characters, and joins the latter two as long as the
    next character is of that same category, too.

    Produces the following tag IDs:

        * alnum (L?, Nl, Nd)+
        * breaker (Zl, Zp)+
        * space (Zs)+
        * glyph (all others){1}
    """

    @staticmethod
    def _findState(cat: int) -> FunctionType:
        if not Category.word(cat):
            return WordTokenizer.glyph
        elif Category.alnum(cat):
            return Category.alnum
        elif Category.space(cat):
            return Category.space
        elif Category.breaker(cat):
            return Category.breaker
        else:
            raise RuntimeError("no tests for cat='%s'" % chr(cat))


def TokenOffsets(string: str):
    """
    Yield the offsets of all Unicode category borders in the *string*,
    including the initial 0 and the final offset value of ``len(string)``.

    Caplitalized words special case: A single upper case letter ('Lu')
    followed by lower case letters ('Ll') are treated as a single token.
    """
    if string is not None and len(string) > 0:
        yield 0
        last = category(string[0])

        for i in range(1, len(string)):
            current = category(string[i])

            if last != current:
                # "join" capitalized tokens:
                if last == 'Lu' and \
                   current == 'Ll' and \
                   (i == 1 or (i > 1 and category(string[i - 2]) != 'Lu')):
                    pass
                else:
                    yield i

            last = current

        yield len(string)


def CategoryIter(string: str) -> iter:
    """
    Yield category integers for a *text*, one per (real - wrt. Surrogate
    Pairs) character in the *text*.
    """
    char_iter = iter(string)

    while True:
        c = next(char_iter)

        if '\ud800' <= c < '\udc00':
            # convert the surrogate pair to one single wide character
            l = next(char_iter)

            if not '\udc00' <= l < '\ue000':
                raise UnicodeError('low surrogate character missing')

            o = 0x10000 + (ord(c) - 0xD800) * 0x400 + (ord(l) - 0xDC00)
            c = chr(o)

        yield GetCharCategoryValue(c)


def GetCharCategoryValue(character: chr) -> int:
    """
    Return the (remapped) Unicode category value of a *character*.

    :raises: TypeError If the *character* can not be mapped by
                       :func:`unicodedata.category`
    """
    cat = CATEGORY_MAP[category(character)]

    if cat in GREEK_REMAPPED:
        if IsGreek(character):
            if cat == Category.Ll:
                return Category.Lg
            else:
                return Category.LG
    elif cat in REMAPPED_CHARACTERS and character in REMAPPED_CHARACTERS[cat]:
        cat = REMAPPED_CHARACTERS[cat][character]

    return cat


def IsGreek(char: chr) -> bool:
    """
    Return ``True`` if the *char* is on one of the Greek code-pages.
    """
    return "\u036F" < char < "\u1FFF" and not ("\u03FF" < char < "\u1F00")
