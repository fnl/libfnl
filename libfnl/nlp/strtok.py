# -*- coding: utf-8 -*-
"""
.. py:module:: strtok
   :synopsis: A string tokenizer for any Unicode text.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
"""

from collections import namedtuple
from unicodedata import category

__author__ = "Florian Leitner"
__version__ = "1.0"
__all__ = ('Token', 'Tokenize', 'TokenizeAlphanumeric', 'Separate', 'Tag',
           'Category', 'STOP_CHARS')


Token = namedtuple("Token", "string tag cats")
"""
A named tuple, consisting of the string, tag, and (modified) Unicode
categories of each code-point in the string (thereby at the same time encoding
the "true" character length of the string).

.. py:attribute:: string

   The actual string this token represents, as a `str`.

.. py:attribute:: tag

   The tag value of this token, as an `int` value (or `bool` for
   :py:func:`.Separate`).

.. py:attribute:: cats

   The (modified) Unicode category of each code-point in the string, as
   ASCII-encode-able `bytes`.
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

"Potential" sentence terminals, such as semicolon, colon, or ellipsis, are
left out.
"""

##########################
# TOKENIZATION FUNCTIONS #
##########################

def Separate(string:str) -> iter:
    """
    A simplistic tokenizer that just splits strings on separators (categories
    Z?, white-spaces and breaks); Instead of regular tags, the
    :py:attr:`.Token.tag` value is ``False`` for yielded separator tokens and
    ``True`` otherwise.

    This tokenizer is more powerful than just ``string.split()`` or a RegEx
    tokenizer using ``\s+``, as there are far more separator characters in
    Unicode than either of these two approaches will recognize; And the
    official Unicode Z? categories do not cover all possible separator
    characters.
    """
    tag, cats, start, end = None, None, 0, 0

    for s, e, c, t in CodepointIter(string):
        if Tag.isSeparator(t) == tag:
            end = e
        else:
            if cats: yield Token(string[start:end], not tag, bytes(cats))
            tag, cats, start, end = Tag.isSeparator(t), bytearray(), s, e

        cats.append(c)

    if cats: yield Token(string[start:end], tag, bytes(cats))


def Tokenize(string:str, case_tags:bool=False) -> iter:
    """
    A Unicode character-based tokenizer, yielding :py:class:`.strtok.Token`
    instances from the input *string*.

    All characters give raise to single-char tokens, except for those that are
    tagged LETTERS, DIGITS, SPACES, or BREAKS.
    If *case tags* are used, the LETTERS tag is furthermore divided into the
    possible groups LOWERCASED, UPPERCASED, CAPITALIZED, CAMELCASED,
    MIXEDCASED, or the token stays unaltered tagged as LETTERS.
    """
    tag, cats, start, end = None, None, 0, 0

    for s, e, c, t in CodepointIter(string):
        if YieldNewToken(t, tag):
            if cats:
                if case_tags: tag = RetagCases(tag, cats)
                yield Token(string[start:end], tag, bytes(cats))

            tag, cats, start, end = t, bytearray(), s, e
        else:
            end = e

        cats.append(c)

    if cats:
        if case_tags: tag = RetagCases(tag, cats, case_tags)
        yield Token(string[start:end], tag, bytes(cats))

def TokenizeAlphanumeric(string:str, case_tags:bool=False) -> iter:
    """
    As :py:func:`.Tokenize`, but in addition joins any consecutive sequences
    of LETTERS (L?), DIGITS (Nd), and NUMERAL (Nl) tokens to either an
    ALPHANUMERIC (if *case tags* is ``False``) or one of the ALNUM_* tags.
    """
    tag, cats, start, end = None, None, 0, 0

    for s, e, c, t in CodepointIter(string):
        if YieldNewToken(t, tag):
            if tag is not None:
                if Tag.isAlnum(t) and Tag.isAlnum(tag):
                    end = e
                    tag = Tag.ALPHANUMERIC
                else:
                    if case_tags: tag = RetagCases(tag, cats)
                    yield Token(string[start:end], tag, bytes(cats))
                    tag, cats, start, end = t, bytearray(), s, e
            else:
                tag, cats, start, end = t, bytearray(), s, e
        else:
            end = e

        cats.append(c)

    if cats:
        if case_tags: tag = RetagCases(tag, cats)
        yield Token(string[start:end], tag, bytes(cats))


#####################
# TAGS & CATEGORIES #
#####################

class Category:
    """
    Integer values the of Unicode categories that also map to ASCII
    characters.

    In other words, a Category value is always in the [0..127] range.
    """

    Cs = ord('*')
    "``*`` - surrogate character (encoding error)"
    Cc = ord('^')
    "``^`` - control character (sans separators (Z?) and two Co chars)"
    Cf = ord('%')
    "``%`` - formatting character"
    Cn = ord('?')
    "``?`` - not assigned (no characters in this category)"
    Co = ord('!')
    "``!`` - other, private use"
    LC = ord('C')
    "``C`` - case character (no characters in this category)"
    Lg = ord('g')
    "``g`` - lower-case Greek character"
    LG = ord('G')
    "``G`` - upper-case Greek character"
    Ll = ord('l')
    "``l`` - lower-case character"
    Lm = ord('m')
    "``m`` - character modifier"
    Lo = ord('L')
    "``L`` - letter, other (symbols without a case)"
    Lt = ord('T')
    "``T`` - title-case letter only (Greek and East European glyphs)"
    Lu = ord('U')
    "``U`` - upper-case letter"
    Mc = ord(';')
    "``;`` - combining space mark (East European glyphs, musical symbols)"
    Me = ord(':')
    "``:`` - combining, enclosing mark (Cyrillic number signs, etc.)"
    Mn = ord('~')
    "``~`` - non-spacing, combining mark (accent, tilde, actue, etc.)"
    Nd = ord('1')
    "``1`` - digit number"
    Nl = ord('2')
    "``2`` - letter number (Roman, Greek, etc. - aka. numerals)"
    No = ord('#')
    "``#`` - other number (superscript, symbol-like numbers, etc.)"
    Pc = ord('_')
    "``_`` - connector punctuation"
    Pd = ord('-')
    "``-`` - dash punctuation"
    Pe = ord(')')
    "``)`` - punctuation end (brackets, etc., sans two quotation marks)"
    Pf = ord('>')
    "``>`` - final quotation mark (like ``»``; ``>`` itself is in Sm)"
    Pi = ord("<")
    "``<`` - initial quotation mark (like ``«``; ``<`` itself is in Sm)"
    Po = ord('.')
    """``.`` - other punctuation (!, ?, ., ,, *, ", ', /, :, ;, etc.), i.e.,
    including the sentence :py:data:`.STOP_CHARS`, but sans characters that
    should be in other (@, #, &) or math (%) symbols."""
    Ps = ord('(')
    "``(`` - punctuation start (brackets, etc., sans three quotation marks)"
    Sc = ord('$')
    "``$`` - currency symbol"
    Sk = ord('`')
    "````` - modifier symbol"
    Sm = ord('+')
    "``+`` - math symbol"
    So = ord('|')
    "``|`` - other symbol (``|`` itself is in Sm)"
    Zl = ord('b')
    "``b`` - line separator; breaks"
    Zp = ord('p')
    "``p`` - paragraph separator"
    Zs = ord('s')
    "``s`` - space separator"

    CONTROLS = (Cc, Cf, Cn, Co, Cs)
    LETTERS = (Lu, LG, Lt, Ll, Lg, LC, Lm, Lo)
    UPPERCASE_LETTERS = (Lu, LG, Lt)
    LOWERCASE_LETTERS = (Ll, Lg)
    OTHER_LETTERS = (LC, Lm, Lo)
    NUMERIC = (Nd, Nl, No)
    NUMBERS = (Nd, Nl)
    MARKS = (Cf, Mc, Me, Mn)
    PUNCTUATION = (Pc, Pd, Pe, Pf, Pi, Po, Ps)
    SYMBOLS = (Sc, Sk, Sm, So)
    SEPARATORS = (Zl, Zp, Zs)

    @classmethod
    def isControl(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any control character category (C?).
        """
        return ord(cat) in cls.CONTROLS

    @classmethod
    def isLetter(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any letter category (L?).
        """
        return ord(cat) in cls.LETTERS

    @classmethod
    def isUppercase(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any upper-case letter category
        (LG, Lt, Lu).
        """
        return ord(cat) in cls.UPPERCASE_LETTERS

    @classmethod
    def isLowercase(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any lower-case letter category (Lg, Ll).
        """
        return ord(cat) in cls.LOWERCASE_LETTERS

    @classmethod
    def isOtherLetter(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any non-upper- or -lower-case letter
        (LC, Lm, Lo).
        """
        return ord(cat) in cls.UPPERCASE_LETTERS

    @classmethod
    def isNumeric(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any numeric character category (N?).
        """
        return ord(cat) in cls.NUMERIC

    @classmethod
    def isNumber(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any numeric character category (Nd, Nl).
        """
        return ord(cat) in cls.NUMBERS

    @classmethod
    def isMark(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any mark category (Cf, M?).
        """
        return ord(cat) in cls.MARKS

    @classmethod
    def isPunctuation(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any punctuation category (P?).
        """
        return ord(cat) in cls.PUNCTUATION

    @classmethod
    def isSymbol(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any symbol character category (S?).
        """
        return ord(cat) in cls.SYMBOLS

    @classmethod
    def isSeparator(cls, cat:bytes) -> bool:
        """
        ``True`` if the *cat* byte is any separator category (Z?).
        """
        return ord(cat) in cls.SEPARATORS

    @staticmethod
    def toStr(cats:bytes) -> str:
        """
        Convert one or more category bytes to their one-character string
        representation (i.e., not the Unicode category codes, but the 7bit
        ASCII characters used here).
        """
        return cats.decode('ASCII')


REMAPPED_CHARACTERS = {Category.Cc: {"\n\f\r\u0085\u008D": Category.Zl,
                                     "\t\v": Category.Zs,
                                     "\u0091\u0092": Category.Co}, # Privates
                       Category.Po: {"#&@\uFE5F\uFE60\uFE6B\uFF03\uFF06\uFF20":
                                     Category.So,
                                     "%\u0609\u060A\u066A\u2030"
                                     "\u2031\uFE6A\uFF05":
                                     Category.Sm},
                       # Quotation markers:
                       Category.Ps: {"\u201A\u201E\u301D": Category.Pi},
                       Category.Pe: {"\u301E\u301F": Category.Pf}}
"Remapped Unicode characters: {cat: {chars: cat}}."


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
        Category.Po: PUNCT, # includes STOP (differentiated in GetTagValue)
        Category.Ps: PUNCT,
        Category.Sc: SYMBOL,
        Category.Sk: SYMBOL,
        Category.Sm: SYMBOL,
        Category.So: SYMBOL,
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
        return tag in (Tag.LETTERS, Tag.DIGITS, Tag.SPACES, Tag.BREAKS)

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


###########
# HELPERS #
###########

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
    """
    # Note: it is not possible to use the Category.is...() classmethods,
    # because they expect bytes input, but at this level we are still working
    # with bytearrays containing integers.
    if cats[0] in Category.LOWERCASE_LETTERS:
        if any(cat in cats for cat in Category.UPPERCASE_LETTERS):
            return Tag.MIXEDCASED
        else:
            return Tag.LOWERCASED
    elif cats[0] in Category.UPPERCASE_LETTERS:
        if any(cat in cats for cat in Category.LOWERCASE_LETTERS):
            if any(cat in cats[1:] for cat in Category.UPPERCASE_LETTERS):
                return Tag.CAMELCASED
            else:
                return Tag.CAPITALIZED
        else:
            return Tag.UPPERCASED
    elif cats[0] == Category.Lo:
        return Tag.LETTERS
    elif cats[0] == Category.Lm:
        if len(cats) > 1: return CasetagLetters(cats[1:])
        else:             return Tag.LETTERS
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
    LC is not handled.

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


def CodepointIter(string:str) -> iter:
    """
    Yield start, end (positions), category, and tag (integers) of each Unicode
    code-point in the string.
    """
    pos, strlen = 0, len(string)

    while pos < strlen:
        char = string[pos]
        cat = GetCharCategoryValue(char)
        tag = GetTagValue(char, cat)
        cplen = 1

        if cat == Category.Cs and pos + 1 < strlen:
            try:
                pair = string[pos:pos + 2]
                cat = GetSurrogateCategoryValue(pair)
            except TypeError:
                pass
            else:
                cplen = 2
                tag = GetTagValue(pair, cat)

        yield pos, pos + cplen, cat, tag
        pos += cplen


def GetCharCategoryValue(character:chr) -> int:
    """
    Return the (remapped) category value of a *character* and its *ordinal*.

    :raises: TypeError If the character is neither a single surrogate nor can
                       be mapped by :py:func:`unicodedata.category`
    """
    cat = getattr(Category, category(character))

    if cat in (Category.Ll, Category.Lu) and IsGreek(character):
        if cat == Category.Ll: cat = Category.Lg
        else:                  cat = Category.LG
    elif cat in REMAPPED_CHARACTERS:
        cat = RemapCategory(character, cat)

    return cat


def GetSurrogateCategoryValue(surrogate_pair:str) -> int:
    """
    Return the (remapped) category value of a *surrogate pair* and its
    *ordinal*.

    :raises: TypeError If the surrogate pair cannot be mapped by
                       :py:func:`unicodedata.category`
    """
    cat = getattr(Category, category(surrogate_pair))

    # Not needed, because no Supplementary Plane characters get remapped
    # if cat in REMAPPED_CHARACTERS:
    #     cat = RemapCategory(character, cat)

    return cat

def GetTagValue(character:str, category:int) -> int:
    """
    Return the integer value of a :py:class:`.Tag` given a *character* and
    its (remapped) Unicode *category*.
    """
    if category == Category.Po and character in STOP_CHARS: return Tag.STOP
    else: return Tag.forCategory(category)


def IsGreek(char:chr) -> bool:
    """
    Return ``True`` if the *char* is on the Greek codepages.
    """
    return "\u0370" <= char < "\u03FF" or "\u1F00" <= char < "\u1FFF"


def RemapCategory(char:str, cat:int) -> int:
    for character_group in REMAPPED_CHARACTERS[cat]:
        if char in character_group:
            cat = REMAPPED_CHARACTERS[cat][character_group]
            break

    return cat


def RetagCases(tag:int, cats:bytearray) -> int:
    """
    Return a new tag if *case tags* is ``True``, using CasetagLetters() if
    the *tag* is LETTERS and CasetagAlphanumeric if it is ALPHANUMERIC;
    Otherwise just return the *tag*.
    """
    if   tag == Tag.LETTERS:      tag = CasetagLetters(cats)
    elif tag == Tag.ALPHANUMERIC: tag = CasetagAlphanumeric(cats)
    return tag


def YieldNewToken(next_tag:int, last_tag:int) -> bool:
    """
    Return ``True`` if the tags mismatch or the new tag is neither a word,
    numeric, break, or whitespace.
    """
    return last_tag != next_tag or not Tag.isMultichar(next_tag)
