################################
nlp.text -- Text Annotation Type
################################

Introduction
============

.. automodule:: libfnl.nlp.text

The NLP package annotates text using tags consisting of a **namespace**, an **ID** and character-based **offsets**. To make this simple, a special :class:`.Text` type has been added with methods to create, retrieve, and delete annotations (aka. tags) on strings. In addition, the :class:`.Text` API provides methods to (de-) serialize the objects to (from) JSON [XML is coming, when/if needed...].

Managing text and their annotations can be a hassle if there is no abstraction in the way this is handled. Therefore, this module provides a class to manage strings as "annotate-able" text data, while not having to worry about encoding or byte-offsets, whether using a narrow or wide Python build (where strings are based on UTF-16 or UTF-32 encoding, respectively), or even the offset-order of annotations, as Red-Black Trees are used to maintain the order of tags at the offset level.

A :class:`.Text.Tag` consists of three attributes: *namespace*, *id* and some *offsets*. Tags are hashable (tuples) and must conform to these requirements:

#. All tags consist of a (string) **namespace** (``ns``) and **ID** (``id``), and have some (integer tuple) **offsets** (``offsets``).
#. An offsets tuple is a list of integers, of length 1, 2, or 2\ ``m`` (for any ``m > 1``).
#. A single value offset annotates an exact point in the text, a two-value position an exact span, and a 2\ ``m``\ -value multiple (consecutive, see next point) text segments.
#. The offset tuple of length ``n`` annotating text ``T`` must pass the following conditions (where ``len`` is the Python `len` function applied to the text's content), that is each position ``P`` in the offsets tuple must be within the text's boundaries and consecutive:

  *    P\ :sub:`1` >= 0 ∧
  *    P\ :sub:`n` <= len(T) ∧
  *    P\ :sub:`i` < P\ :sub:`j` ∀ i =: {1, ..., n-1}, j =: i + 1

As tags are hashable, each tag is also **unique** -- meaning, for a given namespace, ID, and offsets only one tag can exist per text. The :class:`.Text` also provides an :attr:`.Text.attributes` dictionary to store any kind of metadata for a given tag by using the (therefore, hashable) tag as key. Each tag thereby can have a dictionary of attributes to add additional metadata to a tag, such as provenance or confidence values of a tag. To ensure each attribute dictionary can be serialized to JSON or XML, it is recommended that you do not use anything else than strings for both attribute names (keys) and values.

Working with Text
=================

Creating and comparing text objects
-----------------------------------

The simplest way to create a new `Text` object is to instantiate it using a string.

.. doctest::

    >>> from libfnl.nlp.text import Text
    >>> text = Text('example')

In addition to the plain text, an iterable of pre-defined annotations can form part of the instantiation.

.. doctest::

    >>> tag = ('penn', 'NN', (10, 13))
    >>> text = Text('The brown fox jumped over the green frog.', [tag])

In this case, we annotated "fox" with the Penn PoS tag for noun. If the exact same tag appears multiple times, it still is only annotated once -- so, as a matter of fact, the above list is actually treated as a `set`. Finally, each tag (which is unique on the entire `Text`) can have :attr:`.Text.attributes` attached to it, for example to add all kinds of meta-data, track the provenance of the tag, etc..

.. doctest::

    >>> attrs = {'annotator': 'fleitner@cnio.es'}
    >>> text = Text('The brown fox jumped over the green frog.', {tag: attrs})

Note that now, instead of providing the tags as a list, they are given as the dictionary of tags with their attributes. If you wish to add attributes for some tags, but not all, it is recommended to set the value of the tag-attribute dictionary for those values to ``None`` instead of an (empty) dictionary.

The constructor can also be used to make a "nearly-deep" copy of a Text object: all but the values of the tag attribute dictionaries are deep-copied. (So as long as you only use strings such as ``fleitner@cnio.es`` shown above, or any other immutable types, this is probably never an issue).

.. doctest::

    >>> text2 = Text(text)
    >>> text2 == text
    True
    >>> text
    <Text ...@D08DGf5gcyJ8jB1ycY2lHQ>
    >>> text2
    <Text ...@D08DGf5gcyJ8jB1ycY2lHQ>

The last example also shows the effect of the comparison operator ``==``: if both texts have the same underlying string and the same set of tags -- *but not necessarily the same attributes* -- the comparison evaluates to ``True``. If you want to be sure two objects are absolutely the same instances pointing to the same memory, use the ``is`` operator.

The representation of text objects ("``<Text [ID]@[checksum]>``") shows the ID of the objects and the Base64-encoded byte-checksum of the underlying string separated by an ``@`` symbol.

Technical details on creating :class:`.Text` objects are found in the API docs of the class below.

Adding, getting, and removing annotations
-----------------------------------------

`Text` objects are subscriptable sequence objects, just as lists, tuples, strings, or even dictionaries. The subscript type is integer. However, instead of accessing the characters of the underlying string at a given position (character offset, as a string object would), the :class:`.Text.Tag`\ s at that position(s) is (are) fetched.

.. doctest::

    >>> text[12]
    [('penn', 'NN', (10, 13))]
    >>> text[11:13]
    [('penn', 'NN', (10, 13))]

Contrary to lists and regular slices, the third slice item however is not used to define the step of the slice (as in ``[1, 2, 3][0:3:2]`` to fetch ``[1, 3]``); Instead, it only is important whether the third (step) value can be evaluated to ``True`` or not, and if so, instructs the text object to only return annotations that are **included** in the slice.

.. doctest::

    >>> text[11:13:True]
    []
    >>> text[10:13:True]
    [('penn', 'NN', (10, 13))]

In addition to fetching annotations, subscripts can also be used to quickly make annotations on the text object, by providing the namespace and ID of the tag as a colon-separated string (the ID may contain more colons, but the first is used to split the namespace).

.. doctest::

    >>> text[-5:-1] = 'penn:NN'
    >>> text[-2]
    [('penn', 'NN', (36, 40))]

Just as when creating texts, attributes for the tag may be provided as a second (dictionary) element.

.. doctest::

    >>> text[-5:-1] = 'penn:NN', dict(attrs)

To see all tags and attributes annotated on the text, the text is used as an iterator.

.. doctest::

    >>> list(text)
    [(('penn', 'NN', (10, 13)), {'annotator': 'fleitner@cnio.es'}), (('penn', 'NN', (36, 40)), {'annotator': 'fleitner@cnio.es'})]

This follows a special ordering of tags: Tags are ordered by the lowest offset tags (first value in the tag's *offsets* tuple) first, then the highest offset (last value in a tag's *offsets* tuple).

.. doctest::

    >>> text[10:12] = 'offset:order'
    >>> list(text.tags)
    [('penn', 'NN', (10, 13)), ('offset', 'order', (10, 12)), ('penn', 'NN', (36, 40))]

This example also shows that the :attr:`.tags` attribute only fetches the tag tuples, without the attribute dictionaries (but still in the same order as discussed above). Tags with the same start and stop value (first and last offset value) have no specific sorting mechanism and may appear in any order. However, when traversing the text's annotations in `reversed` order, this does not result in the same order as just reversing the list just generated. In reversed order, the tags are ordered by highest stop and the lowest start (which is semantically different to lowest start and highest stop).

.. doctest::

    >>> [tag for tag, _ in reversed(text)]
    [('penn', 'NN', (36, 40)), ('penn', 'NN', (10, 13)), ('offset', 'order', (10, 12))]
    >>> [tag for tag, _ in reversed(list(text))] # NB: not the same as the above!
    [('penn', 'NN', (36, 40)), ('offset', 'order', (10, 12)), ('penn', 'NN', (10, 13))]

To check if a particular tag is annotated on the text, the `in` keyword can be used, just as with sequences.

.. doctest::

    >>> ('offset', 'order', (10, 12)) in text
    True

Finally, to remove an annotation from the text, the `del` keyword can be used, just as on other sequences, and again the step value of a slice can be used to determine whether all tags covering those offsets (if step is not ``True``) or only those inside the span will be deleted (if step evaluates to ``True``).

.. doctest::

    >>> del text[:12:1]
    >>> list(text.tags)
    [('penn', 'NN', (10, 13)), ('penn', 'NN', (36, 40))]

To bulk :meth:`.add`, :meth:`.Text.get`, or :meth:`.remove` tags see the API documents. In general, if you are adding/removing/getting many tags, those methods might perform better than the single tag operations described so far. Finally, all tags can be accessed by :attr:`.Text.offsets` and as a :attr:`.tagtree`.

Accessing the text's string
---------------------------

To access slices or individual characters of the underlying string of the `Text` object, a special :attr:`.Text.string` property is provided.

.. doctest::

    >>> text.string[10:13]
    'fox'
    >>> text.string[10]
    'f'

However, this attribute is a special implementation to fix offset problems with so-called "Astral characters" on narrow Python builds -- characters with code-points mapping to the Supplementary Multilingual Planes (planes 2-16, U+10000-U+10FFFE). By providing this special `string` attribute, character offsets in strings are guaranteed to be equal no matter which Python build is used (on narrow builds, Astrals would normally result in two-character wide Surrogate Pairs). Therefore, to fetch the entire underlying string, for efficiency, it is recommended to simply cast the `Text` object to a string instead of using the `.string` attribute, which in some cases actually might not be a `str` type at all.

.. doctest::

    >>> str(text)
    'The brown fox jumped over the green frog.'

The length operator returns the length of the underlying string in absolute characters (ie., counting Surrogate Pairs -- if any -- as length 1).

.. doctest::

    >>> len(text)
    41

Text API
========

.. autoclass:: libfnl.nlp.text.Text
   :members:

.. py:attribute:: libfnl.nlp.text.Text.attributes

    A dictionary to store attributes for tags. The keys of this dictionary are the tags. Each set of attributes for a tag should be a dictionary consisting of string keys (attribute names) and (attribute) values. If a tag has no attributes, that tag will not have a key in this dictionary.
