"""token module tests"""

from pytest import raises
from fnl.text.token_new import token
from fn.monad import Full, Empty

TAGS = ('norm', 'ortho', 'pos', 'chunk', 'entity')


def CheckAttributes(t, text='txt', ns='ns', offset=(1, 2)):
    """ensure attributes"""
    assert text == t.text
    assert ns == t.ns
    assert offset == t.offset


def CheckTags(t, norm=None, ortho=None, pos=None, chunk=None, entity=None):
    """ensure tags"""
    assert norm == t.norm.get_or(None)
    assert ortho == t.ortho.get_or(None)
    assert pos == t.pos.get_or(None)
    assert chunk == t.chunk.get_or(None)
    assert entity == t.entity.get_or(None)


class TestNewToken():

    """create a token"""

    def test_new(self):
        t = token('txt', 'ns', (1, 2))
        assert isinstance(t, token)
        CheckAttributes(t)
        CheckTags(t)

    def test_new_all_values(self):
        t = token('txt', 'ns', (1, 2), *TAGS)
        CheckAttributes(t)
        CheckTags(t, *TAGS)

    def test_new_most_values(self):
        t = token('txt', 'ns', (1, 2), 'norm', 'ortho')
        CheckAttributes(t)
        CheckTags(t, norm='norm', ortho='ortho')

    def test_new_ignore_excess_values(self):
        tags = TAGS + ('junk',)
        t = token('txt', 'ns', (1, 2), *tags)
        CheckAttributes(t)
        CheckTags(t, *TAGS)

    def test_new_using_keywords(self):
        t = token('txt', 'ns', (1, 2), norm='norm', entity='entity')
        CheckAttributes(t)
        CheckTags(t, norm='norm', entity='entity')

    def test_new_ignore_unused_keywords(self):
        t = token('txt', 'ns', (1, 2), norm='norm', entity='entity', funny='haha')
        CheckAttributes(t)
        CheckTags(t, norm='norm', entity='entity')

    def test_new_missing_values(self):
        with raises(ValueError):
            token('txt', 'ns')
        with raises(ValueError):
            token('txt')
        with raises(ValueError):
            token('12345678')

    def test_new_bad_values(self):
        with raises(AssertionError):
            token(1, 'ns', (1, 2))
        with raises(AssertionError):
            token('txt', 1, (1, 2))
        with raises(TypeError):
            token('txt', 'ns', 1)
        with raises(ValueError):
            token('txt', 'ns', (1,))
        with raises(ValueError):
            token('txt', 'ns', (1, 2, 3))


class TestCopyToken():

    """copy an existing token"""

    def test_copy(self):
        t = token(token('txt', 'ns', (1, 2)))
        assert isinstance(t, token)
        CheckAttributes(t)
        CheckTags(t)

    def test_copy_tuple(self):
        t = token(('txt', 'ns', (1, 2)) + TAGS)
        CheckAttributes(t)
        CheckTags(t, *TAGS)

    def test_copy_too_short(self):
        with raises(ValueError):
            token(('txt', 'ns', (1, 2), 'norm', 'pos'))

    def test_copy_too_long(self):
        t = token(('txt', 'ns', (1, 2)) + TAGS)
        CheckAttributes(t)
        CheckTags(t, *TAGS)

    def test_copy_bad_values(self):
        opts = (None,) * 5

        with raises(AssertionError):
            token((1, 'ns', (1, 2)) + opts)
        with raises(AssertionError):
            token(('txt', 1, (1, 2)) + opts)
        with raises(TypeError):
            token(('txt', 'ns', 1) + opts)
        with raises(ValueError):
            token(('txt', 'ns', (1,)) + opts)
        with raises(ValueError):
            token(('txt', 'ns', (1, 2, 3)) + opts)


class TestTokenMethods():

    """general test"""

    def test_infered_properties(self):
        t = token('text', 'ns', (1, 3))
        assert 1 == t.begin
        assert 3 == t.end
        assert 'ex' == t.word

    def test_repr(self):
        t = token('txt', 'ns', (1, 2), norm='norm', entity='entity')
        assert "token(ns, 'x', norm='norm', entity='entity')" == repr(t)

    def test_str(self):
        t = token('txt', 'ns', (1, 2), norm='norm', entity='entity')
        assert "ns\t1:2\tnorm\t\\N\t\\N\t\\N\tentity" == str(t)

    def test_str_with_tabs(self):
        t = token('txt', 'n\ts', (1, 2), norm='st\t\tem', entity='en\tti\tty')
        assert "n\\ts\t1:2\tst\\t\\tem\t\\N\t\\N\t\\N\ten\\tti\\tty" == str(t)

    def test_Update(self):
        t1 = token('txt', 'ns', (1, 2), norm='norm', entity='entity')
        assert 'sentinel' == t1.pos.get_or('sentinel')
        t2 = t1.Update(pos='pos')
        assert 'pos' == t2.pos.get_or('sentinel')
        assert 'sentinel' == t1.pos.get_or('sentinel')
        t3 = t2.Update(text='another', namespace='different', offset=(2, 3))
        assert 'another' == t3.text
        assert 'different' == t3.namespace
        assert (2, 3) == t3.offset

    def test_Update_bad_values(self):
        t = token('txt', 'ns', (1, 2), norm='norm', entity='entity')

        with raises(AssertionError):
            t.Update(text=1)
        with raises(AssertionError):
            t.Update(namespace=1)
        with raises(TypeError):
            t.Update(offset=1)
        with raises(ValueError):
            t.Update(offset=(1,))
        with raises(ValueError):
            t.Update(offset=(1, 2, 3))

    def test_IsBegin(self):
        assert token._IsBegin(Full("B-begin"))
        assert not token._IsBegin(Full("I-inside"))
        assert not token._IsBegin(Full("O"))
        assert not token._IsBegin(Empty())

    def test_IsInside(self):
        assert not token._IsInside(Full("B-begin"))
        assert token._IsInside(Full("I-inside"))
        assert not token._IsInside(Full("O"))
        assert not token._IsInside(Empty())

    def test_IsOutside(self):
        assert not token._IsOutside(Full("B-begin"))
        assert not token._IsOutside(Full("I-inside"))
        assert token._IsOutside(Full("O"))
        assert not token._IsOutside(Empty())

    def test_PosIs_methods(self):
        t = token('txt', 'ns', (1, 2), pos='NNS')
        assert t.PosIs('NNS')
        assert not t.PosIs('VBZ')
        assert not t.PosIs(None)
        assert t.PosStartswith('NN')
        assert not t.PosStartswith('VB')

    def test_PosIs_None(self):
        t = token('txt', 'ns', (1, 2))
        assert t.PosIs(None)
        assert not t.PosIs('NNS')
        assert not t.PosStartswith('')

    def test_ChunkIs_methods(self):
        t = token('txt', 'ns', (1, 2), chunk='B-chunk')
        assert t.ChunkIs('chunk')
        assert not t.ChunkIs('other')
        assert t.ChunkIsBegin()
        assert not t.ChunkIsInside()
        assert not t.ChunkIsOutside()

    def test_EntityIs_methods(self):
        t = token('txt', 'ns', (1, 2), entity='I-entity')
        assert t.EntityIs('entity')
        assert not t.EntityIs('other')
        assert not t.EntityIsBegin()
        assert t.EntityIsInside()
        assert not t.EntityIsOutside()
