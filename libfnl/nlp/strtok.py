"""
.. py:module:: strtok
   :synopsis: A string tokenizer for any Unicode text.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from io import StringIO
from libfnl.nlp.text import Text
from types import FunctionType
from unicodedata import category

__author__ = "Florian Leitner"
__version__ = "1.0"

#################
# CONFIGURATION #
#################

NAMESPACE = "strtok"
"""
The default namespace for the tags added to a text by the tokenizers.
"""

STOP_CHARS = frozenset({
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
})
"""
An assembly of the more specific sentence stop markers found in Unicode in
one of the following languages: Latin, Arabic, Chinese, Japanese, Korean,
Greek, Devanagari, Syriac, Hebrew, Armenian, Tibetan, Myanmar, Ethiopic.
These characters are assigned the :attr:`.Category.Ts`.

Potential sentence terminals, such as semicolon, colon, or ellipsis, are
not included.
"""


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
    """``i`` - other punctuation (,, \*, ", ', /, :, ;, etc.), but
    excluding the sentence :data:`.STOP_CHARS` that are in :attr:`.Ts`, and
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

    CONTROLS = frozenset({ Cc, Cf, Cn, Co, Cs })
    WORD = frozenset({ Lu, Ll, LG, Lg, Lt, LC, Lm, Lo, Nd, Nl, Zl, Zp, Zs })
    ALNUM = frozenset({ Lu, Ll, Nd, Nl, LG, Lg, Lt, LC, Lm, Lo })
    LETTERS = frozenset({ Lu, LG, Lt, Ll, Lg, LC, Lm, Lo })
    UPPERCASE_LETTERS = frozenset({ Lu, LG, Lt })
    LOWERCASE_LETTERS = frozenset({ Ll, Lg })
    OTHER_LETTERS = frozenset({ LC, Lm, Lo })
    NUMBERS = frozenset({ Nd, Nl, No })
    NUMERIC = frozenset({ Nd, Nl })
    MARKS = frozenset({ Mc, Me, Mn })
    PUNCTUATION = frozenset({ Pc, Pd, Pe, Pf, Pi, Po, Ps, Ts })
    SYMBOLS = frozenset({ Sc, Sk, Sm, So })
    SEPARATORS = frozenset({ Zl, Zp, Zs })
    BREAKS = frozenset({ Zl, Zp, })

    @classmethod
    def control(cls, cat:int) -> bool:
        """``True`` if the *cat* is any control character category (C?)."""
        #return cat in cls.CONTROLS
        return 90 < cat < 97

    @classmethod
    def word(cls, cat:int) -> bool:
        """``True`` if the *cat* is any letter, digit, numeral, or separator."""
        # category (L?, Nd, Nl, Z?).
        #return cat in cls.WORD
        return cat < 78

    @classmethod
    def alnum(cls, cat:int) -> bool:
        """``True`` if the *cat* is any letter, digit, or numeral category"""
        # (L?, Nd, Nl).
        #return cat in cls.ALNUM
        return cat < 75

    @classmethod
    def letter(cls, cat:int) -> bool:
        """``True`` if the *cat* is any letter category (L?)."""
        #return cat in cls.LETTERS
        return cat < 73

    @classmethod
    def uppercase(cls, cat:int) -> bool:
        """``True`` if the *cat* is any upper-case letter category."""
        # (LG, Lt, Lu).
        return cat in cls.UPPERCASE_LETTERS

    @classmethod
    def lowercase(cls, cat:int) -> bool:
        """``True`` if the *cat* is any lower-case letter category (Lg, Ll)."""
        return cat in cls.LOWERCASE_LETTERS

    @classmethod
    def other_letter(cls, cat:int) -> bool:
        """``True`` if the *cat* is any non-upper- or -lower-case letter."""
        # (LC, Lm, Lo).
        return cat in cls.OTHER_LETTERS

    @classmethod
    def number(cls, cat:int) -> bool:
        """``True`` if the *cat* is any number category (N?)."""
        return cat in cls.NUMBERS

    @classmethod
    def numeric(cls, cat:int) -> bool:
        """``True`` if the *cat* is any numeric value (Nd, Nl)."""
        return cat in cls.NUMERIC

    @classmethod
    def digit(cls, cat:int) -> bool:
        """``True`` if the *cat* is digit (Nd)."""
        return cat == Category.Nd

    @classmethod
    def numeral(cls, cat:int) -> bool:
        """``True`` if the *cat* is numeral (Nl)."""
        return cat == Category.Nl

    @classmethod
    def mark(cls, cat:int) -> bool:
        """``True`` if the *cat* is any mark category (M?)."""
        return cat in cls.MARKS

    @classmethod
    def punctuation(cls, cat:int) -> bool:
        """``True`` if the *cat* is any punctuation category (P?)."""
        return cat in cls.PUNCTUATION

    @classmethod
    def symbol(cls, cat:int) -> bool:
        """``True`` if the *cat* is any symbol character category (S?)."""
        return cat in cls.SYMBOLS

    @classmethod
    def separator(cls, cat:int) -> bool:
        """``True`` if the *cat* is any separator category (Z?)."""
        return cat in cls.SEPARATORS

    @classmethod
    def breaker(cls, cat:int) -> bool:
        """``True`` if the *cat* is any breaker separator category (Zl, Zp)."""
        return cat in cls.BREAKS

    @classmethod
    def space(cls, cat:int) -> bool:
        """``True`` if the *cat* is a space (Zs)."""
        return cat == Category.Zs

    @classmethod
    def not_separator(cls, cat:int) -> bool:
        """``True`` if the *cat* is not any separator category (Z?)."""
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
Mapping of Unicode category names to Category attributes.
"""

REMAPPED_CHARACTERS = {
    # NOTE: Lt, Lu and Ll can not be remapped
    # (see GetCharCategoryValue and GREEK_REMAPPED)
    Category.Cc: {
        "\n": Category.Zl,
        "\f": Category.Zl,
        "\r": Category.Zl,
        "\u0085": Category.Zl, # NEXT LINE (is in \s of regexes)
        # "\u008D": Category.Zl, # REVERSE LINE FEED (isn't in \s of regexes!)
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


##################
# IMPLEMENTATION #
##################

class Tokenizer:
    """
    Abstract tokenizer implementing the actual procedure.
    """

    def __init__(self, namespace:str=NAMESPACE):
        """
        The *namespace* is the namespace string used for the tags created on
        the text.
        """
        self.namespace = namespace

    def tag(self, text:Text, morphology:str="morphology") -> dict:
        """
        Tokenize the given *text* by adding tags the defined
        :attr:`.namespace` with *morphology* attributes for each tag.

        :param text: The :class:`.Text` to tag.
        :param morphology: The key used in the attribute dictionaries for the
            morphology strings.
        """
        text.add(self.tags(text, morphology), self.namespace)

    def tags(self, text:Text, morphology:str):
        """
        Yield tokens for the given *text* in the defined
        :attr:`.namespace` with *morphology* attributes for each tag.

        :param text: The :class:`.Text` to tag.
        :param morphology: The key used in the attribute dictionaries for the
            morphology strings.
        :return: An iterator of (tag, attributes) tuples, where tag is a tuple
            of namespace, ID, offsets and attributes is a dictionary.
        """
        cats = None
        last_cat = None
        start = 0
        State = lambda c: False

        for end, cat in enumerate(CategoryIter(text)):
            if State(cat):
                if not cats:
                    cats = StringIO()
                    cats.write(last_cat)

                cats.write(chr(cat))
            else:
                if end:
                    tag = (NAMESPACE, State.__name__, (start, end))
                    last_cat = cats.getvalue() if cats else last_cat
                    yield tag, {morphology: last_cat}

                cats = None
                last_cat = chr(cat)
                start = end
                State = self._findState(cat)

        if cats or last_cat:
            tag = (NAMESPACE, State.__name__, (start, len(text.string)))
            last_cat = cats.getvalue() if cats else last_cat
            yield tag, {morphology: last_cat}

    @staticmethod
    def _findState(cat:int) -> FunctionType:
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
    A tokenizer that only separates `Z?` category characters (line- and
    paragraph-breaks, as well as spaces) from all others.

    Produces the following tag IDs:

        * not_separator (all others)+
        * separator (Z?)+
    """

    @staticmethod
    def _findState(cat:int) -> FunctionType:
        if Category.separator(cat):
            return Category.separator
        else:
            return Category.not_separator


class WordTokenizer(Tokenizer):
    """
    A tokenizer that creates single character tokens for all non-letter,
    -digit, -numeral, and -separator character, while it joins the others
    as long as the next character is of that same category, too.

    Produces the following tag IDs:

        * breaker (Zl, Zp)+
        * digit (Nd)+
        * glyph (all others){1}
        * letter (L?)+
        * numeral (Nl)+
        * space (Zs)+
    """

    @staticmethod
    def glyph(_) -> bool:
        return False

    @staticmethod
    def _findState(cat:int) -> FunctionType:
        if not Category.word(cat):
            return WordTokenizer.glyph

        for State in (Category.letter, Category.space, Category.digit,
                      Category.breaker, Category.numeral):
            if State(cat): return State

        raise RuntimeError("no State for cat='%s'" % chr(cat))


class AlnumTokenizer(Tokenizer):
    """
    A tokenizer that creates single character tokens for all non-separator
    and -alphanumeric characters, and joins the latter two as long as the
    next character is of that same category, too.

    Produces the following tag IDs:

        * alnum (L?, Nl, Nd)+
        * breaker (Zl, Zp)+
        * glyph (all others){1}
        * space (Zs)+
    """

    @staticmethod
    def _findState(cat:int) -> FunctionType:
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


def CategoryIter(text:Text) -> iter:
    """
    Yields category integers for a *text*, one per (real - wrt. Surrogate
    Pairs) character in the *text*.
    """
    for char in text.string:
        yield GetCharCategoryValue(char)

def GetCharCategoryValue(character:chr) -> int:
    """
    Return the (remapped) Unicode category value of a *character*.

    :raises: TypeError If the *character* can not be mapped by
                       :func:`unicodedata.category`
    """
    cat = CATEGORY_MAP[category(character)]

    if cat in GREEK_REMAPPED:
        if IsGreek(character):
            if cat == Category.Ll: return Category.Lg
            else:                  return Category.LG
    elif cat in REMAPPED_CHARACTERS and character in REMAPPED_CHARACTERS[cat]:
        cat = REMAPPED_CHARACTERS[cat][character]

    return cat


def IsGreek(char:chr) -> bool:
    """
    Return ``True`` if the *char* is on one of the Greek code-pages.
    """
    return "\u036F" < char < "\u1FFF" and not ("\u03FF" < char < "\u1F00")


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
