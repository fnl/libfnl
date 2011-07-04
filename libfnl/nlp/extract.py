"""
.. py:module:: extract
   :synopsis: Extract text from files.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)

Conversion of content from files to the internal :mod:`libfnl.nlp.text`
format, attempting to preserve annotations where possible.
"""
import os
import re
from collections import defaultdict, namedtuple
from html.entities import entitydefs
from html.parser import HTMLParser
from libfnl.nlp.text import Unicode
from logging import getLogger
from mimetypes import guess_type
from socket import gethostname
from unicodedata import category, normalize
from urllib.parse import urlparse


def Extract(filename:str, encoding:str=None, mime_type:str=None) -> Unicode:
    """
    :param filename: The path and name of the file to extract.
    :param encoding: The charset encoding of the file; can be guessed by
        :func:`mimetypes.guess_type`. However, if the encoding cannot be
        guessed, UTF-8 is assumed.
    :param mime_type: Optionally, set the MIME type that describes the
        file's type (instead of having `mimetypes` guess it).
    :return: A :class:`.Unicode` text.
    :raise IOError: If the file cannot be opened.
    :raise RuntimeError: If there are no extraction rules for the file's MIME
        type or the extractor fails horribly.
    """
    logger = getLogger('Extract')

    if not encoding or not mime_type:
        guessed_mime_type, guessed_encoding = guess_type(filename)

        if not encoding:
            if not guessed_encoding:
                logger.warn('encoding of %s unknown - using UTF-8', filename)
                guessed_encoding = 'utf-8'

            encoding = guessed_encoding

        if not mime_type:
            if not guessed_mime_type:
                logger.warn('could not guess MIME type of %s', filename)
                logger.info('assuming text/plain for %s', filename)
                mime_type = 'text/plain'
            else:
                mime_type = guessed_mime_type

    if mime_type in ('text/html', 'application/xhtml'):
        html = HtmlExtractor()

        for line in open(filename, encoding=encoding):
            html.feed(line)

        html.close()
        text = Unicode(html.string)
        text.tags = {
            'section': html.section_tags,
            'format': html.format_tags
        }
        text.metadata['source'] = html.url or MakeSource(filename)
    elif mime_type == 'text/plain':
        plain_text = open(filename, 'rb').read()
        text = Unicode(plain_text)
        text.metadata['source'] = MakeSource(filename)
    else:
        msg = 'no extraction rules for MIME type {}'.format(mime_type)
        raise RuntimeError(msg)

    return text


def MakeSource(filename:str) -> str:
    username = os.getlogin()
    hostname = gethostname()

    if not os.path.isabs(filename):
        filename = os.path.join(os.getcwd(), filename)

    return '{}@{}:{}'.format(username, hostname, filename)


class HtmlExtractor(HTMLParser):

    L = getLogger('HtmlExtractor')

    MULTI_WS = re.compile(r'\s+', re.ASCII) # only match r'[ \t\n\r\f\v]+'

    # Special characters:
    LINE_SEP = '\u2028'
    NBS = '\u00A0'
    PARA_SEP = '\u2029'
    OBJECT_CHAR = '\uFFFC'
    REPLACEMENT = '\uFFFD'
    SPACES = frozenset(' \t\n\r\f\v{}{}{}'.format(LINE_SEP, NBS, PARA_SEP))

    URL_LIKE = re.compile('^\w+://') # simple check if a string is 'URL-like'

    EMPTY_TAGS = frozenset({
        'area', 'base', 'basefont', 'bsound', 'br', 'col', 'command', 'embed',
        'eventsource', 'frame', 'hr', 'img', 'input', 'isindex', 'link',
        'meta', 'nobr', 'param', 'source', 'wbr'
    })
    # Elements that might not be closed but always are empty,
    # according to the W3C HTML specification.

    MINOR_CONTENT = frozenset({
        'button', 'caption', 'center', 'dd', 'dt', 'figcaption', 'h1', 'h2',
        'h3', 'h4', 'h5', 'h6', 'label', 'legend', 'li', 'option', 'summary',
        'td', 'textarea', 'tr', 'th',
    })
    """
    Minor content elements that will be followed by a single newline,
    not the two line feeds regular content tags get appended.
    """

    NORMAL_TAG = {
        'b': 'strong',
        'i': 'em',
        'plaintext': 'pre',
        's': 'del',
        'strike': 'del'
    }
    """
    These elements are normalized to reduce redundant tags, and hence,
    keys in the final tagged text.
    """

    IGNORE = 0
    """
    Ignore all contained content of these elements and do not create tags.
    """

    CONTENT_BLOCK = 1
    """
    A 'cohesive' block of content, such as a paragraph, heading, table cell,
    or a list item, separated by one (minor) or two (major content blocks)
    newlines from each other (see :attr:`.MINOR_CONTENT`, too).

    Content block elements are stored as section tags.
    """

    REPLACE = 2
    """
    These elements are replaced with some meaningful characters.

    All such elements are treated as elements w/o special section or format
    annotations; they are:

    * ``br`` (replaced by a newline, but not annotated)
    * ``hr`` (replaced by two newlines, but not annotated)
    * ``img`` (replaced by the object replacement character or the content of
      its title attribute, if present)
    * ``meta`` (if it has a name and content attribute, those are added to the
      text, before the body section itself starts, as ``<name>: <content>\\n``)
    """

    INLINE = 3
    """
    These elements' offsets are maintained as format tags and transformed
    according to :class:`.Tag`.
    """

    #############
    # == Tag == #
    #############

    Tag = namedtuple('Tag', 'name type id classes href title')

    TAG_INDEX = {
        'a': INLINE,
        'abbr': INLINE,
        'acronym': INLINE,
        'address': CONTENT_BLOCK,
        'applet': IGNORE,
        'area': IGNORE,
        'article': CONTENT_BLOCK,
        'aside': CONTENT_BLOCK,
        'audio': IGNORE,
        'b': INLINE,
        'base': REPLACE,
        'basefont': IGNORE,
        'bb': CONTENT_BLOCK,
        'bdo': INLINE,
        'bgsound': IGNORE,
        'big': INLINE,
        'blockquote': INLINE,
        'blink': INLINE,
        'body': CONTENT_BLOCK,
        'br': REPLACE,
        'button': CONTENT_BLOCK,
        'canvas': IGNORE,
        'caption': CONTENT_BLOCK,
        'center': CONTENT_BLOCK,
        'cite': INLINE,
        'code': INLINE,
        'col': INLINE,
        'colgroup': IGNORE,
        'command': IGNORE,
        'datagrid': CONTENT_BLOCK,
        'datalist': CONTENT_BLOCK,
        'dd': CONTENT_BLOCK,
        'del': INLINE,
        'details': CONTENT_BLOCK,
        'dfn': INLINE,
        'dialog': CONTENT_BLOCK,
        'dir': CONTENT_BLOCK,
        'div': CONTENT_BLOCK,
        'dl': CONTENT_BLOCK,
        'dt': CONTENT_BLOCK,
        'em': INLINE,
        'embed': IGNORE,
        'eventsource': IGNORE,
        'fieldset': CONTENT_BLOCK,
        'figcaption': CONTENT_BLOCK,
        'figure': CONTENT_BLOCK,
        'font': INLINE,
        'footer': CONTENT_BLOCK,
        'form': CONTENT_BLOCK,
        'frame': IGNORE,
        'frameset': CONTENT_BLOCK,
        'h1': CONTENT_BLOCK,
        'h2': CONTENT_BLOCK,
        'h3': CONTENT_BLOCK,
        'h4': CONTENT_BLOCK,
        'h5': CONTENT_BLOCK,
        'h6': CONTENT_BLOCK,
        'head': CONTENT_BLOCK,
        'header': CONTENT_BLOCK,
        'hgroup': CONTENT_BLOCK,
        'hr': REPLACE, # SPECIAL: create content block separator!
        'html': CONTENT_BLOCK,
        'i': INLINE,
        'iframe': CONTENT_BLOCK,
        'img': REPLACE,
        'input': IGNORE,
        'ins': INLINE,
        'isindex': IGNORE,
        'kbd': INLINE,
        'keygen': IGNORE,
        'label': CONTENT_BLOCK,
        'legend': CONTENT_BLOCK,
        'li': CONTENT_BLOCK,
        'listing': CONTENT_BLOCK,
        'link': IGNORE,
        'map': INLINE,
        'mark': INLINE,
        'marquee': INLINE,
        'menu': CONTENT_BLOCK,
        'meta': REPLACE,
        'meter': INLINE,
        'nav': CONTENT_BLOCK,
        'nobr': IGNORE,
        'noembed': INLINE,
        'noframes': INLINE,
        'noscript': INLINE,
        'object': IGNORE,
        'ol': CONTENT_BLOCK,
        'optgroup': IGNORE,
        'option': CONTENT_BLOCK,
        'output': IGNORE,
        'p': CONTENT_BLOCK,
        'param': IGNORE,
        'plaintext': CONTENT_BLOCK,
        'pre': CONTENT_BLOCK,
        'progress': INLINE,
        'q': INLINE,
        'rp': IGNORE,
        'rt': IGNORE,
        'ruby': IGNORE,
        's': INLINE,
        'samp': INLINE,
        'script': IGNORE,
        'section': CONTENT_BLOCK,
        'select': CONTENT_BLOCK,
        'small': INLINE,
        'source': IGNORE,
        'spacer': INLINE,
        'span': INLINE,
        'strike': INLINE,
        'strong': INLINE,
        'style': IGNORE,
        'sub': INLINE,
        'summary': CONTENT_BLOCK,
        'sup': INLINE,
        'table': CONTENT_BLOCK,
        'tbody': INLINE,
        'td': CONTENT_BLOCK,
        'textarea': CONTENT_BLOCK,
        'tfoot': INLINE,
        'th': CONTENT_BLOCK,
        'thead': INLINE,
        'time': INLINE,
        'title': CONTENT_BLOCK,
        'tr': INLINE,
        'tt': INLINE,
        'u': INLINE,
        'ul': CONTENT_BLOCK,
        'var': INLINE,
        'video': IGNORE,
        'wbr': IGNORE,
        'xmp': INLINE, }
    """
    A mapping of all valid HTML 4 and 5 tags to
    :attr:`.INLINE` (3),
    :attr:`.CONTENT_BLOCK` (1),
    :attr:`.REPLACE` (2), and
    :attr:`.IGNORE` (0)
    assignments.

    Tags encountered during parsing but not listed here will raise a
    :exc:`RuntimeError`\ .
    """

    @classmethod
    def _Tag(cls, name:str, attrs:tuple, url:str) -> Tag:
        # Create a new tag.
        tag_id = ""
        classes = ""
        href = None
        title = None

        for att, val in attrs:
            if not val:
                continue
            elif att == 'id':
                tag_id = '#{}'.format(val.strip())
            elif att == 'class' and val:
                classes = '.{}'.format('.'.join(c for c in val.split() if c))
            elif att == 'title':
                title = val.strip()
            elif att == 'href' and url and val != '#':
                href = cls._makeHrefLink(url, val)

        try:
            tag_type = cls.TAG_INDEX[name]
        except KeyError:
            cls.L.warn('HTML name %s unknown; ignoring content', name)
            tag_type = cls.IGNORE

        if name in cls.NORMAL_TAG:
            name = cls.NORMAL_TAG[name]

        return cls.Tag(name, tag_type, tag_id, classes, href, title)

    @classmethod
    def _makeHrefLink(cls, url:str, val:str) -> str:
        parsed = urlparse(url)

        if val[0] == '#':
            return '%s://%s%s%s' % (parsed.scheme, parsed.netloc,
                                    parsed.path, val)
        elif val[0] == '/':
            return '%s://%s%s' % (parsed.scheme, parsed.netloc, val)
        elif cls.URL_LIKE.match(val):
            return val
        else:
            path = parsed.path.split('/')
            path = '/'.join(path[1:-1])
            return '%s://%s/%s/%s' % (parsed.scheme, parsed.netloc, path, val)

    ##############################
    # == TAG CHECKING METHODS == #
    ##############################

    @classmethod
    def isIgnored(cls, tag:Tag) -> bool:
        return tag.type == cls.IGNORE

    @classmethod
    def isContent(cls, tag:Tag) -> bool:
        return tag.type == cls.CONTENT_BLOCK

    @classmethod
    def isReplaced(cls, tag:Tag) -> bool:
        return tag.type == cls.REPLACE

    @classmethod
    def isInlined(cls, tag:Tag) -> bool:
        return tag.type == cls.INLINE

    ###############
    # == SETUP == #
    ###############

    def __init__(self):
        """
        Create a new extractor that can be reused with :meth:`.reset()`,
        run with :meth:`.feed()`, and the result then fetched from
        :attr:`.string`.
        """
        super(HtmlExtractor, self).__init__()
        self.__ignoring_content = []
        self.__in_body = False
        self.__root = (HtmlExtractor.Tag('root', *[None]*5), [])
        self.__state = []
        self.__string = None
        self.__url = None
        self.__chunks = self.__root[1]
        self.format_tags = None
        self.section_tags = None

    def reset(self):
        """
        Reset the instance for re-use on another document/feed.
        """
        super(HtmlExtractor, self).reset()
        self.__ignoring_content = []
        self.__in_body = False
        self.__root = (HtmlExtractor.Tag('root', *[None]*5), [])
        self.__state = []
        self.__string = None
        self.__url = None
        self.__chunks = self.__root[1]
        self.format_tags = None
        self.section_tags = None

    #noinspection PyMethodOverriding
    def feed(self, data:str, url:str=None):
        """
        Feed the extractor with a complete or partial HTML string.

        The *URL* should be the URL from where the HTML resource was fetched;
        This URL is used to change all href attributes to fully qualified URLs.

        :param data: The HTML, as string.
        :param url: The base URL to use for ``href`` attributes that are not
            fully qualified URLs; If the HTML has a base element with the href
            attribute set, that is used unless set here explicitly.
        """
        self.__url = url
        super(HtmlExtractor, self).feed(data)

    ######################
    # == CONSTRUCTION == #
    ######################

    @property
    def url(self) -> str:
        """
        Return any URL set or found for this document (or ``None``).
        """
        return self.__url

    @property
    def string(self) -> str:
        """
        After feeding the parser (and, possibly, calling :meth:`.close`, too),
        the extracted text can be fetched from this attribute.
        """
        assert not self.__state, 'parse not complete: {}'.format(self.__state)
        
        if self.__string is None:
            self.__string = ['']
            self.format_tags = defaultdict(list)
            self.section_tags = defaultdict(list)
            strlen = self._toOffsets(self.__root, 0)
            self.__string = ''.join(self.__string).replace(
                HtmlExtractor.LINE_SEP, '\n'
            )
            assert strlen == len(self.__string)
            self.format_tags = dict(self.format_tags)
            self.section_tags = dict(self.section_tags)

        return self.__string

    def _toOffsets(self, node:(Tag, list), start:int) -> int:
        tag = node[0]
        end = start

        if HtmlExtractor.isContent(tag) and node[1] and node[0].name != 'pre':
            HtmlExtractor._stripContent(node[1])

        end = self._appendStrings(node, end)

        if tag.name not in ('root', 'html') and start != end:
            end = self._createTag(tag, start, end)

        return end

    def _appendStrings(self, node:(Tag, list), end:int) -> int:
        tag = node[0]

        for chunk in node[1]:
            if isinstance(chunk, tuple):
                end = self._toOffsets(chunk, end)
            else:
                if tag.name != 'pre':
                    chunk = self.MULTI_WS.sub(' ', chunk)
                    chunk = chunk.replace(HtmlExtractor.PARA_SEP, '\n')
                    last = self.__string[-1]

                    if last in HtmlExtractor.SPACES and chunk.startswith(' '):
                        chunk = chunk[1:]

                if chunk:
                    self.__string.append(normalize('NFC', chunk))
                    end += len(chunk)

        if tag.title:
            prefix = '' if self.__string[-1].endswith(' ') else ' '
            title = self.MULTI_WS.sub(' ', tag.title).strip()
            suffix = '' if HtmlExtractor.isContent(tag) else ' '
            self.__string.append(normalize(
                'NFC', '{}({}){}'.format(prefix, title, suffix)
            ))
            end += len(self.__string[-1])

        return end

    def _createTag(self, tag:Tag, start:int, end:int) -> int:
        offset = (start, end)

        if HtmlExtractor.isInlined(tag):
            key = '{}{}'.format(tag.name, tag.classes)
            if tag.href: key = '{}:{}'.format(key, tag.href)
            self.format_tags[key].append(offset)
        elif HtmlExtractor.isContent(tag):
            key = '{}{}{}'.format(tag.name, tag.id, tag.classes)
            self.section_tags[key].append(offset)

            if tag.name != 'body':
                if tag.name in HtmlExtractor.MINOR_CONTENT:
                    self.__string.append('\n')
                    end += 1
                else:
                    self.__string.append('\n\n')
                    end += 2
        else:
            msg = 'unexpected tag type {}'.format(tag)
            raise RuntimeError(msg)
        return end

    @classmethod
    def _stripContent(cls, chunks:list):
        def strip(i, f):
            for idx in i:
                if isinstance(chunks[idx], str):
                    chunks[idx] = f(cls.MULTI_WS.sub(' ', chunks[idx]))
                    if chunks[idx]: break
                else:
                    break

        strip(range(len(chunks)), lambda c: c.lstrip())
        strip(reversed(range(len(chunks))), lambda c: c.rstrip())

    ####################
    # == EXTRACTION == #
    ####################

    def handle_starttag(self, name:str, attrs:tuple):
        if name in HtmlExtractor.EMPTY_TAGS:
            # redirect to the right handle
            return self.handle_startendtag(name, attrs)

        if not self.__ignoring_content:
            tag = HtmlExtractor._Tag(name, attrs, self.__url)

            if HtmlExtractor.isContent(tag) or HtmlExtractor.isInlined(tag):
                if tag.name == 'body': self.__in_body = True
                node = (tag, [])
                self.__chunks.append(node)
                self.__state.append(node)
                self.__chunks = node[1]
            elif HtmlExtractor.isIgnored(tag):
                self.__ignoring_content.append(name)
            else:
                msg = 'unhandled type {} for tag {}'.format(tag.type, name)
                raise RuntimeError(msg)
        else:
            self.__ignoring_content.append(name)

    def handle_startendtag(self, name:str, attrs:tuple):
        if not self.__ignoring_content:
            tag = self._Tag(name, attrs, self.__url)

            if self.isIgnored(tag):
                pass
            elif self.isReplaced(tag):
                self._handleReplacementTag(tag, attrs)
            elif self.isInlined(tag):
                if tag.title: self.__chunks.append(' {} '.format(tag.title))
            else:
                msg = 'unhandled type {} for tag {}'.format(tag.type, name)
                raise RuntimeError(msg)

    def handle_endtag(self, name:str):
        if self.__ignoring_content:
            checked = self.__ignoring_content.pop()
            assert name == checked, \
                'expected {}, got {} in {}'.format(checked, name,
                                                   self.__ignoring_content)
        elif name in HtmlExtractor.EMPTY_TAGS:
            pass
        else:
            node = self.__state.pop()
            if self.__state: parent = self.__state[-1]
            else: parent = self.__root

            if __debug__:
                for n in reversed(parent[1]):
                    if isinstance(n, tuple):
                        assert n == node, \
                            'expected {}\nfound {}\nin {}\n at {}'.format(
                                n, node, parent, [s[0] for s in self.__state]
                            )
                        break

            self.__chunks = parent[1]
            if node[0].name == 'body': self.__in_body = False

    def handle_data(self, data:str):
        if self.__in_body and not self.__ignoring_content:
            self.__chunks.append(data)

    def handle_charref(self, ref:str):
        if self.__in_body and not self.__ignoring_content:
            try:
                codepoint = int(ref[1:], 16) if ref[0].lower() == 'x' else \
                            int(ref)
                char = chr(codepoint)

                if not char or (category(char) == 'Cc' and not
                                HtmlExtractor.MULTI_WS.match(char)):
                    raise ValueError('empty/control characters are forbidden')

                self.__chunks.append(char)
            except (ValueError, OverflowError):
                self.L.warn('HTML charref &#%s; not a valid codepoint', ref)
                self.__chunks.append(HtmlExtractor.REPLACEMENT)

    def handle_entityref(self, ref:str):
        if self.__in_body and not self.__ignoring_content:
            try:
                self.__chunks.append(entitydefs[ref])
            except KeyError:
                self.L.warn('HTML entityref &%s; unknown', ref)
                self.__chunks.append(HtmlExtractor.REPLACEMENT)

    def _handleReplacementTag(self, tag:Tag, attrs:tuple):
        if tag.name == 'meta':
            meta = dict(attrs)

            if 'name' in meta and 'content' in meta:
                string = '{}: {}{}'.format(meta['name'].strip(),
                                           meta['content'].strip(),
                                           HtmlExtractor.LINE_SEP)
                self.__chunks.append(string)
        elif tag.name == 'br':
            self.__chunks.append(HtmlExtractor.LINE_SEP)
        elif tag.name == 'img':
            if tag.title: self.__chunks.append(' {} '.format(tag.title))
            else:         self.__chunks.append(HtmlExtractor.OBJECT_CHAR)
        elif tag.name == 'hr':
            self.__chunks.append(HtmlExtractor.PARA_SEP)
        elif tag.name == 'base':
            if tag.href and not self.__url and \
               HtmlExtractor.URL_LIKE.match(tag.href): self.__url = tag.href
        else:
            msg = 'replacement for tag {} undefined'.format(tag.name)
            raise RuntimeError(msg)
