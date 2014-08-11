"""text module tests"""
from fnl.text.text_new import text
from fnl.text.segment import segment
from fnl.text.token_new import token
from unittest.mock import patch, sentinel


class TestNewText:

    """text contructor test"""

    def test_init(self):
        t = text("hello world", ("uid",))
        assert isinstance(t, str)
        assert isinstance(t, text)
        assert "hello world" == t
        assert ("uid",) == t.uid
        assert None == t._digest

    @patch('fnl.text.token_new.token', spec=token)
    @patch('fnl.text.segment.segment', spec=segment)
    def test_make_with_segments_and_tokens(self, segmentMock, tokenMock):
        tokenMock.return_value.namespace = 'tok'
        segmentMock.return_value.namespace = 'seg'
        tok = tokenMock()
        seg = segmentMock()
        t = text("hello world", tokens=tok, segments=[seg])
        assert {'seg': [seg]} == t._segments
        assert {'tok': [tok]} == t._tokens

    @patch('fnl.text.token_new.token', spec=token)
    @patch('fnl.text.segment.segment', spec=segment)
    def test_copy(self, segmentMock, tokenMock):
        tokenMock.return_value.namespace = 'tok'
        segmentMock.return_value.namespace = 'seg'
        tokenMock.return_value.Update.return_value = sentinel.token_update
        segmentMock.return_value.Update.return_value = sentinel.segment_update
        tok = tokenMock()
        seg = segmentMock()
        t1 = text("hello world", tokens=tok, segments=seg)
        t2 = text(t1)
        assert t1 is not t2
        assert {'seg': [sentinel.segment_update]} == t2._segments
        assert {'tok': [sentinel.token_update]} == t2._tokens

class TestAddingTags:

    """adding segments and tokens"""

    class mockTag(int):
        namespace = 'ns'

    def test_add_segments_by_insort(self):
        s3 = TestAddingTags.mockTag(3)
        t = text('txt', segments=[s3])
        segs = [TestAddingTags.mockTag(i) for i in range(4, 1, -2)]
        t.AddSegments(segs)
        assert {'ns': [2, 3, 4]} == t._segments

    def test_add_tokens_by_collecting(self):
        t = text('txt')
        toks = [TestAddingTags.mockTag(i) for i in range(5, 0, -1)]
        t.AddTokens(toks)
        assert {'ns': [1, 2, 3, 4, 5]} == t._tokens

