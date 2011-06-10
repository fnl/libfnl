##################################
nlp -- Natural Language Processing
##################################

.. automodule:: libfnl.nlp

=================================
doc -- Text-Annotation Data Types
=================================

.. automodule:: libfnl.nlp.text

This NLP packages uses offset annotations on text to manage the tagging of text spans. To make this simple, Python's `bytes` and `str` implementations are extended with functions to add, retrieve, and delete annotations on these two data types. In addition, the API provides a method on each type to convert to the other without loosing or mangling the (offset) annotations.

Managing documents and their annotations can be a hassle if there is no abstraction in the way this is handled. Therefore, this module provides two classes to manage text documents: one for the binary representation (encoded) and another for the decoded Unicode view of the text. Both data types can be transformed from one to the other, including any annotations (called **tags**) made on the text. Thereby, offset-based annotations made in one specific encoding can even be easily transformed to the Unicode view where it is easy to work with them in Python, and even back into a completely different encoding, all without ever loosing track of the right offsets for the given view. This makes it possible for the user of this API to not have to worry about either offsets or encoding. Furthermore, a few minimum requirements for tags on the text are enforced:

#. All tags are identified by their (string) **namespace** and **key**, and have some (string) **value**.
#. Only one tag and, hence, value for each namespace and key may exist.
#. A key ``K`` is a tuple of integers, of length 1, 2, or 2\ ``m`` (for any ``m > 1``).
#. The key encodes the offsets this tag annotates; A single value key annotates an exact position in the text, a two-value key a given span, and a 2m-value key a multiple (consecutive) text segments.
#. The key ``K`` of length ``n`` annotating text ``T`` must pass the following conditions (where ``len`` is the Python `len` function applied to the text's content):

  *    K\ :sub:`1` >= 0 ∧
  *    K\ :sub:`n` <= len(T) ∧
  *    K\ :sub:`i` < K\ :sub:`j` ∀ i =: {1, ..., n-1}, j =: i + 1

6. By transforming between binary and Unicode, any illegal offsets result in UnicodeErrors.

For example, if an offset value in a key points between to surrogate characters or into the byte-sequence that forms a character in the encoded binary version. The following two classes exist to represent text: :py:class:`.Binary` and :py:class:`.Unicode`, holding a `bytes` or a `str` view of the content, respectively.

However, both views share the same methods for manipulating the tags annotated on the text; the following properties and methods are shared by both views through an abstract base class:

.. autoclass:: libfnl.nlp.text.AnnotatedContent
   :members: addTag, delTag, getTags, getValue, iterNamespaces, iterTags, tags

.. autoclass:: libfnl.nlp.text.Binary
   :members:

.. autoclass:: libfnl.nlp.text.Unicode
   :members:


=============================
strtok -- String Tokenization
=============================

.. automodule:: libfnl.nlp.strtok

The tokenization functions return generators for :py:class:`.strtok.Token` instances created from the input string. The tokenization of Unicode text is based on a logical grouping of Unicode characters by their categories into a tag. Tokens can be entire strings of characters belonging to the same category in cases where the characters are all one of letters, digits, whitespaces (incl. tabs), or breaks (incl. newlines and paragraph breaks); Characters belonging to other categories always result in single code-point tokens. The only exception is for alphanumeric tokenization, where numerals (normally treated as single code-point tokens) are joined to letters and digits. Therefore, each Token has one :py:class:`.Tag` and each code-point in the Token has a :py:class:`.Category`.

Tags are supersets of categories, with the exception of :py:attr:`.Tag.STOP`, with is a subset of :py:attr:`.Category.Po`, and is only assigned to code-points that represent sentence stop glyphs in some of the more common languages of the world. The categories are those found in Unicode, but with minor fixes for a few bad category assignments found in the official Unicode category mapping. Regarding "fixed categories", most notably, greek characters have been separated out of the Ll and Lu categories (lowercase, uppercase characters, respectively) into their own Lg, LG categories. This is of interest due to the fact that in many scientific texts the use of greek letters gives tokens containing them a very special meaning. A few control characters have been moved (linebreaks, tabs, privates), and a few symbols and punctuation marks have been reassigned to their "correct" categories.

A token is either the longest sequence of characters in the input string belonging to the same :py:class:`.Tag` group (for letters, digits, numerals, breaks, and whitespaces), or a single character thereof (all others). A :py:attr:`.Token.tag` is a representation of the token's Unicode categories as a single integer value. The categories of all code-points in the token are represented by a bytes object (:py:attr:`.Token.cats`, in ASCII encoding), but these categories are modifications to the official Unicode groupings. The `Token.cats` is a bytes object encoding the various character categories found in the token (all mapping to the same tag) that can be represented as an ASCII string or an integer array and has the same length as the string itself has code-points. Therefore, the tag (integer) and the cats (bytes object) attributes of a Token together form a perfect feature vector for any supervised training or can even be used by manual rule-sets. Here is the Token for the string "exAmpLe", when tokenizing with *case tags*::

        Token(string="exAmpLe", tag=Tag.MIXEDCASE, cats=b"llUllUl")

When the *case tags* flag is set, tokens containing letters (as well as digits and numerals for alphanumeric tokenization) get the correct case tag (CAMELCASED, CAPITALIZED, LOWERCASED, MIXEDCASED, UPPERCASED, as well as ALNUM\_{DIGIT, LOWER, NUMERAL, OTHER, UPPER} for alphanumeric tokens) assigned. As a sidenote, this tokenizer reproduces the entire string, it does not mysteriously drop characters such as whitespaces or any other "black magick".

.. autofunction:: libfnl.nlp.strtok.Tokenize

.. autofunction:: libfnl.nlp.strtok.TokenizeAlphanumeric

.. autofunction:: libfnl.nlp.strtok.Separate

.. autoclass:: libfnl.nlp.strtok.Token

.. autoclass:: libfnl.nlp.strtok.Tag
   :members:

.. autoclass:: libfnl.nlp.strtok.Category
   :members:

.. autodata:: libfnl.nlp.strtok.STOP_CHARS
