"""
.. py:module:: libfnl
   :synopsis: The fnl Python library.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

__version__ = (0, 0, 1) # MAJOR, MINOR, RELEASE

def _PyEncoding() -> str:
    from sys import maxunicode
    if maxunicode == 0xFFFF: return 'utf-16'
    elif maxunicode == 0x10FFFF: return 'utf-32'
    else: raise RuntimeError('Python\'s Unicode encoding unknown')

Py_ENCODING = _PyEncoding()
"""
The **real** encoding of "Python Unicode" strings given the build used (and
ignoring the UCS-2 vs. UTF-16 issue).
"""