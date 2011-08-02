##################################
nlp.text -- A text annotation type
##################################

Introduction
============

.. automodule:: libfnl.nlp.text

The NLP package annotates text using tags consisting of a **namespace**, an **ID** and character-based **offsets**. To make this simple, a special :class:`.Text` type has been added with methods to create, retrieve, and delete annotations (aka. tags) on strings. In addition, the :class:`.Text` API provides methods to (de-) serialize the objects to (from) JSON [XML is coming, when/if needed...].

Managing text and their annotations can be a hassle if there is no abstraction in the way this is handled. Therefore, this module provides a class to manage strings as "annotate-able" text data, while not having to worry about encoding or byte-offsets, whether using a narrow or wide Python build (where strings are based on UTF-16 or UTF-32 encoding, respectively), or even the offset-order of annotations, as Red-Black Trees are used to maintain the order of tags at the offset level.

A **tag** consists of three elements: *namespace*, *ID* and some *offsets*. Tags are (hashable) tuples and must conform to these requirements:

#. All tags consist of a (string) **namespace** and **ID**, and have some (integer tuple) **offsets**, eg., ``('ns', 'id', (4, 7))``.
#. An offsets tuple is a list of integers, of length 1 or 2\ ``m`` (for any ``m > 0``).
#. A single integer offsets tuple annotates an exact point in the text, a two-value offsets a span, and more than two values represent multi-span segments.
#. The offset tuple of length ``n`` annotating text ``T`` must pass the following conditions (where ``len`` is the Python `len` function applied to the text's content), that is each position ``P`` in the offsets tuple must be within the text's boundaries and consecutive:

  *    P\ :sub:`1` >= 0 ∧
  *    P\ :sub:`n` <= len(T) ∧
  *    P\ :sub:`i` < P\ :sub:`j` ∀ i =: {1, ..., n-1}, j =: i + 1

As tags are hashable, each tag is also **unique** -- meaning, for a given namespace, ID, and offsets only one tag may exist per text. The :class:`.Text` also provides an :attr:`.Text.attributes` dictionary of namespaces to store any kind of metadata for a given tag by using the (therefore, hashable) tag as key, eg., ``{ 'ns': { ('ns', 'id', (4, 7)): {'attribute': 'value'} } }`` Each tag thereby can have a dictionary of attributes to add additional metadata to a tag, such as provenance or confidence values of a tag. To ensure each attribute dictionary can be serialized to JSON or XML, it is recommended that to not use anything else than strings for  attribute names (keys) and JSON-serializable values.

Working with Text
=================

Creating and comparing text objects
-----------------------------------

The simplest way to create a new `Text` object is to instantiate it using a string.

.. doctest::

    >>> from libfnl.nlp.text import Text
    >>> text = Text('example')

In addition to the plain text, an iterable of pre-defined tags with their attributes can form part of the instantiation.

.. doctest::

    >>> tag = ('penn', 'NN', (10, 13))
    >>> text = Text('The brown fox jumped over the green frog.', [(tag, None)])

In this case, we annotated "fox" with the Penn PoS tag for noun and explicitly declared the tag has no attributes (``None``). If you wish to add attributes for some, but not all tags, set the second value for tags without attributes to ``None`` or an empty dictionary. Each tag is expected to appear once and only once. If the same tag is added to the text in two distinct operations, it will be treated as an update of the attributes for that tag - but if the same tag exists twice in the list of tags used during initialization or the list used when add()ing tags, this will lead to unpredictable results. In general, this class assumes that the tags and attributes added are well-formed; No special checks are made to ensure malformed data or possibly complete "junk" is added. The order in which tags are added to/initialized with a text is maintained internally if the tags are for a new namespace not yet annotated on the text. If more tags are add()ed for a existing namespace, the list of tags in any "updated" namespace will be re-ordered in increasing offset order at the end of the :meth:`.Text.add` operation. Each tag can have :attr:`.Text.attributes` attached to it, for example to add all kinds of meta-data, track the provenance of the tag, etc..

.. doctest::

    >>> attrs = {'annotator': 'fleitner@cnio.es'}
    >>> text = Text('The brown fox jumped over the green frog.', [(tag, attrs)])

The constructor can also be used to make a "nearly-deep" copy of a Text object: all but any (possibly mutable!) values of the tag attribute dictionaries are deep-copied.

.. doctest::

    >>> text2 = Text(text)
    >>> text2.attributes = {} # "removes" all attributes
    >>> text2 == text
    True
    >>> text
    <Text ...@D08DGf5gcyJ8jB1ycY2lHQ>
    >>> text2
    <Text ...@D08DGf5gcyJ8jB1ycY2lHQ>
    >>> text is text2
    False

The last example also shows the effect of the comparison operator ``==``: if both texts have the same underlying string and the same set of tags -- *but not necessarily the same attributes* -- the comparison evaluates to ``True``. If you want to be sure two objects are absolutely the same instances pointing to the same memory location, use the ``is`` operator.

The representation of text objects ("``<Text [ID]@[checksum]>``") shows the ID of the objects and the Base64-encoded byte-checksum of the underlying string separated by an ``@`` symbol.

Technical details on creating :class:`.Text` objects are found in the API docs of the `Text` class.

Accessing the text's string
---------------------------

To access slices of or iterate over the characters of the underlying string of a `Text` object, a special :attr:`.Text.string` (read-only) property is provided.

.. doctest::

    >>> text.string[10:13]
    'fox'
    >>> text.string[10]
    'f'
    >>> isinstance(text.string, str)
    True

However, this attribute may be a special type to fix offset problems with so-called "Astral characters" on narrow Python builds -- characters with code-points mapping to the Supplementary Multilingual Planes (planes 2-16, U+10000-U+10FFFE). By providing this special `string` attribute, character offsets in strings are guaranteed to be equal no matter which Python build is used (on narrow builds, Astrals would normally result in two-character wide Surrogate Pairs). However, as it behaves just as any other string would, so there is not problem in using it just as you would use any other string.

.. doctest::

    >>> str(text) # directly on text
    'The brown fox jumped over the green frog.'
    >>> str(text.string) # just as good
    'The brown fox jumped over the green frog.'
    >>> [char for char in text.string]
    ['T', 'h', 'e', ' ', 'b', 'r', 'o', 'w', 'n', ' ', 'f', 'o', 'x', ...]

Using the length operator on `string` returns the length of the underlying string in "real" characters (ie., counting Surrogate Pairs -- if any -- as length 1). If you need to get the "real" offsets of narrow builds (ie., counting Surrogate Pairs as length 2), cast it to a string object as shown above.

.. doctest::

    >>> len(text.string)
    41

Adding, getting, and removing annotations
-----------------------------------------

`Text` objects are subscriptable sequence objects, just as lists, tuples, strings, or even dictionaries. The subscript type is integer. However, instead of accessing the characters of the underlying string at a given position (character offset, as a string object would), the **tags** at the given (offset) position(s) are fetched, added, or deleted.

.. doctest::

    >>> text[12]
    [('penn', 'NN', (10, 13))]
    >>> text[12:14]
    [('penn', 'NN', (10, 13))]

Contrary to lists and regular slices, the third slice item however is not used to define the step of the slice (as in ``[1, 2, 3][0:3:2]`` to fetch ``[1, 3]``); Instead, it only is important whether the third (step) value can be evaluated to ``True`` or not, and if so, instructs the text object to only return annotations that are **included** in the slice.

.. doctest::

    >>> text[11:13:True]
    []
    >>> text[10:13:1]
    [('penn', 'NN', (10, 13))]

In addition to fetching annotations, subscripts can also be used to quickly make annotations on the text object, by providing the namespace and ID of the tag.

.. doctest::

    >>> text[-5:-1] = 'penn', 'NN'
    >>> text[-2]
    [('penn', 'NN', (36, 40))]

Just as when creating texts, attributes for the tag may be provided as a third dictionary element.

.. doctest::

    >>> text[-5:-1] = 'penn', 'NN', [('dictionary', 'like')]

To see all tags annotated on the text, the text is used as an iterable; Note that the tags are grouped by namespaces (in no particular order) and the tags for each namespace are in the order they are stored (usually, offset order). Attributes are not returned by the subscript accessors and iterator methods.

.. doctest::

    >>> list(text)
    [('penn', 'NN', (10, 13)), ('penn', 'NN', (36, 40))]

This requires explaining the way the ordering of tags is handled: Tags should be added ordered by the lowest offset tags (first value in the tag's *offsets* tuple) first, then the highest offset (last value in a tag's *offsets* tuple) when adding to the text (see :obj:`.Text.Key`) and each time new tags are added to an existing namespace on the text, all tags in that namespace are (re-) ordered by this key.

.. doctest::

    >>> text[(10, 12)] = 'penn', 'order'
    >>> list(text)
    [('penn', 'NN', (10, 13)), ('penn', 'order', (10, 12)), ('penn', 'NN', (36, 40))]

The above example also shows that tags can be created by directly using the offset tuple instead of slice notation (``10:12`` here), which is useful to create multi-span tags (eg., ``(10, 12, 14, 18)``, which is not possible to represent in slice notation).

Tags with the same start and stop values (first and last offset values) are ordered by their remaining offset values, then the namespace, and finally their IDs. Note that reversed order - sorting by highest stop and then lowest start is semantically different to lowest start and highest stop; see :obj:`.Text.ReverseKey`. Furthermore, ``reversed(text)`` is meaningless and produces the same result as ``iter(text)``; The iteration accessors are just a quick means to iterate over all annotated tags, they are not meant to "provide order". To retrieve a list of **all** tags (ie., not just from one namespace) in offset order, use :meth:`.Text.tags`.

.. doctest::

    >>> # NB: reverse offset order is not the reverse of the list shown above!
    >>> text.tags(Text.ReverseKey)
    [('penn', 'NN', (36, 40)), ('penn', 'NN', (10, 13)), ('penn', 'order', (10, 12))]

To check if a particular tag is annotated on the text, the `in` keyword can be used, just as with sequences.

.. doctest::

    >>> ('penn', 'order', (10, 12)) in text
    True
    >>> ('not', 'there', (10, 12)) in text
    False
    >>> 'not a tag' in text
    False

To count the number of tags annotated on the text, the `len` function is applied to the text.

.. doctest::

    >>> len(text)
    3

Finally, to remove an annotation from the text, the `del` keyword can be used, just as on other sequences, and again the step value of a slice can be used to indicate whether all tags covering those offsets (if step is not ``True``) or only those inside the span should be deleted (if step evaluates to ``True``).

.. doctest::

    >>> del text[:12:1]
    >>> list(text)
    [('penn', 'NN', (10, 13)), ('penn', 'NN', (36, 40))]

To bulk :meth:`.Text.add`, :meth:`.Text.get`, or :meth:`.Text.remove` tags see the API section below. In general, if you are adding/getting/removing more than a single tag for a namespace, those methods will perform significantly better than the subscript operations described so far, but contrary to the code shown so far always work in combination with each tag's attributes. Mostly, the subscript accessors will be useful to fetch or remove all tags at a certain offset/span, and to quickly add a single tag. A tags' attributes can be separately accessed via :attr:`.Text.attributes`.

Text API
========

Text constructor and attributes
-------------------------------

.. autoclass:: libfnl.nlp.text.Text
   :members: Key, ReverseKey, base64digest, digest, utf8, utf16

String access
-------------

.. autoattribute:: libfnl.nlp.text.Text.string

.. automethod:: libfnl.nlp.text.Text.encode

.. automethod:: libfnl.nlp.text.Text.iter

Tag and attribute access
------------------------

.. py:attribute:: Text.attributes

    A dictionary of namespaces holding dictionaries of tags that store each tag's attributes.

    The keys of this dictionary are the namespaces for which tags exist. Each namespace key in turn has another dictionary of tags that hold the attributes (dictionaries). These attribute dictionaries consist of string keys (attribute names) and (attribute) values that should be JSON-encodable. Furthermore, list and dictionary attribute values are updated if an existing tag is added again (see :meth:`.Text.add`). If a tag has no attributes, that tag will not have a key in the namespace dictionary::

        {
            'namespace': {
                ('namespace', 'tag_ID', (10, 20)): { 'attribute': 'value },
                ...
            },
            ...
        }

.. autoattribute:: libfnl.nlp.text.Text.namespaces

.. automethod:: libfnl.nlp.text.Text.add

.. automethod:: libfnl.nlp.text.Text.get

.. automethod:: libfnl.nlp.text.Text.remove

.. automethod:: libfnl.nlp.text.Text.tags

.. automethod:: libfnl.nlp.text.Text.update

Text serialization
------------------

.. automethod:: libfnl.nlp.text.Text.fromJson

.. automethod:: libfnl.nlp.text.Text.toJson

.. automethod:: libfnl.nlp.text.Text.addFromDict

.. automethod:: libfnl.nlp.text.Text.tagsAsDict


JSON Annotations
================

Text and annotations can be saved to any other databases, files, might be provided as a REST web service, or available on some website. Therefore, all text and annotations are exchanged as `JSON`_ objects that follow the same uniform principles to make it easy to communicate them over the Internet (aka. "interoperable"). Two or more text and/or annotation objects form a **collection**. The exact nature of a collection is not defined in this context. A collection might be all objects found at a certain URL (resource), in one or more databases, retrievable from one or more web services/sites, etc.. In essence, a collection is entirely implementation dependent and therefore remains undefined in this context. JSON is specified in `RFC 4627`_ and both text and annotation objects must follow this specification.

Text objects
------------

**Members:** ``text``, ``checksum``, [``_id``].

Text objects are `JSON`_ objects with two required members: ``text`` and ``checksum``, and one optional member ``_id``.

The ``text`` holds a JSON Unicode string of the text itself (see section "2.5. Strings" and "3. Encoding" of `RFC 4627`_ - JSON strings by default are UTF-8, but can be UTF-16 or -32 encoded, too). The ``checksum`` element is a JSON object with at least two values::

    {
        'encoding': '<encoding>',
        '<hash type>': '<hexdigest>'
    }

The ``<encoding>`` value should be the encoding used on the ``text`` string to calculate the checksum as a 7bit ASCII string and must follow the `IANA specification`_ for character set names (Preferentially, the name should be the official encoding name using all lower case characters without dashes, eg., "utf8".) Allowed encodings are only the *UCS Transformation Format encodings* currently supported by the Unicode consortium (as of August 2011, those are UTF-8, -16, and -32). Preferentially, the encoding should be the same encoding as used for the ``text`` string in the JSON object. The ``<hash type>`` should be the hash algorithm used to calculate the checksum. Allowed hash types are **MD5** (preferred), **SHA256**, and **SHA512**, and the string can be written in upper- or lower-case and with or without a dash separating the letters from the digits. For MD5, the strings "md5" (preferred), "MD-5", "mD5", and "Md-5" are all valid keys to indicate a MD5 the hash type. The ``<hexdigest>`` is simply the hexadecimal representation of the binary hash, using two characters per byte. This value string must match the regular expression ``/^[A-Fa-f0-9]+$/`` and it must be twice as long as the number of bytes produced by the chosen hash type. Optionally, two or all three of the valid hash types may be part of the ``checksum`` JSON object. If hashing the encoded (ie., binary) ``text`` string with the specified hash type does not lead to the same ``<hexdigest>`` value, the text object is malformed and the receiver of a malformed text object should reject it.

In addition, a text object may contain an additional key, ``_id``, that provides a unique ID for the text object. The ID must be a Unicode string, but an ID's exact nature remains unspecified. However, it is highly recommended to keep the string as short as possible, 256 characters or less. Objects with IDs longer than 256 characters may be rejected. IDs must be unique with respect to the collection this object pertains to. The ``_id`` is used to identify the text of annotation objects (see below), as annotation objects do not necessarily contain the text they annotate if the collection is a mixed collection of text and annotation objects.

Additional members and data may be added to text objects, as long as they do not collide with the members just described. However, a receiver may decide to drop any other member not described. If a received text object does not match the described specifications, the receiver should reject the text object.

Annotation objects
------------------

**Members**: ``annotator``, ``tags``, ``text_id`` OR (``text`` AND ``checksum``), [``_id``].

Annotation objects are `JSON`_ objects unique to one ``annotator``, with the ``tags`` holding the annotation and *either* a ``text_id`` reference *or* the two required members ``text`` and ``checksum``. Optionally, annotation objects may have an ``_id``.

An ``annotator`` references the entity that made the annotations represented by this object, and the value must be a string. If an automated agent created the annotations, a unique **URL** (and, explicitly **not** any other URI, ie., not a URN) for that agent must be used, preferentially mapping to some meaningful and available Internet resource with respect to the annotation agent. The agent URL syntax must follow the `RFC 1738`_ specifications for URLs, but only the schemes ``http[s]`` (`RFC 2616`_ and `RFC 2818`_ for HTTP over SSL/TLS), ``ftp`` (`RFC 1738`_), and ``mailto`` (`RFC 6068`_) are allowed. In the case of a human annotator, the annotator string must be the unique E-mail address of the annotator, and must follow the `RFC 5322`_ specifications for E-mail addresses (see `section 3.4.1`_). The E-mail address string for human annotators may **not** contain the ``mailto:`` (scheme) prefix, as this would qualify an annotator string as a URL, used to identify automated agents.

The ``tags`` member holds a JSON object of annotations on some text string. The object must follow the structure as already described in :meth:`.Text.tagsAsDict`, namely::

    { '<namespace>': { '<tag_id>': { '<offset>(\.<offset>)*': { '<attr_name>': <attr_value> } } } }

To map entities annotated as tags to real resources, each namespace in ``tags`` might actually be a qualified **URI**, usable to map the namespace to an existing resource, such as a database entry. Preferentially, a namespace combined with a tag's ID creates a valid URL that points to the actual resource of the annotated entity. For example, to annotate UniProt proteins, the namespace might be ``http://www.uniprot.org/uniprot/``, and the IDs would be UniProt accessions, such as ``P12345``. For example, the annotation of the mention of the UniProt protein `P12345`_ - which has the official protein name "mAspAT", found in some text as the string "FABP1" (5 chars) at offsets 187 to 192 (5 chars) - might look like this::

    { 'http://www.uniprot.org/uniprot/': { 'P12345': { '187.192': { 'name': 'mAspAT', 'confidence': 0.8745672 } } } } }

The semantics of attribute values are undefined as they are only meaningful in an implementation dependent manner. Attributes can be used for a large variety of purposes, such as referencing other tags to create relational annotations, containing the annotated text when using separate text and annotation objects, or any relevant values created by automated systems, such as the confidence value for an annotation or the official name of an annotated entity, as shown in the example above. The only limitation for attributes is that they must be `JSON`_-serializable *objects*.

Annotation objects always tag some specific text (string). Either, the text can be part of the annotation object, in which case it is added as two members, ``text`` and ``checksum``, following the same rules as described for text objects. Otherwise, the text can be referenced by the annotation object, by adding a ``text_id`` string. In this case, the actual text object must have an ``_id`` value with exactly that string, and both objects must be part of the same collection.

Just as text objects, annotation objects may contain an ``_id`` value following the same guidelines as for text object IDs.

Additional members and data may be added to annotation objects, as long as their names do not collide with the names just described. However, a receiver may decide to drop any other member not described. If a received annotation object does not match the described specifications, the receiver should reject the annotation object.

.. _IANA specification: http://www.iana.org/assignments/character-sets
.. _JSON: http://json.org/
.. _P12345: http://www.uniprot.org/uniprot/P12345
.. _RFC 1738: http://tools.ietf.org/html/rfc1738
.. _RFC 2616: http://www.rfc-editor.org/rfc/rfc2616.txt
.. _RFC 2818: http://www.rfc-editor.org/rfc/rfc2818.txt
.. _RFC 4627: http://www.ietf.org/rfc/rfc4627.txt
.. _RFC 5322: http://tools.ietf.org/html/rfc5322
.. _RFC 6068: http://www.rfc-editor.org/rfc/rfc6068.txt
.. _section 3.4.1: http://tools.ietf.org/html/rfc5322#section-3.4.1
