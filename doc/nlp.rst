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

==================================
text -- Text-Annotation Data Types
==================================

.. automodule:: libfnl.nlp.text

This NLP packages uses offset annotations on text to manage the tagging of text spans. To make this simple, Python's `bytes` and `str` implementations are extended with functions to add, retrieve, and delete annotations on these two data types. In addition, the API provides a method on each type to convert to the other without loosing or mangling the (offsets of) annotations.

Managing text and their annotations can be a hassle if there is no abstraction in the way this is handled. Therefore, this module provides two classes to manage text as abstract documents: one for the binary representation (ie., encoded) and another for the decoded Unicode view of the text. Both data types can be transformed from one to the other, including any (offset-based) annotations (called *tags*) made on the text. Thereby, **byte-offset-based** annotations made in one specific encoding can be transformed to the Unicode view where it is easy to work with them in Python with a **character-based offset**, and then converted back into any desired encoding, all without ever loosing track of the right offsets for the given view. This makes it possible for the user of this API to not have to worry about the encoding- and programming language-dependency of offsets.

The following two classes exist to represent text: :py:class:`.Binary` and :py:class:`.Unicode`, holding a `bytes` or a `str` view of the content, respectively.

A **tag** consists of a *namespace*, a *key* and an *offset*. The namespace and key can be any string, the offset is a [immutable!] tuple of integer values (one, two, or any multiple of two integers for multi-span annotations). Therefore, a few minimum requirements are enforced:

#. All tags consist of a (string) **namespace** and **key**, and have some (integer tuple) **offsets**.
#. A position ``P`` is a tuple of integers, of length 1, 2, or 2\ ``m`` (for any ``m > 1``).
#. The key ``K`` holds a list of offsets where this tag annotated on the text; A single value position annotates an exact point in the text, a two-value position a given span, and a 2\ ``m``\ -value multiple (consecutive, see next) text segments.
#. The ``P`` of length ``n`` annotating text ``T`` must pass the following conditions (where ``len`` is the Python `len` function applied to the text's content), that is each offset in ``P`` must be within the text's boundaries and consecutive:

  *    P\ :sub:`1` >= 0 ∧
  *    P\ :sub:`n` <= len(T) ∧
  *    P\ :sub:`i` < P\ :sub:`j` ∀ i =: {1, ..., n-1}, j =: i + 1

6. By transforming between :class:`.Binary` and :class:`.Unicode`, any illegal offsets (eg., offsets inside a multi-byte character (for `Binary` `bytes`) or inside a surrogate pair (for `Unicode` strings on narrow Python builds) result in UnicodeErrors.

The *tags* attribute of text, in a nutshell, is a dictionary of this form::

    {
        ...
        'some_namespace': {
            ...
            'some_key': [ ... (10, 20), (24), (25, 28, 30, 33), ... ],
            ...
        },
        ...
    }

The text views also provide a **meta-data dictionary** to store any kind of :attr:`.metadata`\ , useful to maintain information otherwise contained in a CouchDB document that is used to store the text (for example, metadata from MEDLINE records). Therefore, ensure this dictionary can be encoded to a JSON string (ie., only use strings as dictionary keys and better not to use tuples, as they are transformed to lists, anyways) -- at least if you plan to store the text objects in a CouchDB. This metadata dictionary will form the basis of the Couch :class:`.Document`, that will use the fields ``tags`` and ``text`` to store the text -- so it is adviseable to not add any metadata keys with those names, either. Finally, two datetime values are set on those `Document`\ s: ``created`` and ``modified``, that would also overwrite any metadata of the same name.

Both text views (`Binary` and `Unicode`) share the same methods for manipulating the tags inherited from their abstract parent :class:`.Annotated`\ :

Annotated
----------------

.. autoclass:: libfnl.nlp.text.Annotated
   :members:

.. py:attribute:: libfnl.nlp.text.Annotated.metadata

    A dictionary to store any number of values. Note it is recommended not to use the keys that coincide with the fields used when casting the text to a Couch document, namely ``text``, ``encoding``, and ``tags``.

Binary
------

.. autoclass:: libfnl.nlp.text.Binary
   :members:

Unicode
-------

Unicode classes can be transformed to :meth:`.Unicode.markup` strings, ie., XML. This transforms tags to elements with "<namespace>:<key>" names, for example producing the rather verbose ``<strtok:alnum>abc123</strtok:alnum>`` from a tag ``('strtok', 'alnum', (0, 6))`` on the text "abc123". A tag with a single offset value is represented as the empty element (``<namespace:key />``).

Multispan-tags are transformed to elements that have an "offsets" attribute added, with a space-separated list of colon-separated offset spans *of* **code-points** (NB: not bytes!) *relative to the text (PCDATA) the element encloses*, such as ``offsets="0:3 7:8 10:20"`` for a tag with offsets ``(50, 53, 57, 58, 60, 70)``. Note that this means (a) that the first span always starts at zero, (b) that there are at least two such spans if this attribute is present, and (c) if using a *narrow build* of Python, **surrogate pairs** in the element's text are correctly measured as single code-points (and not two).

The element nesting of tags with the same start and end value can be influenced by two special attributes on the **class**: :attr:`.Unicode.ns_weights` and :attr:`.Unicode.key_weights`. Both are dictionaries that should hold integer weights of a specific namespace (NS) or key. By default, tags that have the same start and end are just nested in the alphabetical order of their NS, then their keys, and finally sorted by the offset tuple (and very different to :meth:`.Annotated.ordered`). However, this sorting can be influenced by assigning integer values to a NS or key in those two dictionaries. By default, each NS and key has a weight of ``int(sqrt(sys.maxsize))``, and all element with the same start and end offset (no matter if an empty, single- or multi-span tag), is ordered by NS times key weight. In the simplest case, if you set a NS or key weight to 0, it will always be added before all other elements at that position. However, because of the use of multiplication, it is possible to model complex keys and/or namespaces nesting.

The namespaces (but not the keys!) can also be mangled via the **class** attribute :attr:`.Unicode.ns_map`, a dictionary of ``NS: mangled`` strings. For example, the namespaces ``section`` and ``format`` set by the HTML extractor can be replaced with ``html`` by setting ``ns_map['section'] = 'html'`` (and idem for format), producing ``html:<key>`` element names for both namespaces. Furthermore, an entire namespace can be "suppressed" by setting the value to ``None`` or the empty string, producing ``<key>`` (only) element names for that NS.

.. warning::

    Note that if any tags have partial overlaps, this will produce
    markup that is invalid.

.. autoclass:: libfnl.nlp.text.Unicode
   :members:
   :special-members:


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
'meta: content\\n\\nThis is the text\\nof this weird\u00a0document.\\n\\n'
>>> html.section_tags['div']
[(15, 55)]
>>> print(html.string[15:55]) # &nbsp in div is represented as U+00A0
This is the text
of this weird\u00a0document.
>>> list(sorted(html.section_tags.keys()))
['body', 'divb', 'head']
>>> html.format_tags
{'strong': [(27, 31)]}
>>> html.tag_attributes
{}
>>> len(html.string) == html.section_tags['body'][-1][1]
True

.. autoclass:: libfnl.nlp.extract.HtmlExtractor
    :members: feed, reset, close, string, TAG_INDEX, MINOR_CONTENT, CONTENT, INLINE, REPLACE, IGNORE

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

The tokenizers' `tag()` methods automatically tag :class:`.text.Unicode` instances created from some string. The tokenization of Unicode text is based on a logical grouping of Unicode characters via their categories into a tag. A token is either the longest sequence of characters in the input string belonging to the same :py:class:`.Category` group (for letters, digits, numerals, and separators - but depending on the chosen tokenizer), or a single character (for all other groups). For the standard :class:`.WordTokenizer`, tokens are entire strings of characters belonging to the same category in cases where the characters are all one of letters, digits, numerals, and separators (whitespaces incl. tabs, and breaks incl. newlines and paragraph separators); Characters belonging to other categories always result in single code-point tokens. For alphanumeric tokenization (:class:`.AlnumTokenizer`), the letters, digits, and numerals are joined to a single token. Finally, a simple :class:`.Separator` tokenizer is provided to split text between characters in separator categories and all other classes.

In addition to the default Unicode categories, a category :attr:`.Category.Ts` is provided, for "terminal separator", where "Stop characters" such as fullstop, exclamation mark, or question mark are separated from the default `Po` (punctuation other) category. Another "added category" are the greek characters, that have been separated out of the `Ll` and `Lu` group (lowercase and uppercase characters, respectively) into their own `Lg`, `LG` categories. This is of interest due to the fact that in many scientific texts the use of greek letters gives tokens containing them a very special meaning. A few control characters have been moved (linebreaks, tabs, privates), and a few symbols and punctuation marks have been reassigned to their "correct" categories. In addition, a number of characters have been remapped to other categories where the Unicode standard seems wrong, yet in fact are simply unchanged assignments because of backwards compatibility. For example, the Linefeed character is in the control character (`Cc`) group, instead of the line separator (`Zl`) category. Such inconsistencies have been fixed here, at least for the Basic Multilingual Plane (``U+0000`` - ``U+FFFF``).

While tokenizing, the tokenizer adds tags to the :class:`.Unicode` text. Each tag is made with the namespace provided during instantiation of the tokenizer (using :data:`.strtok.NAMESPACE` as default value), the start and end offsets of the token, and a `str` value that encodes the categories encountered in that tag. If surrogate pairs are found inside the token, each such pair (given it is valid, obviously), receives just one category assignment, which is a single ASCII character per category. Therefore, this value can be understood as encoding the **morphology** of the token and can be made use of later on in a variety of ways.

As a sidenote, these tokenizers all tag the entire string, they do not mysteriously drop characters such as whitespaces or any other "black magick".

Here is a straight-forward usage example:

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
