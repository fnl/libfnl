"""
.. py:module:: libfnl
   :synopsis: The fnl Python library.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

__version__ = (0, 0, 1) # MAJOR, MINOR, RELEASE

def _UTF16() -> bool:
    from sys import maxunicode
    if maxunicode == 0xFFFF: return True
    elif maxunicode == 0x10FFFF: return False
    else: raise RuntimeError('Python\'s Unicode encoding unknown')

PyUTF16 = _UTF16()
"""
The **real** encoding of "Python Unicode" strings given the build used (and
ignoring the UCS-2 vs. UTF-16 issue...).
"""