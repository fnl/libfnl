"""
.. py:module:: fnl.text.corpus
   :synopsis: Functions to create a (HTML-based) corpus.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from html import unescape
from io import StringIO
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as etree
from fn.monad import Option, optionable
import html5lib
from html5lib.constants import entities
from html5lib.filters import whitespace


ARTICLE_TAG = "article"
CORPUS_TAG = "body"
ROOT_TAG = "html"
HEAD_TAG = "head"
META_TAG = "meta"
TITLE_TAG = "title"
WRAPPER_TAG = "div"

NONBREAKING_TAGS = frozenset({
    'a',
    'abbr',
    'acronym',
    'applet',
    'area',
    'audio',
    'b',
    'base',
    'basefont',
    'bdo',
    'bgsound',
    'big',
    'blink',
    'canvas',
    'cite',
    'code',
    'col',
    'colgroup',
    'command',
    'del',
    'dfn',
    'em',
    'embed',
    'eventsource',
    'font',
    'frame',
    'i',
    'img',
    'input',
    'ins',
    'kbd',
    'link',
    'mark',
    'marquee',
    'meta',
    'meter',
    'nobr',
    'noembed',
    'noframes',
    'noscript',
    'object',
    'optgroup',
    'output',
    'param',
    'progress',
    'q',
    'rp',
    'rt',
    'ruby',
    's',
    'samp',
    'script',
    'small',
    'source',
    'spacer',
    'span',
    'strike',
    'strong',
    'style',
    'sub',
    'sup',
    'tbody',
    'tfoot',
    'thead',
    'time',
    'tt',
    'u',
    'var',
    'video',
    'wbr',
    'xmp',
})

SPACE_PRESERVING_TAGS = frozenset({
    'pre',
    'style',
    'script',
    'textarea',
})


_ensure = lambda e, tag: e.find(tag) if e.tag != tag else e

# HTML5 serialization setup
_tree_walker = html5lib.getTreeWalker("etree", implementation=etree)
_serializer = html5lib.serializer.HTMLSerializer(omit_optional_tags=False,
                                                 resolve_entities=False)

# HTML5 parsing setup
_tree_builder = html5lib.getTreeBuilder("etree", implementation=etree)
_parser = html5lib.HTMLParser(_tree_builder, namespaceHTMLElements=False)
# FIX for HTMLParser.reset():
if not hasattr(_parser, "innerHTMLMode"):
    # add the missing attribute, as otherwise calling .reset() would raise an AttributeError
    _parser.innerHTMLMode = None


def Root(title=None, encoding=None) -> Element:
    root = Element(ROOT_TAG)
    head = SubElement(root, HEAD_TAG)

    if title is not None:
        assert isinstance(title, str), 'title not a string'
        SubElement(head, TITLE_TAG).text = title

    if encoding is not None:
        assert isinstance(encoding, str), 'encoding not a string'
        SubElement(head, META_TAG, {'charset': encoding})

    return root


@optionable
def GetEncoding(root) -> Option(str):
    for meta in root.find(HEAD_TAG).iter(META_TAG):
        if meta.get('charset') is not None:
            return meta.get('charset')

    return None


def AddMeta(root, name, content) -> Element:
    assert isinstance(name, str), 'name not a string'
    assert isinstance(content, str), 'content not a string'

    while RemoveMeta(root, name):
        pass

    head = root.find(HEAD_TAG)
    SubElement(head, META_TAG, {'name': name, 'content': content})
    return root


@optionable
def GetMeta(root, name) -> Option(str):
    for meta in root.find(HEAD_TAG).iter(META_TAG):
        if meta.get('name') == name:
            return meta.get('content')

    return None


def RemoveMeta(root, name) -> bool:
    head = root.find(HEAD_TAG)

    for meta in head.iter(META_TAG):
        if meta.get('name') == name:
            head.remove(meta)
            return True

    return False


def GetMetaDict(root) -> dict:
    return {meta.get('name'): meta.get('content') for
            meta in root.find(HEAD_TAG).iter(META_TAG)}


def SetMetaDict(root, meta):
    for name, content in meta.items():
        AddMeta(root, name, content)


def SetContent(element, *content) -> Element:
    for item in content:
        if isinstance(item, str):
            SubElement(element, WRAPPER_TAG).text = item
        else:
            element.append(item)

    return element


def Corpus(*articles, **attributes) -> Element:
    corpus = Element(CORPUS_TAG, attributes)
    return SetContent(corpus, *articles)


def CreateCorpus(root, *articles, **attributes) -> Element:
    root = _ensure(root, ROOT_TAG)
    corpus = SubElement(root, CORPUS_TAG, attributes)
    return SetContent(corpus, *articles)


def Article(*content, **attributes) -> Element:
    article = Element(ARTICLE_TAG, attributes)
    return SetContent(article, *content)


def AppendArticle(corpus, *content, **attributes) -> Element:
    corpus = _ensure(corpus, CORPUS_TAG)
    article = SubElement(corpus, ARTICLE_TAG, attributes)
    return SetContent(article, *content)


def IterArticles(corpus) -> iter([Element]):
    corpus = _ensure(corpus, CORPUS_TAG)
    return corpus.iter(ARTICLE_TAG)


_DISPATCH = {
    'Characters': lambda buffer, name, data: buffer.append(unescape(data)),
    'SpaceCharacters': lambda buffer, name, data: buffer.append(unescape(data)),
    'Entity': lambda buffer, name, data: buffer.append(entities[name + ';']),
    'Comment': lambda buffer, name, data: None,
    'Doctype': lambda buffer, name, data: None,
}


def IterText(element, filter_spaces=False) -> iter([str]):
    buffer = StringIO()
    walker = _tree_walker(element)

    if filter_spaces:
        walker = whitespace.Filter(walker)

    for token in walker:
        type = token['type']

        if type in ('StartTag', 'EndTag', 'EmptyTag'):
            yield from _YieldBufferOnBreakingTag(buffer, token['name'])
        elif 'name' in token:
            _DISPATCH[type](buffer, token['name'], token['data'])

    yield buffer.getvalue()


def _YieldBufferOnBreakingTag(buffer, name):
    if name not in NONBREAKING_TAGS:
        yield buffer.getvalue()
        buffer.seek(0)


def Serialize(element) -> iter([bytes]):
    encoding = GetEncoding(element).get_or("UTF-8")
    return _serializer.serialize(_tree_walker(element), encoding=encoding)


def Deserialize(bytestream) -> Element:
    _parser.reset()
    return _parser.parse(bytestream)


def ReadCorpus(filepath) -> Element:
    with open(filepath, "rb") as instream:
        return _ensure(Deserialize(instream), ROOT_TAG)


def WriteCorpus(root, filepath):
    root = _ensure(root, ROOT_TAG)

    with open(filepath, "wb") as outstream:
        for data in Serialize(root):
            outstream.write(data)
