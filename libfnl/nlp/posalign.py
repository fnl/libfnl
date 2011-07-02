"""
.. py:module:: posalign
   :synopsis: Align a Penn PoS-tagged/-tokenized corpus to strtok tokens.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from collections import namedtuple
from libfnl.nlp.strtok import Tag

PosToken = namedtuple("PosToken", "start end tag")

SPACER = "_"

def AlignPosTags(str_tokens:str, pos_tokens:str) -> PosToken:
    """"""
    tok = next(str_tokens)
    pos = next(pos_tokens)

    while True:
        if tok.start == pos.start:
            if tok.end == pos.end:
                yield tok, pos.tag
                pos = next(pos_tokens)
            elif tok.end < pos.end:
                yield tok, pos.tag
            else:
                raise ValueError("== token longer than PoS: {} - {}".format(tok, pos))

            tok = next(str_tokens)
        elif tok.start > pos.start:
            if tok.end == pos.end:
                yield tok, pos.tag
                pos = next(pos_tokens)
            elif tok.end < pos.end:
                yield tok, pos.tag
            else:
                raise ValueError("> token longer than PoS: {} - {}".format(tok, pos))

            tok = next(str_tokens)
        elif tok.start < pos.start:
            if tok.end <= pos.start:
                if Tag.isSeparator(tok.tag):
                    yield tok, SPACER
                    tok = next(str_tokens)
                else:
                    raise ValueError("no PoS for token {}".format(tok))
            else:
                raise ValueError("token w/o PoS growing into PoS: {} - {}".format(tok, pos))