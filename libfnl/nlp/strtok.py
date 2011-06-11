"""
.. py:module:: strtok
   :synopsis: A string tokenizer for any Unicode text.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
"""

from io import StringIO
from types import FunctionType
from libfnl.nlp.text import Unicode
from unicodedata import category

__author__ = "Florian Leitner"
__version__ = "1.0"

NAMESPACE = "morphology"
"""
The default namespace string for the tags added to a text by the tokenizers.
"""

STOP_CHARS = {
    "\u0021", # EXCLAMATION MARK
    "\u002E", # FULL STOP
    "\u003F", # QUESTION MARK
    "\u037E", # GREEK QUESTION MARK
    "\u055C", # ARMENIAN EXCLAMATION MARK
    "\u055E", # ARMENIAN QUESTION MAR
    "\u0589", # ARMENIAN FULL STOP
    "\u05C3", # HEBREW PUNCTUATION SOF PASUQ
    "\u061F", # ARABIC QUESTION MARK
    "\u06D4", # ARABIC FULL STOP
    "\u0700", # SYRIAC END OF PARAGRAPH
    "\u0701", # SYRIAC SUPRALINEAR FULL STOP
    "\u0702", # SYRIAC SUBLINEAR FULL STOP
    "\u0964", # DEVANAGARI DANDA
    "\u0965", # DEVANAGARI DOUBLE DANDA
    "\u0F08", # TIBETAN MARK SBRUL SHAD
    "\u0F0D", # TIBETAN MARK SHAD
    "\u0F0E", # TIBETAN MARK NYIS SHAD
    "\u0F0F", # TIBETAN MARK TSHEG SHAD
    "\u0F10", # TIBETAN MARK NYIS TSHEG SHAD
    "\u0F11", # TIBETAN MARK RIN CHEN SPUNGS SHAD
    "\u0F12", # TIBETAN MARK RGYA GRAM SHAD
    "\u104A", # MYANMAR SIGN LITTLE SECTION
    "\u104B", # MYANMAR SIGN SECTION
    "\u1362", # ETHIOPIC FULL STOP
    "\u1367", # ETHIOPIC QUESTION MARK
    "\u1368", # ETHIOPIC PARAGRAPH SEPARATOR
    "\u166E", # CANADIAN SYLLABICS FULL STOP
    "\u1803", # MONGOLIAN FULL STOP
    "\u1809", # MONGOLIAN MANCHU FULL STOP
    "\u1944", # LIMBU EXCLAMATION MARK
    "\u1945", # LIMBU QUESTION MARK
    "\u203C", # DOUBLE EXCLAMATION MARK
    "\u203D", # INTERROBANG (? + ! combined)
    "\u2047", # DOUBLE QUESTION MARK
    "\u2048", # QUESTION EXCLAMATION MARK
    "\u2049", # EXCLAMATION QUESTION MARK
    "\u3002", # IDEOGRAPHIC FULL STOP
    "\uFE12", # PRESENTATION FORM FOR VERTICAL IDEOGRAPHIC FULL STOP
    "\uFE15", # PRESENTATION FORM FOR VERTICAL EXCLAMATION MARK
    "\uFE16", # PRESENTATION FORM FOR VERTICAL QUESTION MARK
    "\uFE52", # SMALL FULL STOP
    "\uFE56", # SMALL QUESTION MARK
    "\uFE57", # SMALL EXCLAMATION MARK
    "\uFF01", # FULLWIDTH EXCLAMATION MARK
    "\uFF0E", # FULLWIDTH FULL STOP
    "\uFF1F", # FULLWIDTH QUESTION MARK
    "\uFF61", # HALFWIDTH IDEOGRAPHIC FULL STOP
}
"""
An assembly of the more specific sentence stop markers found in Unicode in
one of the following languages: Latin, Arabic, Chinese, Japanese, Korean,
Greek, Devanagari, Syriac, Hebrew, Armenian, Tibetan, Myanmar, Ethiopic.
These characters are assigned the :attr:`.Category.Ts`.

Potential sentence terminals, such as semicolon, colon, or ellipsis, are
not included.
"""


class Tokenizer:
    """
    Abstract tokenizer implementing the actual procedure.
    """

    def __init__(self, namespace:str=NAMESPACE):
        """
        The *namespace* is the string used for the tags created on the text.
        """
        self.namespace = namespace

    def tag(self, text:Unicode):
        """
        Tag the given *text* with tokens.

        .. warning::

            Any existing tags on the *text* that are in the same
            namespace as the tokenizer is set to will be deleted.
        """
        assert len(text), "empty text"
        text._tags[self.namespace] = dict() # using unsafe!
        start = 0
        cats = StringIO()
        State = lambda c: False

        for end, cat in CharIter(text):
            if State(cat):
                cats.write(chr(cat))
            else:
                if end: text.addTagUnsafe(self.namespace, cats.getvalue(),
                                          start, end)
                start = end
                cats = StringIO()
                cats.write(chr(cat))
                State = self._findState(cat)

        if cats: text.addTagUnsafe(self.namespace, cats.getvalue(),
                                   start, len(text))

    def _findState(self, cat:int) -> FunctionType:
        """
        Abstract method that should define the state of the iteration
        thorough a string and thereby the token boundaries.

        The implementing method should return the appropriate function that
        evaluates to ``True`` if the same category (or category group) is
        sent to it.
        """
        raise NotImplementedError("abstract")


class Separator(Tokenizer):
    """
    A tokenizer that only separates `Z?` category character (line- and
    paragraph-breaks, as well as spaces) from all others.
    """

    def _findState(self, cat:int) -> FunctionType:
        if Category.isSeparator(cat):
            return Category.isSeparator
        else:
            return Category.notSeparator


class WordTokenizer(Tokenizer):
    """
    A tokenizer that creates single character tokens for all non-letter,
    -digit, -numeral, and -separator character, while it joins the others
    as long as the next character is of that same category, too.
    """

    def _findState(self, cat:int) -> FunctionType:
        if not Category.isWord(cat):
            return lambda cat: False
        elif Category.isLetter(cat):
            return Category.isLetter
        elif Category.isSeparator(cat):
            return Category.isSeparator
        elif Category.isDigit(cat):
            return Category.isDigit
        elif Category.isNumeral(cat):
            return Category.isNumeral
        else:
            raise RuntimeError("no tests for cat='%s'" % chr(cat))


class AlnumTokenizer(Tokenizer):
    """
    A tokenizer that creates single character tokens for all non-separator
    and -alphanumeric characters, and joins the latter two as long as the
    next character is of that same category, too.
    """

    def _findState(self, cat:int) -> FunctionType:
        if not Category.isWord(cat):
            return lambda cat: False
        elif Category.isAlnum(cat):
            return Category.isAlnum
        elif Category.isSeparator(cat):
            return Category.isSeparator
        else:
            raise RuntimeError("no tests for cat='%s'" % chr(cat))


class Category:
    """
    Integer values for the Unicode categories that correspond to single ASCII
    characters. In other words, a category value always will be in the
    [1..127] range.

    Three additional categories are added that are not found in UniCode:
    :attr:`.Lg`, :attr:`.LG`, and :attr:`.Ts`.

    """

    # 65 - 90 (A-Z)
    Lu = ord('A')
    "``A`` - upper-case letter"
    LG = ord('B')
    "``B`` - upper-case Greek character"
    Lt = ord('C')
    "``C`` - title-case letter only (Greek and East European glyphs)"
    Ll = ord('D')
    "``D`` - lower-case character"
    Lg = ord('E')
    "``E`` - lower-case Greek character"
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
    """``i`` - other punctuation (,, \*, ", ', /, :, ;, etc.), but
    excluding the sentence :data:`.STOP_CHARS` that are in :attr:`Ts`, and
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
    specifically for the :data:`.STOP_CHARS`."""

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

    CONTROLS = { Cc, Cf, Cn, Co, Cs }
    WORD = { Lu, Ll, LG, Lg, Lt, LC, Lm, Lo, Nd, Nl, Zl, Zp, Zs }
    ALNUM = { Lu, Ll, Nd, Nl, LG, Lg, Lt, LC, Lm, Lo }
    LETTERS = { Lu, LG, Lt, Ll, Lg, LC, Lm, Lo }
    UPPERCASE_LETTERS = { Lu, LG, Lt }
    LOWERCASE_LETTERS = { Ll, Lg }
    OTHER_LETTERS = { LC, Lm, Lo }
    NUMBERS = { Nd, Nl, No }
    NUMERIC = { Nd, Nl }
    MARKS = { Mc, Me, Mn }
    PUNCTUATION = { Pc, Pd, Pe, Pf, Pi, Po, Ps, Ts }
    SYMBOLS = { Sc, Sk, Sm, So }
    SEPARATORS = { Zl, Zp, Zs }

    @classmethod
    def isControl(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any control character category (C?).
        #return cat in cls.CONTROLS
        return 90 < cat < 97

    @classmethod
    def isWord(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any letter, digit, numeral, or separator
        # category (L?, Nd, Nl, Z?).
        #return cat in cls.WORD
        return cat < 78

    @classmethod
    def isAlnum(cls, cat:int) -> bool:
        #``True`` if the *cat* is any letter, digit, or numeral category
        # (L?, Nd, Nl).
        #return cat in cls.ALNUM
        return cat < 75

    @classmethod
    def isLetter(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any letter category (L?).
        #return cat in cls.LETTERS
        return cat < 73

    @classmethod
    def isUppercase(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any upper-case letter category
        # (LG, Lt, Lu).
        return cat in cls.UPPERCASE_LETTERS

    @classmethod
    def isLowercase(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any lower-case letter category (Lg, Ll).
        return cat in cls.LOWERCASE_LETTERS

    @classmethod
    def isOtherLetter(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any non-upper- or -lower-case letter
        # (LC, Lm, Lo).
        return cat in cls.OTHER_LETTERS

    @classmethod
    def isNumber(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any number category (N?).
        return cat in cls.NUMBERS

    @classmethod
    def isNumeric(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any numeric value (Nd, Nl).
        return cat in cls.NUMERIC

    @classmethod
    def isDigit(cls, cat:int) -> bool:
        # ``True`` if the *cat* is digit (Nd).
        return cat == Category.Nd

    @classmethod
    def isNumeral(cls, cat:int) -> bool:
        # ``True`` if the *cat* is numeral (Nl).
        return cat == Category.Nl

    @classmethod
    def isMark(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any mark category (Cf, M?).
        return cat in cls.MARKS

    @classmethod
    def isPunctuation(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any punctuation category (P?).
        return cat in cls.PUNCTUATION

    @classmethod
    def isSymbol(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any symbol character category (S?).
        return cat in cls.SYMBOLS

    @classmethod
    def isSeparator(cls, cat:int) -> bool:
        # ``True`` if the *cat* is any separator category (Z?).
        return cat in cls.SEPARATORS

    @classmethod
    def notSeparator(cls, cat:int) -> bool:
        # ``True`` if the *cat* is not any separator category (Z?).
        return cat not in cls.SEPARATORS


def CharIter(text:str) -> iter([(int, int)]):
    """
    Yields (offset, category) pairs for any *text* string, one per (real -
    wrt. the surrogate range) character in the *text*.
    """
    pos = 0
    strlen = len(text)

    while pos < strlen:
        cat = GetCharCategoryValue(text[pos])
        char_len = 1

        if cat == Category.Cs and pos + 1 < strlen:
            try:
                cat = GetSurrogateCategoryValue(text[pos:pos + 2])
                char_len = 2
            except TypeError:
                pass

        yield pos, cat
        pos += char_len


def GetCharCategoryValue(character:chr) -> int:
    """
    Return the (remapped) Unicode category value of a *character*.

    :raises: TypeError If the *character* can not be mapped by
                       :func:`unicodedata.category`
    """
    cat = getattr(Category, category(character))

    if cat in (Category.Ll, Category.Lu) and IsGreek(character):
        if cat == Category.Ll: cat = Category.Lg
        else:                  cat = Category.LG
    elif cat in REMAPPED_CHARACTERS and character in REMAPPED_CHARACTERS[cat]:
        cat = REMAPPED_CHARACTERS[cat][character]

    return cat


def GetSurrogateCategoryValue(surrogate_pair:str) -> int:
    """
    Return the (remapped) category value of a *surrogate pair*.

    :raises: TypeError If the *surrogate pair* can not be mapped by
                       :func:`unicodedata.category`
    """
    cat = getattr(Category, category(surrogate_pair))

    if cat in REMAPPED_CHARACTERS and \
       surrogate_pair in REMAPPED_CHARACTERS[cat]:
        cat = REMAPPED_CHARACTERS[cat][surrogate_pair]

    return cat


def IsGreek(char:chr) -> bool:
    """
    Return ``True`` if the *char* is on one of the Greek code-pages.
    """
    return "\u0370" <= char < "\u03FF" or "\u1F00" <= char < "\u1FFF"


REMAPPED_CHARACTERS = {
    Category.Cc: {
        "\n": Category.Zl,
        "\f": Category.Zl,
        "\r": Category.Zl,
        "\u0085": Category.Zl, # NEXT LINE
        "\u008D": Category.Zl, # REVERSE LINE FEED
        "\t": Category.Zs,
        "\v": Category.Zs,
        "\u0091": Category.Co, # Private
        "\u0092": Category.Co, # Private
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
        "\u0021": Category.Ts, # EXCLAMATION MARK
        "\u002E": Category.Ts, # FULL STOP
        "\u003F": Category.Ts, # QUESTION MARK
        "\u037E": Category.Ts, # GREEK QUESTION MARK
        "\u055C": Category.Ts, # ARMENIAN EXCLAMATION MARK
        "\u055E": Category.Ts, # ARMENIAN QUESTION MAR
        "\u0589": Category.Ts, # ARMENIAN FULL STOP
        "\u05C3": Category.Ts, # HEBREW PUNCTUATION SOF PASUQ
        "\u061F": Category.Ts, # ARABIC QUESTION MARK
        "\u06D4": Category.Ts, # ARABIC FULL STOP
        "\u0700": Category.Ts, # SYRIAC END OF PARAGRAPH
        "\u0701": Category.Ts, # SYRIAC SUPRALINEAR FULL STOP
        "\u0702": Category.Ts, # SYRIAC SUBLINEAR FULL STOP
        "\u0964": Category.Ts, # DEVANAGARI DANDA
        "\u0965": Category.Ts, # DEVANAGARI DOUBLE DANDA
        "\u0F08": Category.Ts, # TIBETAN MARK SBRUL SHAD
        "\u0F0D": Category.Ts, # TIBETAN MARK SHAD
        "\u0F0E": Category.Ts, # TIBETAN MARK NYIS SHAD
        "\u0F0F": Category.Ts, # TIBETAN MARK TSHEG SHAD
        "\u0F10": Category.Ts, # TIBETAN MARK NYIS TSHEG SHAD
        "\u0F11": Category.Ts, # TIBETAN MARK RIN CHEN SPUNGS SHAD
        "\u0F12": Category.Ts, # TIBETAN MARK RGYA GRAM SHAD
        "\u104A": Category.Ts, # MYANMAR SIGN LITTLE SECTION
        "\u104B": Category.Ts, # MYANMAR SIGN SECTION
        "\u1362": Category.Ts, # ETHIOPIC FULL STOP
        "\u1367": Category.Ts, # ETHIOPIC QUESTION MARK
        "\u1368": Category.Ts, # ETHIOPIC PARAGRAPH SEPARATOR
        "\u166E": Category.Ts, # CANADIAN SYLLABICS FULL STOP
        "\u1803": Category.Ts, # MONGOLIAN FULL STOP
        "\u1809": Category.Ts, # MONGOLIAN MANCHU FULL STOP
        "\u1944": Category.Ts, # LIMBU EXCLAMATION MARK
        "\u1945": Category.Ts, # LIMBU QUESTION MARK
        "\u203C": Category.Ts, # DOUBLE EXCLAMATION MARK
        "\u203D": Category.Ts, # INTERROBANG (? + ! combined)
        "\u2047": Category.Ts, # DOUBLE QUESTION MARK
        "\u2048": Category.Ts, # QUESTION EXCLAMATION MARK
        "\u2049": Category.Ts, # EXCLAMATION QUESTION MARK
        "\u3002": Category.Ts, # IDEOGRAPHIC FULL STOP
        "\uFE12": Category.Ts, # PRESENTATION FORM FOR VERTICAL IDEOGRAPHIC FULL STOP
        "\uFE15": Category.Ts, # PRESENTATION FORM FOR VERTICAL EXCLAMATION MARK
        "\uFE16": Category.Ts, # PRESENTATION FORM FOR VERTICAL QUESTION MARK
        "\uFE52": Category.Ts, # SMALL FULL STOP
        "\uFE56": Category.Ts, # SMALL QUESTION MARK
        "\uFE57": Category.Ts, # SMALL EXCLAMATION MARK
        "\uFF01": Category.Ts, # FULLWIDTH EXCLAMATION MARK
        "\uFF0E": Category.Ts, # FULLWIDTH FULL STOP
        "\uFF1F": Category.Ts, # FULLWIDTH QUESTION MARK
        "\uFF61": Category.Ts, # HALFWIDTH IDEOGRAPHIC FULL STOP
    },
    Category.Ps: {
        "\u201A": Category.Pi, # SINGLE LOW-9 QUOTATION MARK
        "\u201E": Category.Pi, # DOUBLE LOW-9 QUOTATION MARK
        "\u301D": Category.Pf, # RIGHT DOUBLE QUOTATION MARK
    },
    Category.Pe: {
        "\u301E": Category.Pf, # DOUBLE PRIME QUOTATION MARK
        "\u301F": Category.Pf, # LOW DOUBLE PRIME QUOTATION MARK
    }
}
"Remapped Unicode character categories: ``{ from_cat: { char: to_cat } }``."


###############
# UNUSED CODE #
###############

class Tag:
    """
    Tags for tokens representing a logical grouping strategy of
    the Unicode categories into tag "supersets".

    All tags are supersets of the (re-mapped) Unicode categories, except for
    STOP, which is a subset of characters found in Po and are used as
    sentence stop characters.
    """

    # PURE TAGS, STRING TOKENS
    LETTERS = 0b00000001 #   1
    "Letter category characters (L.)."
    DIGITS = 0b00000010 #   2
    "Number (digit) category chars (Nd)."
    SPACES = 0b00000100 #   4
    "Space characters (U+20, U+A0, and quite a few more; Zs (with fixes))."

    # PURE TAGS, CHARACTER TOKENS
    BAD = 0b00000000 #   0
    "Characters from a 'bad' category: C[nos] and LC."
    SYMBOL = 0b00001000 #   8
    "Symbol category characters (S.)."
    PUNCT = 0b00010000 #  16
    "Punctuation category chars (P.) except STOP chars in Po."
    CONTROL = 0b00100000 #  32
    "Control characters (Cc, fixed) except those in BREAKS, SPACES, and BAD."

    # COMBINED TAGS, CHARACTER+STRING TOKENS
    NUMERAL = 0b00001010 #  10, SYMBOL & DIGITS
    "Number letter category characters (Nl)."
    ALPHANUMERIC = 0b00001011 #  11, LETTERS & DIGITS & NUMERAL
    """Special tag when joining LETTERS, DIGITS, and NUMERAL tagged tokens
    by using :py:func:`.TokenizeAlphanumeric`."""
    NUMBER = 0b00010010 #  18, PUNCT & DIGITS
    "Number, other category (No, e.g. subscript indices) characters."
    MARK = 0b00100001 #  33, CONTROL & LETTERS
    "The Mark categories and Other format category characters (M. and Cf)."

    # COMBINED TAGS, CHARACTER ONLY TOKENS
    STOP = 0b00011000 #  24, SYMBOL & PUNCT
    "Sentence stop markers, a special subset of Po (:py:data:`.STOP_CHARS`)."
    BREAKS = 0b00100100 #  36, CONTROL & SPACES
    "Line-break characters (U+0A, U+0C, U+0D, U+85, U+2028, U+2029: Zl & Zp)."

    _WORDS = 0b01000000
    # Useful to detect the 'special' word case tags below; Any token tagged
    # with any of them can be separated from all others by testing
    # token.tag > Tag._WORDS
    # _WORDS all have an integer value > 64 (0b01000000, 0x40)
    # These tokens need to be created post-classification and in some cases
    # might be the result of joining LETTERS and DIGITS tokens.

    # SPECIALIZED LETTER TOKENS (tag is determined post-tokenization)
    LOWERCASED = 0b01000001 #  65 b"^l+$"
    "All lower-case (Ll) code-points; only assigned when using *case tags*."
    MIXEDCASED = 0b01100001 #  97 b"^l[Ul]+^" AND "U"
    """Both lower- and upper-case code-points, starting with lower-case; only
    assigned when using *case tags*."""
    UPPERCASED = 0b10000001 # 129 b"^U+^"
    "All upper-case (Lu) code-points; only assigned when using *case tags*."
    CAPITALIZED = 0b11000001 # 193 b"^Ul*$"
    """First letter upper-case, rest lower-case; only assigned when using *case
    tags*."""
    CAMELCASED = 0b11100001 # 225 b"^(Ul*){2,}$" AND "l"
    """Both lower- and upper-case code-points, starting with upper-case; only
    assigned when using *case tags*."""

    # SPECIALIZED ALPHANUMERIC TOKENS (token is joined post-tokenization)
    # consist of LETTERS & DIGITS & NUMERAL chars
    ALNUM_LOWER = 0b01000011 #  67, "^l[Ul1N]+$"
    "Letters, digits, and numerals, starting with a lower-case letter."
    ALNUM_UPPER = 0b10000011 # 131, "^U[Ul1N]+$"
    "Letters, digits, and numerals, starting with an upper-case letter."
    ALNUM_DIGIT = 0b11000011 # 195, "^1[Ul1N]+$"
    "Letters, digits, and numerals, starting with a digit."
    ALNUM_NUMERAL = 0b11001011 # 203, "^N[Ul1N]+$"
    "Letters, digits, and numerals, starting with a numeral."
    ALNUM_OTHER = 0b11100011 # 227, "^L[L1N]+$"
    "Letters, digits, and numerals, starting with a any other."

    # Mapping of the (modified) Unicode categories to a Tag, except STOP
    _TAG_MAP = {
        Category.Cc: CONTROL,
        Category.Cf: MARK,
        Category.Cn: BAD, # has no known characters assigned
        Category.Co: BAD, # private use only characters
        Category.Cs: BAD, # only for lone (=bad) surrogate range characters
        Category.LC: BAD, # has no known characters assigned
        Category.Ll: LETTERS,
        Category.Lg: LETTERS,
        Category.Lm: LETTERS,
        Category.Lo: LETTERS,
        Category.Lt: LETTERS,
        Category.Lu: LETTERS,
        Category.LG: LETTERS,
        Category.Mc: MARK,
        Category.Me: MARK,
        Category.Mn: MARK,
        Category.Nd: DIGITS,
        Category.Nl: NUMERAL,
        Category.No: NUMBER,
        Category.Pc: PUNCT,
        Category.Pd: PUNCT,
        Category.Pe: PUNCT,
        Category.Pf: PUNCT,
        Category.Pi: PUNCT,
        Category.Po: PUNCT,
        Category.Ps: PUNCT,
        Category.Sc: SYMBOL,
        Category.Sk: SYMBOL,
        Category.Sm: SYMBOL,
        Category.So: SYMBOL,
        Category.Ts: STOP,
        Category.Zl: BREAKS,
        Category.Zp: BREAKS,
        Category.Zs: SPACES,
    }
    # Will be populated with the attribute names of each tag by _setNames()
    _TAG_NAMES = {}

    @classmethod
    def forCategory(cls, category:int) -> int:
        """
        Return the tag for the *category* value.

        :raises: KeyError If that *category* does not exist.
        """
        return cls._TAG_MAP[category]

    @classmethod
    def isAlnum(cls, tag:int) -> bool:
        """
        Return ``True`` if the tag is one of the tags that give rise to
        alphanumeric tokens
        """
        return tag in (cls.LETTERS, cls.DIGITS, cls.NUMERAL, cls.ALPHANUMERIC)

    @classmethod
    def isNumber(cls, tag:int) -> bool:
        """
        A test to check if a *tag* represents a number; return ``True``
        if the *tag* is DIGITS or NUMERAL.
        """
        return tag in (cls.DIGITS, cls.NUMERAL)

    @classmethod
    def isMultichar(cls, tag:int) -> bool:
        """
        Return ``True`` if the tag is one of the tags that give rise to
        multi-char tokens
        """
        return tag in (Tag.LETTERS, Tag.DIGITS, Tag.SPACES, Tag.BREAKS,
                       Tag.ALPHANUMERIC)

    @classmethod
    def isWord(cls, tag:int) -> bool:
        """
        A test to check if a *tag* represents a "word"; return ``True``
        if the *tag* is one of the specialized case-tokens or the tags LETTERS
        or ALPHANUMERIC.
        """
        return tag == cls.LETTERS or\
               tag == cls.ALPHANUMERIC or\
               tag > cls._WORDS

    @classmethod
    def isSeparator(cls, tag:int) -> bool:
        """
        A test to check if a *tag* is SPACES or BREAKS (Categories Z?).
        """
        return tag in (cls.SPACES, cls.BREAKS)

    @classmethod
    def toStr(cls, tag:int) -> str:
        """
        Return the string representation for that *tag*.
        """
        if not cls._TAG_NAMES: cls._setNames()
        return cls._TAG_NAMES[tag]

    @classmethod
    def _setNames(cls):
        for name in cls.__dict__:
            if not name.startswith("_"):
                val = getattr(cls, name)

                if type(val) == int:
                    cls._TAG_NAMES[val] = name


def CasetagLetters(cats:bytearray) -> int:
    """
    Return a new tag for LETTERS tokens if they do not start with the Lo
    Unicode category (Letter other). All these tags have an integer value
    that is > 64 (0x40).

    * LOWERCASED (lower)
    * UPPERCASED (UPPER)
    * CAMELCASED (CamlCase)
    * MIXEDCASED (mIxEd cAse) Note: first char must be lower-case!
    * CAPITALIZED (Capitalized Words)

    If the first character is a modifier letter (Lm), the process is repeated
    with the next character until a non-Lm character is found, or LETTERS is
    returned if no other character is present.

    :raises: RuntimeError If the head category in *cats* is none of the above.
    """
    # Note: it is not possible to use the Category.is...() classmethods,
    # because they expect bytes input, but at this level we are still working
    # with bytearrays containing integers.
    if cats[0] in Category.LOWERCASE_LETTERS:
        if any(cat in cats for cat in Category.UPPERCASE_LETTERS):
            return Tag.MIXEDCASED

        return Tag.LOWERCASED
    elif cats[0] in Category.UPPERCASE_LETTERS:
        if any(cat in cats for cat in Category.LOWERCASE_LETTERS):
            if any(cat in cats[1:] for cat in Category.UPPERCASE_LETTERS):
                return Tag.CAMELCASED

            return Tag.CAPITALIZED

        return Tag.UPPERCASED
    elif cats[0] == Category.Lo:
        return Tag.LETTERS
    elif cats[0] == Category.Lm:
        if len(cats) > 1: return CasetagLetters(cats[1:])
        return Tag.LETTERS
    else:
        raise RuntimeError("no provisions for cats %s" % 
                           cats.decode("ASCII"))


def CasetagAlphanumeric(cats:bytearray) -> int:
    """
    Return a new ALPHANUMERIC tag depending on the code-point category of the
    first character. All these tags have an integer value that is > 64 (ox40).

    * ALNUM_UPPER (Lu, Lt, LG)
    * ALNUM_LOWER (Ll, Lg)
    * ALNUM_DIGIT (Nd)
    * ALNUM_NUMERAL (Nl)
    * ALNUM_OTHER (Lo)

    If the first character is a modifier letter (Lm), the process is repeated
    with the next character until a non-Lm character is found. The category
    LC is not handled (and raises an error).

    :raises: RuntimeError If no matching category can be found.
    """
    c = cats[0]
    if c in Category.UPPERCASE_LETTERS:   return Tag.ALNUM_UPPER
    elif c in Category.LOWERCASE_LETTERS: return Tag.ALNUM_LOWER
    elif c == Category.Nd:                return Tag.ALNUM_DIGIT
    elif c == Category.Nl:                return Tag.ALNUM_NUMERAL
    elif c == Category.Lo:                return Tag.ALNUM_OTHER
    elif c == Category.Lm and len(cats) > 1:
        return CasetagAlphanumeric(cats[1:])
    else:
        raise RuntimeError("no provisions for cats %s" % cats.decode("ASCII"))
