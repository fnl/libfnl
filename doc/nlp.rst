##################################
nlp -- Natural language processing
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

=========================================
extract -- Text extraction from documents
=========================================

.. automodule:: libfnl.nlp.extract

Extract
-------

Extract the contents of the file at *filename*, assuming the given *encoding* for the file, and returning a :class:`.Binary` text object.

If the file-type contains HTML markup, this markup is preserved as much as possible. A plain-text file simply gets read into `Binary`, but no annotations are made. If the MIME type isn't set and cannot be guessed (from the file's extension), 'text/plain' is assumed automatically. Currently supported MIME-types (ie., file-types) are:

* text/html, application/xhtml (.htm, .html, .xhtml)
* text/plain (.txt) [defaulted if not set and guessing fails]

HTML text is extracted by the :class:`.HtmlExtractor`. The extractor's ``section_tags`` get set as tags in the namespace ``section``, the ``format_tags`` in the namespace ``format``. And the ``tag_attributes`` dictionary gets added as metadata, using the key ``attributes``, and splitting the attribute tags into their namespaces ``section`` and ``format``, as required for `nlp.text` instances.

.. autofunction:: libfnl.nlp.extract.Extract

HtmlExtractor
-------------

Converts HTML files to plain text files as close as possible to the way these files would be shown in a browser without any formatting directives.

.. warning::

    This extractor relies on :mod:`html.parser` and therefore is not especially robust when used on noisy HTML. Therefore, it is recommended you install the lxml_ package wrapping **libxml2** and first clean HTML documents with :func:`lxml.html.clean.clean_html` before feeding the HTML to this extractor.

Any section (ie., a HTML element that would separate a piece of text from another -- not just ``p``, but also things such as ``dl``, ``li``, ``h3``, or ``div``) are separated by one or two line feeds (\\n), any entity (eg., &nbsp) or character reference (eg., &#x0123) is converted to the corresponding character, while any such reference that would be invalid gets replaced by the replacement (U+FFFD) character.

All the elements that can be handled by the extractor are listed in :attr:`.HtmlExtractor.ELEM_INDEX`\ , while those that are :attr:`.HtmlExtractor.IGNORE`\ D are dropped entirely, including any elements or text they might contain.

A few elements follow special replacement procedures -- see :attr:`.HtmlExtractor.REPLACE`\ .

All relevant HTML elements are converted to format (:attr:`.HtmlExtractor.INLINE`) or section (:attr:`.HtmlExtractor.CONTENT`) tags and are annotated on the resulting string with offsets. Inline and content block elements are converted to text tags (as ``{str(<tag name>): [tuple(<offsets>), ...]}`` dictinaries), available from the attributes ``format_tags`` and ``section_tags``, respectively, **after** the HTMLs extracted :attr:`.HtmlExtractor.string` has been fetched the first time. Most of the attributes are preserved, too, in a separate dictionary ``tag_attributes``, set as an attribute on the extractor instance after fetching the :attr:`.HtmlExtractor.string` -- see :class:`.HtmlExtractor.Tag`\ .

The parser should be initialized, then the HTML :meth:`.feed` sent to it, which has to be :meth:`.HtmlExtractor.close`\ d if has been fed in several rounds. Now, the :attr:`.HtmlExtractor.string` of the extracted content can be fetched, whence the two tag dictionaries will become available as :attr:`.HtmlExtractor.format_tags` and :attr:`.HtmlExtractor.section_tags`. To reuse the same instance, call :meth:`.HtmlExtractor.reset` before feeding new content. An example:

>>> from libfnl.nlp.extract import HtmlExtractor
>>> html = HtmlExtractor()
>>> html.feed('''<html>
...   <head>
...     <meta name="meta" content="content">
...    </head>
...    <body>
...      <div id="div" class="a b">
... This is the <b>text</b><br/> of this weird&nbsp;document.<object/>
...      </div>
...    </body>
... </html>''')
>>> html.close()
>>> html.string
'meta: content\n\nThis is the text\nof this weird\xa0document.\n\n'
>>> print(html.string[15:55]) # &nbsp; in div is represented as U+00A0
This is the text
of this weird\xa0document.
>>> list(sorted(html.tags))
[('html', 'body', (15, 57)), ('html', 'div', (15, 55)), ('html', 'head', (0, 13)), ('html', 'meta', (0, 13)), ('html', 'strong', (27, 31))]
>>> len(html.string)
57

.. autoclass:: libfnl.nlp.extract.HtmlExtractor
    :members: feed, reset, close, string, ELEM_INDEX, MINOR_CONTENT, CONTENT, INLINE, REPLACE, IGNORE

.. py:class:: libfnl.nlp.extract.HtmlExtractor.Tag

    Text annotation tag keys are simply the elements' name.

    The element attributes are preserved in ``tag_attributes``. This is a dictionary of the form::

        {   '<tag name>': { '(<start>, <end>)': <attributes> } }

     Note that the **representation** (ie., a string) of the offsets tuple is used as dictionary key, not the tuple itself, to ensure it can be serialized to JSON. The attributes dictionary contains most attributes except those listed in :class:`HtmlExtractor.SKIPPED_ATTRIBUTES` as well as ``alt`` and ``title``, which are integrated into the extracted text. The ``href`` values get joined as absolute URLs **if** an absolute URL is supplied to the :meth:`.feed` call **or** the document has a *base* element in the header with an absolute ``href`` URL attribute.

    Should it happen that a tag with the same name has the exact same offset as another, eg., ``<div id=1><div id=2>bla</div></div>``, only the attributes on the inner element (here, ``#2``) are preserved.

    In addition, if set, the ``title`` values get appended as ``(<title>)`` -- incl. the parenthesis -- to the end of the **text** (ie., not the ``tag_attributes``\ !) content of that element, and ``alt`` values relplace ``img`` and ``area`` tags. Furthermore, if the ``alt`` value maps extactly to the latin written form of a greek letter (alpha, beta, gamma, ...), the actual greek letter is used, upper-cased if the written form is capitalized, and lower-cased otherwise.

    For general information on text annotation and tags, see :mod:`libfnl.nlp.text`.

.. _lxml: http://lxml.de

=============================
strtok -- String Tokenization
=============================

.. automodule:: libfnl.nlp.strtok

The tokenizers' `tag()` methods tag :class:`.Text` instances created from some string. The tokenization of Unicode text is based on the Unicode grouping (categories) of characters into a tag. A token is either the longest sequence of characters in the input string belonging to the same :py:class:`.Category` group (for letters, digits, numerals, and separators - but depending on the chosen tokenizer), or a single character (for all other groups). For the standard :class:`.WordTokenizer`, tokens are entire strings of characters belonging to the same category in cases where the characters are all one of letters, digits, numerals, and separators (whitespaces incl. tabs, and breaks incl. newlines and paragraph separators); Characters belonging to other categories always result in single code-point tokens. For alphanumeric tokenization (:class:`.AlnumTokenizer`), the letters, digits, and numerals are joined to a single token. Finally, a simple :class:`.Separator` tokenizer is provided to split text between characters in separator categories and all other classes.

In addition to the default Unicode categories, a category :attr:`.Category.Ts` is provided, for "terminal separator", where "Stop characters" such as fullstop, exclamation mark, or question mark are separated from the default `Po` (punctuation other) category. Another "added category" are the greek characters, that have been separated out of the `Ll` and `Lu` group (lowercase and uppercase characters, respectively) into their own `Lg`, `LG` categories. This is of interest due to the fact that in many scientific texts the use of greek letters gives tokens containing them a very special meaning. A few control characters have been moved (linebreaks, tabs, privates), and a few symbols and punctuation marks have been reassigned to their "correct" categories. In addition, a number of characters have been remapped to other categories where the Unicode standard seems wrong, yet in fact are simply unchanged assignments because of backwards compatibility. For example, the Linefeed character is in the control character (`Cc`) group, instead of the line separator (`Zl`) category. Such inconsistencies have been fixed here, at least for the Basic Multilingual Plane (``U+0000`` - ``U+FFFF``).

While tokenizing, the tokenizer adds tags to the :class:`.Text`. Each tag is made with the namespace provided during instantiation of the tokenizer (using :data:`.strtok.NAMESPACE` as default value), the start and end offsets of the token, and a `str` attribute that encodes the categories of that token tag. Therefore, this attribute can be understood as encoding the **morphology** of the token.

As can be understood from this description, the tokenizers tag the entire string, they do not mysteriously manipulate the underlying string, drop characters such as whitespaces, or any other "black magick".

Here is a straight-forward usage example:

>>> from libfnl.nlp.text import Text
>>> from libfnl.nlp.strtok import WordTokenizer, NAMESPACE
>>> text = Text("A simple example sentence.")
>>> tok = WordTokenizer()
>>> tok.tag(text)
>>> for tag, attrs in text.get(NAMESPACE):
...     print(tag[2], tag[1], attrs['morphology'])
...
(0, 1) letter A
(1, 2) space M
(2, 8) letter DDDDDD
(8, 9) space M
(9, 16) letter DDDDDDD
(16, 17) space M
(17, 25) letter DDDDDDDD
(25, 26) glyph o

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
