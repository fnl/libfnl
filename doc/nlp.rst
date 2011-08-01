##################################
nlp -- Natural language processing
##################################

.. automodule:: libfnl.nlp

The NLP packages work with both the 32bit version of Python 3000 (i.e., the narrow build using UTF-16 for [Unicode] strings) and 64bit (wide build, UTF-32) as well [#f1]_ . To check the build of your Python distribution, enter an interpreter session and type::

    >>> import sys
    >>> sys.maxunicode
    65535

If the result is the above number (hex value 0xFFFF), you have a narrow build. If it is ``1114111`` instead (hex value 0x10FFFF), you are using a wide build [#f2]_.

.. [#f1] UCS-2 and -4 are nearly equal to UTF-16 and -32. *De facto*, narrow
         Python uses UTF-16, and not UCS-2, as often claimed. The difference
         is that UCS-2 has no Surrogate Range to compose Supplementary Plane
         characters, while UTF-16 does. As Python uses Surrogate Pairs, it
         really is UTF-16 based, not UCS-2.

.. [#f2] Using wide builds is only recommended if characters you are
         processing are frequently found in the Unicode Supplementary Planes.
         In all other cases it is significantly more efficient to use narrow
         builds (because UTF-16 strings will only consume half the memory
         UTF-32/UCS-4 encoded strings would when no Supplementary Plane
         characters are involved).

=========================================
extract -- Text extraction from documents
=========================================

.. automodule:: libfnl.nlp.extract

Extract
-------

Extract the contents of the file at *filename*, assuming the given *encoding* for the file, and returning a :class:`.Text` object.

If the file-type contains HTML markup, this markup is preserved as much as possible. A plain-text file simply gets read into `Text`, but no annotations are made. If the MIME type isn't set and cannot be guessed (from the file's extension), 'text/plain' is assumed automatically. Currently supported MIME-types (ie., file-types) are:

* text/html, application/xhtml (.htm, .html, .xhtml)
* text/plain (.txt) [defaulted if not set and guessing fails]

HTML text is extracted by the :class:`.HtmlExtractor`.

.. autofunction:: libfnl.nlp.extract.Extract

HtmlExtractor
-------------

Converts HTML files to plain text files as close as possible to the way these files would be shown in a browser without any formatting directives.

.. warning::

    This extractor relies on :mod:`html.parser` and therefore is not especially robust when used on noisy HTML. Therefore, it is recommended you install the lxml_ package wrapping **libxml2** and first prune HTML documents with :func:`lxml.html.clean.clean_html` before feeding the HTML to this extractor.

Any section (ie., a HTML element that would separate a piece of text from another -- not just ``p``, but also things such as ``dl``, ``li``, ``h3``, or ``div``) are separated by one or two line feeds (\\n), any entity (eg., &nbsp) or character reference (eg., &#x0123) is converted to the corresponding character, while any such reference that would be invalid gets replaced by the replacement (U+FFFD) character.

All the elements that are officially part of HTML 4 or 5 (even if their use is not recommeded by the W3C) are handled, while any elements that are not part of HTML are dropped entirely, including any elements or CDATA they might contain.

All relevant HTML elements are converted to :attr:`.HtmlExtractor.tags` and are annotated on the resulting string with offsets. Elements that have neither a span size in the extracted text nor any attributes are "dropped" (ie., no tag is created for them).

The parser should be initialized, then the HTML :meth:`.feed` sent to it once or more, then the feed should to be :meth:`.HtmlExtractor.close`\ d. Now, the :attr:`.HtmlExtractor.string` of the extracted content can be fetched, as well as the :attr:`.HtmlExtractor.tags`. To reuse the same instance, call :meth:`.HtmlExtractor.reset` before feeding new content. An example:

>>> from libfnl.nlp.extract import HtmlExtractor
>>> html = HtmlExtractor(namespace='html')
>>> html.feed('''<html>
...   <head>
...     <meta name="meta" content="content">
...     <title>Example</title>
...    </head>
...    <body>
...      <div id="div" class="a b">
... This is the <b> text </b> <br/> of this weird &nbsp; document.<fake/>
...      </div>
...    </body>
... </html>''')
>>> html.close() # IMPORTANT - close feed, clean up rightmost whitespaces
>>> html.string
'Example\n\nThis is the text \nof this weird \xa0document.'
>>> list(sorted(html.tags))
[('html', 'body', (9, 51)), ('html', 'br', (26, 27)), ('html', 'div', (9, 51)), ('html', 'head', (0, 9)), ('html', 'html', (0, 51)), ('html', 'meta', (0,)), ('html', 'strong', (21, 26)), ('html', 'title', (0, 9))]
>>> html.string[9:51] # &nbsp; in div is represented as U+00A0 (\xa0)
'This is the text \nof this weird \xa0document.'
>>> len(html.string)
51
>>> sorted(html.tags[('html', 'meta', (0,))].items())
[('content', 'content'), ('name', 'meta')]
>>> html.reset() # all extracted data is erased and the parser is ready again

If an image (img) or area tag has an "alt" or "title" attribute, instead of using a placeholder character, the alt (preferred) or title (otherwise) value is used and the attribute is deleted from the dictionary. In addition, for image tags with alt values that exactly match to the latin name of a greek letter, the actual greek letter is used instead of the latin name. That greek letter is upper-case if the latin name if written capitalized and lower-case otherwise.

>>> html.feed('''<img alt='alpha' href='some_url'/>''')
>>> html.close()
>>> html.string
'α'
>>> html.tags[(html.namespace, 'img', (0, 1))]
{'href': 'some_url'}

.. autoclass:: libfnl.nlp.extract.HtmlExtractor
    :members: NORMAL_NAME, SKIPPED_ATTRIBUTES, close, feed, reset

.. py:attribute:: libfnl.nlp.extract.HtmlExtractor.tags

    A dictionary of tag tuples: attributes dictionaries.

    Text annotation tag keys are the same as :class:`.Text` tags. The namespace is set during instantiation of the extractor. The IDs are the names of the HTML elements. The offsets are calculated during extraction.

    The attributes are all attributes found on each tag, except for attributes that are removed (see :attr:`.SKIPPED_ATTRIBUTES`).

    Should it happen that a tag with the same name has the exact same offset as another, eg., ``<div id=1 a=x><div id=2 b=y>bla</div></div>``, the attributes dictionary is updated with the attributes from the second, but only one tag is created. In the example, the attribute "id" on the inner element would be overwritten with ``2``, resulting in ``{'id': '2', 'a': 'x', 'b': 'y'}`` only.

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
