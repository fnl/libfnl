"""
.. py:module:: fnl
   :synopsis: A Python text mining library.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

__version__ = '1'


def _UTF16() -> bool:
    from sys import maxunicode

    if maxunicode == 0xFFFF:
        return True
    elif maxunicode == 0x10FFFF:
        return False
    else:
        raise RuntimeError('Python\'s Unicode encoding unknown')


PyUTF16 = _UTF16()
"""
The **real** encoding of "Python Unicode" strings given the build used (and
ignoring the UCS-2 vs. UTF-16 issue...). ``True`` if 2-byte strings are
being used and ``False`` otherwise.
"""
