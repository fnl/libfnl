##################################
nlp -- Natural Language Processing
##################################

.. automodule:: libfnl.nlp

=============================
strtok -- String Tokenization
=============================

.. automodule:: libfnl.nlp.strtok

The tokenization functions return generators for :py:class:`.strtok.Token` instances created from the input string. The tokenization of Unicode text is based on a logical grouping of Unicode characters by their categories into a tag. Tokens can be entire strings of characters belonging to the same category in cases where the characters are all one of letters, digits, whitespaces (incl. tabs), or breaks (incl. newlines and paragraph breaks); Characters belonging to other categories always result in single code-point tokens. The only exception is for alphanumeric tokenization, where numerals (normally treated as single code-point tokens) are joined to letters and digits. Therefore, each Token has one :py:class:`.Tag` and each code-point in the Token has a :py:class:`.Category`.

Tags are supersets of categories, with the exception of :py:attr:`.Tag.STOP`, with is a subset of :py:attr:`.Category.Po`, and is only assigned to code-points that represent sentence stop glyphs in some of the more common languages of the world. The categories are those found in Unicode, but with minor fixes for a few bad category assignments found in the official Unicode category mapping. Regarding "fixed categories", most notably, greek characters have been separated out of the Ll and Lu categories (lowercase, uppercase characters, respectively) into their own Lg, LG categories. This is of interest due to the fact that in many scientific texts the use of greek letters gives tokens containing them a very special meaning. A few control characters have been moved (linebreaks, tabs, privates), and a few symbols and punctuation marks have been reassigned to their "correct" categories.

A token is either the longest sequence of characters in the input string belonging to the same :py:class:`.Tag` group (for letters, digits, numerals, breaks, and whitespaces), or a single character thereof (all others). A :py:attr:`.Token.tag` is a representation of the token's Unicode categories as a single integer value. The categories of all code-points in the token are represented by a bytes object (:py:attr:`.Token.cats`, in ASCII encoding), but these categories are modifications to the official Unicode groupings. The `Token.cats` is a bytes object encoding the various character categories found in the token (all mapping to the same tag) that can be represented as an ASCII string or an integer array and has the same length as the string itself has code-points. Therefore, the tag (integer) and the cats (bytes object) attributes of a Token together form a perfect feature vector for any supervised training or can even be used by manual rule-sets. Here is the Token for the string "exAmpLe", when tokenizing with *case tags*::

        Token(string="exAmpLe", tag=Tag.MIXEDCASE, cats=b"llUllUl")

When the *case tags* flag is set, tokens containing letters (as well as digits and numerals for alphanumeric tokenization) get the correct case tag (CAMELCASED, CAPITALIZED, LOWERCASED, MIXEDCASED, UPPERCASED, as well as ALNUM_{DIGIT, LOWER, NUMERAL, OTHER, UPPER} for alphanumeric tokens) assigned. As a sidenote, this tokenizer reproduces the entire string, it does not mysteriously drop characters such as whitespaces or any other "black magick".

.. autofunction:: libfnl.nlp.strtok.Tokenize

.. autofunction:: libfnl.nlp.strtok.TokenizeAlphanumeric

.. autofunction:: libfnl.nlp.strtok.Separate

.. autoclass:: libfnl.nlp.strtok.Token

.. autoclass:: libfnl.nlp.strtok.Tag
   :members:

.. autoclass:: libfnl.nlp.strtok.Category
   :members:

.. autodata:: libfnl.nlp.strtok.STOP_CHARS
