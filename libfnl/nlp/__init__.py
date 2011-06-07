# -*- coding: utf-8 -*-
"""
.. py:module:: nlp
   :synopsis: Modules for Natural Language Processing.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>

Modules for Natural Language Processing.

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
"""
