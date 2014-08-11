"""segment module tests"""

from pytest import raises
from fnl.text.segment import segment


def CheckAttributes(s, text='txt', ns='ns', offset=(1, 2)):
    """ensure attributes"""
    assert text == s.text
    assert ns == s.ns
    assert offset == s.offset


def CheckMeta(s, identifier=None, annotations=None):
    """ensure tags"""
    assert identifier == s.identifier.get_or(None)
    assert annotations == s.annotations.get_or(None)


class TestNewSegment():

    """creating a segment"""

    def test_new(self):
        s = segment('txt', 'ns', (1, 2))
        assert isinstance(s, segment)
        CheckAttributes(s)
        CheckMeta(s)

    def test_new_all_values(self):
        s = segment('txt', 'ns', (1, 2), 'id', 'ann')
        CheckAttributes(s)
        CheckMeta(s, 'id', 'ann')

    def test_new_most_values(self):
        s = segment('txt', 'ns', (1, 2), 'id')
        CheckAttributes(s)
        CheckMeta(s, 'id')

    def test_new_ignore_excess_values(self):
        s = segment('txt', 'ns', (1, 2), 'id', 'ann', 'junk')
        CheckAttributes(s)
        CheckMeta(s, 'id', 'ann')

    def test_new_using_keywords(self):
        t = segment('txt', 'ns', (1, 2), identifier='id')
        CheckAttributes(t)
        CheckMeta(t, 'id')

    def test_new_ignore_unused_keywords(self):
        t = segment('txt', 'ns', (1, 2), annotations='ann', funny='haha')
        CheckAttributes(t)
        CheckMeta(t, annotations='ann')

    def test_new_missing_values(self):
        with raises(ValueError):
            segment('txt', 'ns')
        with raises(ValueError):
            segment('txt')
        with raises(ValueError):
            segment('12345')

    def test_new_bad_values(self):
        with raises(AssertionError):
            segment(1, 'ns', (1, 2))
        with raises(AssertionError):
            segment('txt', 1, (1, 2))
        with raises(TypeError):
            segment('txt', 'ns', 1)
        with raises(ValueError):
            segment('txt', 'ns', (1, 2, 3))

    def test_alternative_offsets(self):
        segment('txt', 'ns', (1,))
        segment('txt', 'ns', (1, 2, 3, 4))


class TestCopySegment():

    def test_copy(self):
        s = segment(segment('txt', 'ns', (1, 2), 'id', 'ann'))
        assert isinstance(s, segment)
        CheckAttributes(s)
        CheckMeta(s, 'id', 'ann')

    def test_copy_list(self):
        s = segment(['txt', 'ns', (1, 2), 'id', None])
        CheckAttributes(s)
        CheckMeta(s, 'id')

    def test_copy_too_short(self):
        with raises(ValueError):
            segment(('txt', 'ns', (1, 2), 'id'))

    def test_copy_too_long(self):
        t = segment(('txt', 'ns', (1, 2), 'id', 'ann', 'junk'))
        CheckAttributes(t)
        CheckMeta(t, 'id', 'ann')

    def test_new_from_generator(self):
        def gen():
            for i in ('txt', 'ns', (1, 2), 'id', None):
                yield i

        s = segment(gen())
        assert s.offset == (1, 2)


class TestSegmentMethods:

    """segment methods"""

    def test_infered_properties(self):
        s = segment('text', 'ns', (1, 3))
        assert 1 == s.begin
        assert 3 == s.end
    
    def test_repr(self):
        s = segment('txt', 'ns', (1, 2), identifier='UID')
        assert "segment(ns, 1:2, identifier='UID')" == repr(s)

    def test_str(self):
        s = segment('txt', 'ns', (1, 2), annotations='TODO')
        assert "ns\t1:2\t\\N\tTODO" == str(s)

    def test_str_with_tabs(self):
        s = segment('txt', 'n\ts', (1, 2), identifier='st\t\tem')
        assert "n\\ts\t1:2\tst\\t\\tem\t\\N" == str(s)

    def test_Update(self):
        s1 = segment('txt', 'ns', (1, 2), identifier='id')
        assert 'id' == s1.identifier.get_or('sentinel')
        s2 = s1.Update(identifier='other')
        assert 'other' == s2.identifier.get_or('sentinel')
        s3 = s2.Update(text='another', namespace='different', offset=(2, 3))
        assert 'another' == s3.text
        assert 'different' == s3.namespace
        assert (2, 3) == s3.offset

    def test_Update_bad_values(self):
        t = segment('txt', 'ns', (1, 2), identifier='id')

        with raises(AssertionError):
            t.Update(text=1)
        with raises(AssertionError):
            t.Update(namespace=1)
        with raises(TypeError):
            t.Update(offset=1)
        with raises(ValueError):
            t.Update(offset=(1, 2, 3))
