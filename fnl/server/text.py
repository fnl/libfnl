"""
.. py:module:: text
   :synopsis: .

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
"""

from bottle import abort, post, request
from libfnl.couch.serializer import Decode

@post('/text/tag')
def Tag():
    raw = request.body.read()

    if len(raw) == 0:
        abort(400, 'no request body')

    try:
        json = Decode(raw.decode('utf8'))
    except UnicodeDecodeError:
        abort(400, 'request body not UTF-8')
    except ValueError:
        abort(400, 'request body not JSON')

    if 'text' not in json:
        abort(400, 'JSON object has no text property')

    if not isinstance(json['text'], str):
        abort(400, 'JSON text not a string')


    return "<span pos='0'>a</span><span pos='1'>b</span><span pos='2'>c</span>"

