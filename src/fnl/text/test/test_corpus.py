"""
.. py:module:: .corpus_test
   :synopsis: Unit tests for corpus generation.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import os
import pytest

from tempfile import TemporaryFile, NamedTemporaryFile
from unittest.mock import patch, mock_open
from fnl.text.corpus import *


def setup_module():
    pass


def teardown_module():
    pass


# ROOT

root = None


def setup():
    global root
    root = Root()


def teardown():
    global root
    root = None


def test_root():
    assert root.tag == ROOT_TAG
    assert isinstance(root.find(HEAD_TAG), Element)


def test_root_with_title():
    root = Root("sentinel")
    assert root.find(HEAD_TAG).find(TITLE_TAG).text == "sentinel"


def test_root_with_encoding():
    root = Root(encoding="sentinel")
    meta = root.find(HEAD_TAG).find(META_TAG)
    assert meta.get('charset') == "sentinel"


# GET ENCODING

def test_get_encoding():
    assert GetEncoding(Root(encoding="UTF-8")).get_or("sentinel") == "UTF-8"
    assert GetEncoding(root).get_or("sentinel") == "sentinel"


# ADD/GET/REMOVE META

def test_add_get_meta():
    r = AddMeta(root, "sentinel.name", "sentinel.content")
    assert r is root
    m = root.find(HEAD_TAG).find(META_TAG)
    assert m.get('name') == "sentinel.name"
    assert m.get('content') == "sentinel.content"
    assert GetMeta(root, "sentinel.name").get_or(None) == "sentinel.content"


def test_remove_meta():
    AddMeta(root, "sentinel.name", "sentinel.content")
    assert GetMeta(root, "sentinel.name").get_or(None) == "sentinel.content"
    RemoveMeta(root, "sentinel.name")
    assert GetMeta(root, "sentinel.name").get_or(None) is None


def test_duplicate_meta():
    AddMeta(root, "sentinel.name", "sentinel.content")
    assert GetMeta(root, "sentinel.name").get_or("other") == "sentinel.content"
    AddMeta(root, "sentinel.name", "sentinel.content2")
    assert GetMeta(root, "sentinel.name").get_or("other") == "sentinel.content2"
    assert GetMeta(root, "sentinel.missing").get_or("other") == "other"


# META DICT

def test_meta_dict():
    d = {}

    for i in range(3):
        AddMeta(root, 'n' + str(i), 'c' + str(i))
        d['n' + str(i)] = 'c' + str(i)

    assert d == GetMetaDict(root)


# SET CONTENT

def test_set_empty_content():
    e = Element('e')
    assert e is SetContent(e)


def test_set_text_content():
    e = Element('e')
    assert SetContent(e, 'text').find(WRAPPER_TAG).text == 'text'


def test_set_element_content():
    x = Element('x')
    assert SetContent(Element('e'), x).find('x') == x


def test_set_mixed_content():
    c = ['text1', Element('x'), 'text2']
    n = list(SetContent(Element('e'), *c))
    assert n[0].tag == WRAPPER_TAG
    assert n[0].text == 'text1'
    assert n[1].tag == 'x'
    assert n[2].tag == WRAPPER_TAG
    assert n[2].text == 'text2'


def test_set_illegal_content():
    with pytest.raises(TypeError):
        SetContent(Element('e'), 1)


# CORPUS

def test_new_corpus():
    c = Corpus()
    assert isinstance(c, Element)
    assert c.tag == CORPUS_TAG


def test_new_corpus_with_attributes():
    c = Corpus(sentinel="value")
    assert c.get('sentinel') == "value"


# CREATE CORPUS

def test_create_corpus():
    c = CreateCorpus(root)
    assert isinstance(c, Element)
    assert c.tag == CORPUS_TAG


def test_create_corpus_with_attributes():
    c = CreateCorpus(root, url="http://example.com/")
    assert c.get('url') == "http://example.com/"


# ARTICLE

def test_new_article():
    a = Article()
    assert isinstance(a, Element)


def test_new_article_with_content():
    a = Article("text")
    assert "text" == a.find(WRAPPER_TAG).text


def test_new_article_with_attributes():
    a = Article(**{'id': "sentinel.id", 'class': "sentinel.class"})
    assert a.get('id') == "sentinel.id"
    assert a.get('class') == "sentinel.class"


def test_new_article_with_content_and_attributes():
    a = Article("text", id="sentinel")
    assert "text" == a.find(WRAPPER_TAG).text
    assert a.get('id') == "sentinel"


# APPEND ARTICLE


def test_append_article():
    a = AppendArticle(CreateCorpus(root))
    assert isinstance(a, Element)
    assert a.tag == ARTICLE_TAG


def test_append_article_to_non_corpus_element():
    with pytest.raises(TypeError):
        AppendArticle(Element('illegal'))


def test_append_article_with_text():
    a = AppendArticle(CreateCorpus(root), "text")
    assert a.find(WRAPPER_TAG).text == "text"


def test_append_article_with_one_element():
    e = Element("e")
    assert [e] == list(AppendArticle(CreateCorpus(root), e))


def test_append_article_with_several_elements():
    el = [Element("e%i" % (i + 1)) for i in range(5)]
    assert el == list(AppendArticle(CreateCorpus(root), *el))


# ITER ARTICLES

def test_iter_articles():
    a1 = AppendArticle(CreateCorpus(root), "text1")
    a2 = AppendArticle(root, "text2")
    articles = [a1, a2]

    for idx, a in enumerate(IterArticles(root)):
        assert a is articles[idx]


# ITER TEXT

# TODO
# def test_iter_text():
#     a = Article("text1", "text2")
#     for s in IterText(a):
#         print(s)
#     assert False

# (DE-) SERIALIZE

def test_serialize():
    CreateCorpus(root)
    AppendArticle(root, "text")
    assert "missing" == GetEncoding(root).get_or("missing")
    b = b''.join(list(Serialize(root)))
    assert b == b"<html><head><meta charset=UTF-8></head>" \
                b"<body><article><div>text</div></article></body></html>"
    assert "missing" == GetEncoding(root).get_or("missing")


def test_deserialize():
    temp = TemporaryFile()
    temp.write(b"<html><head><meta charset=UTF-8></head>"
               b"<body><article><div>text</div></article></body></html>")
    temp.seek(0)
    root2 = Deserialize(temp)

    for article in IterArticles(root2):
        assert article.find(WRAPPER_TAG).text == "text"

# READ/WRITE CORPUS

EXAMPLE = """
<html>
<head>
    <title>example</title>
    <meta charset="UTF-8">
    <meta name="type" content="example">
</head>
<body>
<article id="first">
    <div class="post">
        <h2 class="title">
            <a href="http://fnl.es/installing-a-full-stack-python-data-analysis-environment-on-osx.html" rel="bookmark" title="Permanent Link to &quot;Installing a full stack Python data analysis environment on OSX&quot;">Installing a full stack Python data analysis environment on OSX</a>
        </h2>
        <p>
            <p><strong>UPDATE</strong>: Installing the Scientific Python stack from &quot;source&quot; has become a lot simpler recently and this tutorial was updated accordingly in November 2013 to use with OSX Mavericks and, in particular, <strong>Python 3</strong>.</p>
            Installing a full-stack scientific data analysis environment on Mac OSX for Python 3 and making sure the correct, underlying Fortran and C libraries are used is (was?) not trivial. Thanks to Apple, parts of the required libraries are already on your box when you install XCode (code-named the &quot;<a class="reference external" href="https://developer.apple.com/library/ios/documentation/Accelerate/Reference/AccelerateFWRef/_index.html">Accelerate</a> Framework&quot;), and the remaining pieces can easily be installed due to the great <a class="reference external" href="http://brew.sh/">Homebrew</a> project. In other words, for the <a class="reference external" href="http://en.wikipedia.org/wiki/Basic_Linear_Algebra_Subprograms">BLAS</a> optimizations this setup will use Apple's pre-installed <a class="reference external" href="https://developer.apple.com/library/ios/documentation/Accelerate/Reference/AccelerateFWRef/_index.html">Accelerate</a> framework and you can choose to add the <a class="reference external" href="http://www.cise.ufl.edu/research/sparse/SuiteSparse/">SuiteSparse</a> and <a class="reference external" href="http://www.fftw.org/">FFTW</a> libraries via Homebrew for some extra speed when factorizing sparse matrices and doing Fourier transforms. This guide will describe how to properly install the following software stack on Mac OSX from their sources and ensuring all the relevant C/Fortran &quot;acceleration&quot; is available:
            <ul class="simple">
                <li><a class="reference external" href="http://www.numpy.org/">NumPy</a></li>
                <li><a class="reference external" href="http://www.scipy.org/scipylib">SciPy</a></li>
                <li><a class="reference external" href="http://matplotlib.org/">matplotlib</a></li>
                <li><a class="reference external" href="http://ipython.org/">IPython</a></li>
            </ul>
            With this stack, it is a breeze to add other cool data analysis tools such as <a class="reference external" href="http://scikit-learn.org/stable">scikit-learn</a>, <a class="reference external" href="http://pandas.pydata.org/">pandas</a>, <a class="reference external" href="http://sympy.org/en/index.html">SymPy</a>, or <a class="reference external" href="http://github.com/pymc-devs/pymc">PyMC</a> in your <a class="reference external" href="http://www.virtualenv.org/">VirtualEnv</a>.
        </p>
    </div>
</article>
</body>
</html>
"""


def test_read_corpus():
    temp = NamedTemporaryFile(delete=False)
    temp.write(EXAMPLE.encode('UTF-8'))
    temp.close()
    c = ReadCorpus(temp.name)
    os.remove(temp.name)
    assert "example" == GetMeta(c, "type").get_or("sentinel")

    for a in IterArticles(c):
        assert a.get('id') == "first"
        assert len(a.find('.//ul')) == 4


def test_write_corpus():
    mock = mock_open()

    with patch('builtins.open', mock, create=True):
        WriteCorpus(root, 'sentinel')

    print(mock.mock_calls)
    mock.assert_called_once_with('sentinel', 'wb')
    inner = mock.return_value.write
    print(inner.mock_calls)
    inner.assert_any_call(b'<html')
    inner.assert_any_call(b'<head')
    inner.assert_any_call(b'<meta')
    inner.assert_called_with(b'</html>')
