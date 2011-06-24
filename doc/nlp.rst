##################################
nlp -- Natural Language Processing
##################################

.. automodule:: libfnl.nlp

The NLP packages only have been tested with the 32bit version of Python
3000 (i.e., the narrow build using UTF-16 for [Unicode] strings); They might
work with 64bit (wide build, UTF-32) as well [#f1]_ . To check the build of
your Python distribution, enter an interpreter session and type::

    >>> import sys
    >>> sys.maxsize
    2147483647

If the result is the above number (hex value 0x7FFFFFFF), you have a narrow
build. If it is ``9223372036854775807`` instead (hex value 0x7FFFFFFFFFFFFFFF),
you are running a wide build [#f2]_.

.. [#f1] UCS-2 and -4 are nearly equal to UTF-16 and -32. As a matter of fact,
         Python uses UTF-16, and not UCS-2, as often claimed. The difference
         is that UCS-2 has no surrogate range to compose Supplementary Plane
         characters, while UTF-16 does. As Python makes use of the surrogate
         range, it is UTF-16 based, not UCS-2.

.. [#f2] Using wide builds is only recommended if the majority of characters
         you are processing are found in the Unicode Supplementary Planes. In
         all other cases it is significantly more efficient to use narrow
         builds (because UTF-16 strings will only consume half the memory
         UTF-32/UCS-4 encoded strings would when no Supplementary Plane
         characters are involved).

=================================
doc -- Text-Annotation Data Types
=================================

.. automodule:: libfnl.nlp.text

This NLP packages uses offset annotations on text to manage the tagging of text spans. To make this simple, Python's `bytes` and `str` implementations are extended with functions to add, retrieve, and delete annotations on these two data types. In addition, the API provides a method on each type to convert to the other without loosing or mangling the (offsets of) annotations.

Managing documents and their annotations can be a hassle if there is no abstraction in the way this is handled. Therefore, this module provides two classes to manage text documents: one for the binary representation (encoded) and another for the decoded Unicode view of the text. Both data types can be transformed from one to the other, including any annotations (called **tags**) made on the text. Thereby, offset-based annotations made in one specific encoding can be transformed to the Unicode view where it is easy to work with them in Python, and then back into a completely different encoding, all without ever loosing track of the right offsets for the given view. This makes it possible for the user of this API to not have to worry about offsets or encoding. Furthermore, a few minimum requirements for tags on the text are enforced:

#. All tags consist of a (string) **namespace** and **key**, and have some (integer tuple) **offset**.
#. A position ``P`` is a tuple of integers, of length 1, 2, or 2\ ``m`` (for any ``m > 1``).
#. The key ``K`` holds a list of offsets where this tag annotated on the text; A single value position annotates an exact point in the text, a two-value position a given span, and a 2\ ``m``\ -value multiple (consecutive, see next) text segments.
#. The ``P`` of length ``n`` annotating text ``T`` must pass the following conditions (where ``len`` is the Python `len` function applied to the text's content), that is each offset in ``P`` must be within the text's boundaries and consecutive:

  *    P\ :sub:`1` >= 0 ∧
  *    P\ :sub:`n` <= len(T) ∧
  *    P\ :sub:`i` < P\ :sub:`j` ∀ i =: {1, ..., n-1}, j =: i + 1

6. By transforming between binary and Unicode, any illegal offsets (eg., offsets inside a multi-byte character (for bytes) or inside a surrogate pair (for strings and narrow Python builds) result in UnicodeErrors.

For example, if an offset value of a key points between two surrogate characters or into the byte-sequence that forms a character in the encoded binary version, this would be considered an illegal offset value and raises a :py:exc:`UnicodeError`. The following two classes exist to represent text: :py:class:`.Binary` and :py:class:`.Unicode`, holding a `bytes` or a `str` view of the content, respectively.

However, both views share the same methods for manipulating the tags annotated on the text; the following properties and methods are shared by both views through an abstract base class:

AnnotatedContent
----------------

.. autoclass:: libfnl.nlp.text.AnnotatedContent
   :members: addTag, delTag, getTags, getValue, iterNamespaces, iterTags, tags

Binary
------

.. autoclass:: libfnl.nlp.text.Binary
   :members:

Unicode
-------

.. autoclass:: libfnl.nlp.text.Unicode
   :members:


======================================
medline -- Handling of MEDLINE records
======================================

.. automodule:: libfnl.nlp.medline

.. autodata:: libfnl.nlp.medline.EUTILS_URL

.. autodata:: libfnl.nlp.medline.SKIPPED_ELEMENTS

FetchMedlineXml
---------------

.. autofunction:: libfnl.nlp.medline.FetchMedlineXml

ParseMedlineXml
---------------

.. autofunction:: libfnl.nlp.medline.ParseMedlineXml

=============================
strtok -- String Tokenization
=============================

.. automodule:: libfnl.nlp.strtok

The tokenizers' `tag()` methods automatically tag :class:`.text.Unicode` instances created from some string. The tokenization of Unicode text is based on a logical grouping of Unicode characters via their categories into a tag. A token is either the longest sequence of characters in the input string belonging to the same :py:class:`.Category` group (for letters, digits, numerals, and separators - but depending on the chosen tokenizer), or a single character (for all other groups). For the standard :class:`.WordTokenizer`, tokens are entire strings of characters belonging to the same category in cases where the characters are all one of letters, digits, numerals, and separators (whitespaces incl. tabs, and breaks incl. newlines and paragraph separators); Characters belonging to other categories always result in single code-point tokens. For alphanumeric tokenization (:class:`.AlnumTokenizer`), the letters, digits, and numerals are joined to a single token. Finally, a simple :class:`.Separator` tokenizer is provided to split text between characters in separator categories and all other classes.

In addition to the default Unicode categories, a category :attr:`.Category.Ts` is provided, for "terminal separator", where "Stop characters" such as fullstop, exclamation mark, or question mark are separated from the default `Po` (punctuation other) category. Another "added category" are the greek characters, that have been separated out of the `Ll` and `Lu` group (lowercase and uppercase characters, respectively) into their own `Lg`, `LG` categories. This is of interest due to the fact that in many scientific texts the use of greek letters gives tokens containing them a very special meaning. A few control characters have been moved (linebreaks, tabs, privates), and a few symbols and punctuation marks have been reassigned to their "correct" categories. In addition, a number of characters have been remapped to other categories where the Unicode standard seems wrong, yet in fact are simply unchanged assignments because of backwards compatibility. For example, the Linefeed character is in the control character (`Cc`) group, instead of the line separator (`Zl`) category. Such inconsistencies have been fixed here, at least for the Basic Multilingual Plane (``U+0000`` - ``U+FFFF``).

While tokenizing, the tokenizer adds tags to the :class:`.Unicode` text. Each tag is made with the namespace provided during instantiation of the tokenizer (using :data:`.strtok.NAMESPACE` as default value), the start and end offsets of the token, and a `str` value that encodes the categories encountered in that tag. If surrogate pairs are found inside the token, each such pair (given it is valid, obviously), receives just one category assignment, which is a single ASCII character per category. Therefore, this value can be understood as encoding the **morphology** of the token and can be made use of later on in a variety of ways.

As a sidenote, these tokenizers all tag the entire string, they do not mysteriously drop characters such as whitespaces or any other "black magick".

Here is a straight-forward usage example::

    >>> from libfnl.nlp.text import Unicode
    >>> from libfnl.nlp.strtok import WordTokenizer, NAMESPACE
    >>> text = Unicode("A simple example sentence.")
    >>> tok = WordTokenizer()
    >>> tok.tag(text)
    >>> for offset, value in text.iterTags(NAMESPACE):
    ...     print(offset, value, sep='\t')
    ...
    (0, 1)	A
    (1, 2)	M
    (2, 8)	DDDDDD
    (8, 9)	M
    (9, 16)	DDDDDDD
    (16, 17)	M
    (17, 25)	DDDDDDDD
    (25, 26)	o

.. autodata:: libfnl.nlp.strtok.NAMESPACE

.. autodata:: libfnl.nlp.strtok.STOP_CHARS

Tokenizer
---------

.. autoclass:: libfnl.nlp.strtok.Tokenizer
    :members:

AlnumTokenizer
--------------

.. autoclass:: libfnl.nlp.strtok.AlnumTokenizer

WordTokenizer
-------------

.. autoclass:: libfnl.nlp.strtok.WordTokenizer

Separator
---------

.. autoclass:: libfnl.nlp.strtok.Separator

Category
--------

.. autoclass:: libfnl.nlp.strtok.Category
   :members:
