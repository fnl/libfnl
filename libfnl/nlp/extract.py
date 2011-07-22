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
from collections import namedtuple
from html.entities import entitydefs
from html.parser import HTMLParser
from libfnl.nlp.text import Text
from logging import getLogger
from mimetypes import guess_type
from socket import gethostname
from unicodedata import category, normalize
from urllib.parse import urljoin, urlsplit, urlunsplit

GREEK_LOWER = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "omicron": "ο",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
}

GREEK_UPPER = {
    "Alpha": "Α",
    "Beta": "Β",
    "Gamma": "Γ",
    "Delta": "Δ",
    "Epsilon": "Ε",
    "Zeta": "Ζ",
    "Eta": "Η",
    "Theta": "Θ",
    "Iota": "Ι",
    "Kappa": "Κ",
    "Lambda": "Λ",
    "Mu": "Μ",
    "Nu": "Ν",
    "Xi": "Ξ",
    "Omicron": "Ο",
    "Pi": "Π",
    "Rho": "Ρ",
    "Sigma": "Σ",
    "Tau": "Τ",
    "Upsilon": "Υ",
    "Phi": "Φ",
    "Chi": "Χ",
    "Psi": "Ψ",
    "Omega": "Ω",
}

def Extract(filename:str, encoding:str=None, mime_type:str=None) -> Text:
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
        text = Text(html.string, html.tags)
    elif mime_type == 'text/plain':
        plain_text = open(filename, 'rb').read()
        text = Text(plain_text)
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

    multi_ws = re.compile(r'\s+', re.ASCII) # only match r'[ \t\n\r\f\v]+'
    nl_end = re.compile(r'[\n\u2028]+$')
    url_like = re.compile('^\w*:?//\w+') # simple check if a href is URL-like
    ws_end = re.compile(r'\s+$')
    ws_start = re.compile(r'^\s+')

    # Special characters:
    LINE_SEP = '\u2028'
    NBS = '\u00A0'
    PARA_SEP = '\u2029'
    OBJECT_CHAR = '\uFFFC'
    REPLACEMENT = '\uFFFD'
    SPACES = frozenset(' \t\n\r\f\v{}{}{}'.format(LINE_SEP, NBS, PARA_SEP))

    ##########################
    # == ELEMENT HANDLING == #
    ##########################

    MINOR_CONTENT = frozenset({
        'button', 'caption', 'center', 'dd', 'dt', 'figcaption', 'h1', 'h2',
        'h3', 'h4', 'h5', 'h6', 'label', 'legend', 'li', 'option', 'summary',
        'td', 'textarea', 'tr', 'th',
    })
    """
    Minor content elements that will be followed by a single newline,
    not the two line feeds regular content tags get appended.
    """

    NORMAL_NAME = {
        'b': 'strong',
        'i': 'em',
        'plaintext': 'pre',
        's': 'del',
        'strike': 'del'
    }
    """
    These element names are normalized to reduce redundant tags, and hence,
    keys in the final tagged text.
    """

    EMPTY_ELEMS = frozenset({
        'area', 'base', 'basefont', 'bsound', 'br', 'col', 'command', 'embed',
        'eventsource', 'frame', 'hr', 'img', 'input', 'isindex', 'link',
        'meta', 'nobr', 'param', 'source', 'wbr'
    })
    # Elements that might not be closed but always are empty,
    # according to the W3C HTML specification.

    SKIPPED_ATTRIBUTES = frozenset({
        'accesskey', 'contenteditable', 'contextmenu',
        'draggable', 'dropzone', 'style', 'tabindex',
    })
    """
    These attributes are never stored/always dropped.
    """

    IGNORE = 0
    """
    Ignore all contained content of these elements and do not create tags.
    """

    CONTENT = 1
    """
    A 'cohesive' block of content, such as a paragraph, heading, table cell,
    or a list item, separated by one (minor) or two (major content blocks)
    newlines from each other (see :attr:`.MINOR_CONTENT`, too).

    Content block elements are stored as section tags.
    """

    INLINE = 2
    """
    These elements' offsets are maintained as format tags and transformed
    according to :class:`.Tag`.
    """

    REPLACE = 3
    """
    These elements are replaced with some meaningful characters.

    All such elements are treated as elements w/o special section or format
    annotations; they are:

    * ``br`` (replaced by a newline, but not annotated as tag)
    * ``hr`` (replaced by two newlines, but not annotated as tag)
    * ``img`` (replaced by the object replacement character or the alt
      attribute's value, if present)
    * ``area`` (replaced by the object replacement character or the alt
      attribute's value, if present)
    * ``meta`` (if it has a name and content attribute, those are added to the
      text, before the body section itself starts, as ``<name>: <content>\\n``)
    """

    ELEM_INDEX = {
        'a': INLINE,
        'abbr': INLINE,
        'acronym': INLINE,
        'address': CONTENT,
        'applet': IGNORE,
        'area': REPLACE,
        'article': CONTENT,
        'aside': CONTENT,
        'audio': IGNORE,
        'b': INLINE,
        'base': REPLACE,
        'basefont': INLINE,
        'bb': CONTENT,
        'bdo': INLINE,
        'bgsound': IGNORE,
        'big': INLINE,
        'blockquote': INLINE,
        'blink': INLINE,
        'body': CONTENT,
        'br': REPLACE,
        'button': CONTENT,
        'canvas': IGNORE,
        'caption': CONTENT,
        'center': CONTENT,
        'cite': INLINE,
        'code': INLINE,
        'col': INLINE,
        'colgroup': INLINE,
        'command': INLINE,
        'datagrid': CONTENT,
        'datalist': CONTENT,
        'dd': CONTENT,
        'del': INLINE,
        'details': CONTENT,
        'dfn': INLINE,
        'dialog': CONTENT,
        'dir': CONTENT,
        'div': CONTENT,
        'dl': CONTENT,
        'dt': CONTENT,
        'em': INLINE,
        'embed': IGNORE,
        'eventsource': IGNORE,
        'fieldset': CONTENT,
        'figcaption': CONTENT,
        'figure': CONTENT,
        'font': INLINE,
        'footer': CONTENT,
        'form': CONTENT,
        'frame': IGNORE,
        'frameset': CONTENT,
        'h1': CONTENT,
        'h2': CONTENT,
        'h3': CONTENT,
        'h4': CONTENT,
        'h5': CONTENT,
        'h6': CONTENT,
        'head': CONTENT,
        'header': CONTENT,
        'hgroup': CONTENT,
        'hr': REPLACE, # SPECIAL: create content block separator!
        'html': CONTENT,
        'i': INLINE,
        'iframe': CONTENT,
        'img': REPLACE,
        'input': IGNORE,
        'ins': INLINE,
        'isindex': IGNORE,
        'kbd': INLINE,
        'keygen': IGNORE,
        'label': CONTENT,
        'legend': CONTENT,
        'li': CONTENT,
        'listing': CONTENT,
        'link': IGNORE,
        'map': CONTENT,
        'mark': INLINE,
        'marquee': INLINE,
        'menu': CONTENT,
        'meta': REPLACE,
        'meter': INLINE,
        'nav': CONTENT,
        'nobr': IGNORE,
        'noembed': INLINE,
        'noframes': INLINE,
        'noscript': INLINE,
        'object': IGNORE,
        'ol': CONTENT,
        'optgroup': INLINE,
        'option': INLINE,
        'output': IGNORE,
        'p': CONTENT,
        'param': IGNORE,
        'plaintext': CONTENT,
        'pre': CONTENT,
        'progress': INLINE,
        'q': INLINE,
        'rp': IGNORE,
        'rt': IGNORE,
        'ruby': IGNORE,
        's': INLINE,
        'samp': INLINE,
        'script': IGNORE,
        'section': CONTENT,
        'select': CONTENT,
        'small': INLINE,
        'source': IGNORE,
        'spacer': INLINE,
        'span': INLINE,
        'strike': INLINE,
        'strong': INLINE,
        'style': IGNORE,
        'sub': INLINE,
        'summary': CONTENT,
        'sup': INLINE,
        'table': CONTENT,
        'tbody': INLINE,
        'td': CONTENT,
        'textarea': CONTENT,
        'tfoot': INLINE,
        'th': CONTENT,
        'thead': INLINE,
        'time': INLINE,
        'title': CONTENT,
        'tr': INLINE,
        'tt': INLINE,
        'u': INLINE,
        'ul': CONTENT,
        'var': INLINE,
        'video': IGNORE,
        'wbr': INLINE,
        'xmp': INLINE,
    }
    """
    A mapping of all possible HTML 4 and 5 element names to their
    :attr:`.CONTENT` (1),
    :attr:`.INLINE` (2),
    :attr:`.REPLACE` (3), and
    :attr:`.IGNORE` (0)
    assignments.

    .. warning::

        Element names encountered during parsing but not listed here will raise
        a :exc:`RuntimeError`\ .
    """

    Tag = namedtuple('Tag', 'name type attrs title alt')

    @classmethod
    def _Tag(cls, name:str, attrs:tuple, url:str):
        # Create a new tag.
        attrs = dict(attrs)
        title = None
        alt = None

        for k in list(attrs.keys()):
            if not attrs[k]:
                del attrs[k]
            elif k == 'href':
                href = urlunsplit(urlsplit(attrs[k]))
                if url: attrs[k] = urljoin(url, href)
                elif href: attrs[k] = href
                else: del attrs[k]
            elif k == 'title':
                title = attrs[k]
                del attrs[k]
            elif k == 'alt':
                alt = attrs[k]
                del attrs[k]

                if alt in GREEK_UPPER:
                    alt = GREEK_UPPER[alt]
                elif alt in GREEK_LOWER or alt.lower() in GREEK_LOWER:
                    alt = GREEK_LOWER[alt]
            elif k in HtmlExtractor.SKIPPED_ATTRIBUTES:
                del attrs[k]

        try:
            tag_type = cls.ELEM_INDEX[name]
        except KeyError:
            cls.L.warn('HTML element %s unknown; ignoring content', name)
            tag_type = cls.IGNORE

        if name in cls.NORMAL_NAME:
            name = cls.NORMAL_NAME[name]

        return cls.Tag(name, tag_type, attrs, alt, title)

    @classmethod
    def isIgnored(cls, tag:Tag) -> bool:
        return tag.type == cls.IGNORE

    @classmethod
    def isContent(cls, tag:Tag) -> bool:
        return tag.type == cls.CONTENT

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
        self.__root = (HtmlExtractor.Tag('root', *[None]*4), [])
        self.__state = []
        self.__string = None
        self.__url = None
        self.__chunks = self.__root[1]
        self.tags = None

    def reset(self):
        """
        Reset the instance for re-use on another document/feed.
        """
        super(HtmlExtractor, self).reset()
        self.__ignoring_content = []
        self.__in_body = False
        self.__root = (HtmlExtractor.Tag('root', *[None]*4), [])
        self.__state = []
        self.__string = None
        self.__url = None
        self.__chunks = self.__root[1]
        self.tags = None

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
        if url and HtmlExtractor.url_like.match(url):
            self.__url = urlunsplit(urlsplit(url, 'http'))

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
            self.tags = dict()
            strlen = self._toOffsets(self.__root, 0)
            self.__string = ''.join(self.__string).replace(
                HtmlExtractor.LINE_SEP, '\n'
            )
            assert strlen == len(self.__string)

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
                    chunk = self.multi_ws.sub(' ', chunk)
                    chunk = chunk.replace(HtmlExtractor.PARA_SEP, '\n\n')
                    last = ''

                    for s in reversed(self.__string):
                        if s:
                            last = s
                            break

                    if HtmlExtractor.ws_end.search(last):
                        chunk = HtmlExtractor.ws_start.sub('', chunk)

                if chunk:
                    chunk = normalize('NFC', chunk)
                    self.__string.append(chunk)
                    end += len(chunk)

        if tag.title:
            prefix = '' if self.__string[-1].endswith(' ') else ' '
            title = self.multi_ws.sub(' ', tag.title)
            suffix = '' if HtmlExtractor.isContent(tag) else ' '
            self.__string.append(normalize(
                'NFC', '{}({}){}'.format(prefix, title, suffix)
            ))
            end += len(self.__string[-1])

        return end

    def _createTag(self, tag:Tag, start:int, end:int) -> int:
        self.tags[('html', tag.name, (start, end))] = tag.attrs

        if HtmlExtractor.isContent(tag):
            if tag.name != 'body':
                last = ''

                for s in reversed(self.__string):
                    if s:
                        last += s
                        if len(last) > 1: break

                mo = HtmlExtractor.nl_end.search(last)

                if mo: last = mo.group()
                else: last = ''

                if tag.name in HtmlExtractor.MINOR_CONTENT:
                    if not last:
                        self.__string.append('\n')
                        end += 1
                else:
                    if not len(last) > 1:
                        self.__string.append('\n\n')
                        end += 2
        elif not HtmlExtractor.isInlined(tag):
            msg = 'unexpected tag {}'.format(tag)
            raise RuntimeError(msg)
        return end

    @classmethod
    def _stripContent(cls, chunks:list):
        def strip(i, f):
            for idx in i:
                if isinstance(chunks[idx], str):
                    chunks[idx] = f(cls.multi_ws.sub(' ', chunks[idx]))
                    if chunks[idx]: break
                else:
                    break

        strip(range(len(chunks)), lambda c: c.lstrip())
        strip(reversed(range(len(chunks))), lambda c: c.rstrip())

    ####################
    # == EXTRACTION == #
    ####################

    def handle_starttag(self, name:str, attrs:tuple):
        if name in HtmlExtractor.EMPTY_ELEMS:
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
                self._replace(tag)
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
        elif name in HtmlExtractor.EMPTY_ELEMS:
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
                                HtmlExtractor.multi_ws.match(char)):
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

    def _replace(self, tag:Tag):
        if tag.name == 'meta':
            if 'name' in tag.attrs and 'content' in tag.attrs:
                string = '{}: {}'.format(tag.attrs['name'],
                                           tag.attrs['content'])
                del tag.attrs['name']
                del tag.attrs['content']
                # append as 'mini-node' by simulating it were an inline tag
                self.__chunks.append((tag._replace(type=HtmlExtractor.INLINE),
                                      [string]))
                self.__chunks.append(HtmlExtractor.LINE_SEP)
        elif tag.name == 'br':
            self.__chunks.append(HtmlExtractor.LINE_SEP)
        elif tag.name == 'img' or tag.name == 'area':
            # append as 'mini-node' by simulating it were an inline tag
            self.__chunks.append((tag._replace(type=HtmlExtractor.INLINE),
                                  [tag.alt or HtmlExtractor.OBJECT_CHAR]))
        elif tag.name == 'hr':
            self.__chunks.append(HtmlExtractor.PARA_SEP)
        elif tag.name == 'base':
            if 'href' in tag.attrs and not self.__url and \
               HtmlExtractor.url_like.match(tag.attrs['href']):
                self.__url = urlunsplit(urlsplit(tag.attrs['href'], 'http'))
        else:
            msg = 'replacement for tag {} undefined'.format(tag.name)
            raise RuntimeError(msg)
