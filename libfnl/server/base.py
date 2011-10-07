"""
.. py:module:: base.py
   :synopsis: .

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
"""

import libfnl.server.text

if __name__ == '__main__':
    from bottle import run
    run(host='localhost', port=8080, reloader=True)