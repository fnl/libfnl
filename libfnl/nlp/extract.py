"""
.. py:module:: extract
   :synopsis: Extract text from files.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)

Conversion of content from files to the internal :mod:`libfnl.nlp.text`
format, attempting to preserve annotations where possible.
"""
import os
from html.entities import entitydefs
from html.parser import HTMLParser, HTMLParseError
import re
from unicodedata import normalize
from libfnl.nlp.text import Text
from logging import getLogger
from mimetypes import guess_type
from socket import gethostname

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
    "ypsilon": "υ",
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
    "Ypsilon": "Υ",
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
        html.feed(open(filename, encoding=encoding).read())
        html.close()
        text = Text(html.string)
        tags = [(t, html.tags[t]) for t in sorted(html.tags, key=Text.Key)]
        text.add(tags, html.namespace)
    elif mime_type == 'text/plain':
        encoding = encoding or 'utf-8'
        plain_text = open(filename, 'rb', encoding=encoding).read()
        text = Text(normalize('NFC', plain_text))
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

    REPLACEMENT = '\uFFFD'
    OBJECT_REPLACEMENT = '\uFFFC'
    WS_REGEX = re.compile(r'\s+')
    RSTRIP_REGEX = re.compile(r'\s+$')

    IGNORE, INLINE, MINOR, CONTENT = 0, 1, 2, 3
    # IGNORE: content and tag will never be added
    # INLINE: no newline added after the tag's content
    # MINOR: single newline added after the tag's content
    # CONTENT: double newline added after the tag's content

    ELEMENTS = {
        'a': INLINE,
        'abbr': INLINE,
        'acronym': INLINE,
        'address': CONTENT,
        'applet': IGNORE, # IGNORE
        'area': INLINE,
        'article': CONTENT,
        'aside': CONTENT,
        'audio': IGNORE, # IGNORE
        'b': INLINE,
        'base': INLINE,
        'basefont': INLINE,
        'bb': CONTENT,
        'bdo': INLINE,
        'bgsound': IGNORE, # IGNORE
        'big': INLINE,
        'blockquote': INLINE,
        'blink': INLINE,
        'body': INLINE,
        'br': INLINE,
        'button': MINOR,
        'canvas': IGNORE, # IGNORE
        'caption': MINOR,
        'center': MINOR,
        'cite': INLINE,
        'code': INLINE,
        'col': INLINE,
        'colgroup': INLINE,
        'command': INLINE,
        'datagrid': CONTENT,
        'datalist': CONTENT,
        'dd': MINOR,
        'del': INLINE,
        'details': CONTENT,
        'dfn': INLINE,
        'dialog': CONTENT,
        'dir': CONTENT,
        'div': CONTENT,
        'dl': CONTENT,
        'dt': MINOR,
        'em': INLINE,
        'embed': IGNORE, # IGNORE
        'eventsource': IGNORE, # IGNORE
        'fieldset': CONTENT,
        'figcaption': MINOR,
        'figure': CONTENT,
        'font': INLINE,
        'footer': CONTENT,
        'form': CONTENT,
        'frame': IGNORE, # IGNORE
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
        'hr': INLINE,
        'html': CONTENT,
        'i': INLINE,
        'iframe': CONTENT,
        'img': INLINE,
        'input': INLINE,
        'ins': INLINE,
        'isindex': IGNORE, # IGNORE
        'kbd': INLINE,
        'keygen': IGNORE, # IGNORE
        'label': MINOR,
        'legend': MINOR,
        'li': MINOR,
        'listing': CONTENT,
        'link': INLINE,
        'map': CONTENT,
        'mark': INLINE,
        'marquee': INLINE,
        'menu': CONTENT,
        'meta': INLINE,
        'meter': INLINE,
        'nav': CONTENT,
        'nobr': INLINE,
        'noembed': INLINE,
        'noframes': INLINE,
        'noscript': INLINE,
        'object': IGNORE, # IGNORE
        'ol': CONTENT,
        'optgroup': INLINE,
        'option': MINOR,
        'output': IGNORE, # IGNORE
        'p': CONTENT,
        'param': IGNORE, # IGNORE
        'plaintext': CONTENT,
        'pre': CONTENT,
        'progress': INLINE,
        'q': INLINE,
        'rp': IGNORE, # IGNORE
        'rt': IGNORE, # IGNORE
        'ruby': IGNORE, # IGNORE
        's': INLINE,
        'samp': INLINE,
        'script': IGNORE, # IGNORE
        'section': CONTENT,
        'select': CONTENT,
        'small': INLINE,
        'source': IGNORE, # IGNORE
        'spacer': INLINE,
        'span': INLINE,
        'strike': INLINE,
        'strong': INLINE,
        'style': IGNORE, # IGNORE
        'sub': INLINE,
        'summary': MINOR,
        'sup': INLINE,
        'table': CONTENT,
        'tbody': INLINE,
        'td': MINOR,
        'textarea': MINOR,
        'tfoot': INLINE,
        'th': MINOR,
        'thead': INLINE,
        'time': INLINE,
        'title': CONTENT,
        'tr': MINOR,
        'tt': INLINE,
        'u': INLINE,
        'ul': CONTENT,
        'var': INLINE,
        'video': IGNORE, # IGNORE
        'wbr': INLINE,
        'xmp': INLINE,
    }

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

    EMPTY_ELEMENTS = frozenset({
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
    These attributes are never extracted/always dropped.
    """

    def __init__(self, namespace:str='html'):
        """
        :param namespace: The namespace to use for the tags.
        """
        HTMLParser.__init__(self)
        self.namespace = namespace
        self._string = []
        self._elements = []
        self._ignored = []
        self.tags = dict()

    def _addContentBreak(self):
        # Add up to 2 LF chars to _string.
        # Must have a string before already, and only add two LFs if there are
        # none before, or add one if there is just one LF before.
        length = 0

        if self._string:
            if len(self._string[-1]) > 1:
                if not self._string[-1].endswith('\n\n'):
                    if self._string[-1][-1] == '\n':
                        self._string.append('\n')
                        length = 1
                    else:
                        self._string.append('\n\n')
                        length = 2
            elif self._string[-1][-1] == '\n':
                if len(self._string) > 1:
                    if self._string[-2][-1] != '\n':
                        self._string.append('\n')
                        length = 1
            else:
                self._string.append('\n\n')
                length = 2

        return length

    def _addImgOrArea(self, name:str, attrs:dict):
        if 'alt' in attrs or 'title' in attrs:
            if 'alt' in attrs:
                string = attrs['alt'].strip()
                del attrs['alt']

                if name == 'img' and string.lower() in GREEK_LOWER:
                    if string in GREEK_UPPER: string = GREEK_UPPER[string]
                    else: string = GREEK_LOWER[string.lower()]
            else:
                string = attrs['title'].strip()
                del attrs['title']

            self._string.append(normalize('NFC', string))
        else:
            self._string.append(HtmlExtractor.OBJECT_REPLACEMENT)

    def _addTag(self, name:str, start:int, stop:int, attrs:dict):
        if any(a in HtmlExtractor.SKIPPED_ATTRIBUTES for a in attrs):
            # clean up attributes
            for a in HtmlExtractor.SKIPPED_ATTRIBUTES:
                if a in attrs: del attrs[a]

        if start != stop or attrs:
            # only add tags that have content or attributes
            if start != stop: offsets = (start, stop)
            else: offsets = (start,)

            if name in HtmlExtractor.NORMAL_NAME:
                # normalize tag names
                name = HtmlExtractor.NORMAL_NAME[name]

            self._setTag((self.namespace, name, offsets), attrs)

    def _setTag(self, tag:tuple, attrs:dict):
        if tag in self.tags:
            self.tags[tag].update(attrs)
        else:
            self.tags[tag] = attrs

    def _shortenTags(self, max_offset:int):
        for tag in list(self.tags.keys()):
            if tag[2][-1] > max_offset:
                if tag[2][0] >= max_offset: # entire tag shortened to no length
                    if self.tags[tag]: # has attributes -> maintain tag
                        new = (tag[0], tag[1], (max_offset,))
                        attrs = self.tags[tag]
                        self._setTag(new, attrs)
                else:
                    new = (tag[0], tag[1], (tag[2][0], max_offset))
                    attrs = self.tags[tag]
                    self._setTag(new, attrs)

                del self.tags[tag]

    def close(self):
        """
        Tell the parser the feed has ended and clean up the rightmost
        whitespaces.
        """
        HTMLParser.close(self)
        string = ''.join(self._string)

        if string and HtmlExtractor.RSTRIP_REGEX.search(string):
            # clean up those rightmost whitespaces:
            self._string = [string.rstrip()]
            self._shortenTags(self.position)

    def feed(self, data:str):
        """
        Feed some data to the parser.

        Can be called multiple times and feeding must be terminated with a
        call to :meth:`.close`.

        :param data: A string containing HTML.
        """
        HTMLParser.feed(self, data)

    def reset(self):
        """
        Reset the parser for feeding a new document.
        """
        HTMLParser.reset(self)
        self._string = []
        self._elements = []
        self._ignored = []
        self.tags = dict()

    @property
    def string(self) -> str:
        """
        The string representation of the text extracted from the document.
        """
        if self._elements or self._ignored:
            raise HTMLParseError('incomplete parse')
        
        return ''.join(self._string)

    @property
    def position(self) -> int:
        return sum(len(s) for s in self._string)

    def handle_charref(self, ref:str):
        if not self._ignored:
            try:
                codepoint = int(ref[1:], 16) if ref[0].lower() == 'x' else \
                            int(ref)
                self._string.append(chr(codepoint))
            except (ValueError, OverflowError):
                self.L.warn('HTML char ref &#%s; not a valid codepoint', ref)
                self._string.append(HtmlExtractor.REPLACEMENT)

    def handle_comment(self, data:str):
        pass

    def handle_decl(self, decl:str):
        pass

    def handle_endtag(self, name:str):
        if self._ignored:
            check = self._ignored.pop()
            assert name == check
        else:
            check, start, tag_type, attrs = self._elements.pop()

            if name != check:
                name = 'expected to close {}, got {}'.format(check, name)
                raise HTMLParseError(name)

            stop = self.position

            if start != stop:
                if tag_type == HtmlExtractor.MINOR:
                    if self._string and self._string[-1][-1] != '\n':
                        self._string.append('\n')
                        stop += 1
                elif tag_type == HtmlExtractor.CONTENT:
                    stop += self._addContentBreak()

            self._addTag(name, start, stop, attrs)


    def handle_entityref(self, ref:str):
        if not self._ignored:
            try:
                self._string.append(entitydefs[ref.lower()])
            except KeyError:
                self.L.warn('HTML entity ref &%s; unknown', ref)
                self._string.append(HtmlExtractor.REPLACEMENT)


    def handle_data(self, data:str):
        if not self._ignored:
            data = HtmlExtractor.WS_REGEX.sub(' ', data)

            if not self._string or \
               HtmlExtractor.RSTRIP_REGEX.search(self._string[-1]):
                data = data.lstrip()
            
            if data: self._string.append(normalize('NFC', data))

    def handle_pi(self, data:str):
        pass

    def handle_startendtag(self, name:str, attrs:list):
        if not self._ignored:
            try:
                tag_type = HtmlExtractor.ELEMENTS[name]
            except KeyError:
                self.L.warn('ignoring unknown element "{}"'.format(name))
            else:
                if tag_type != HtmlExtractor.IGNORE:
                    start = self.position
                    attrs = dict(attrs)

                    if name in ('img', 'area'):
                        self._addImgOrArea(name, attrs)
                    elif name == 'br':
                        self._string.append('\n')
                    elif name == 'hr':
                        self._string.append('\n\n')

                    self._addTag(name, start, self.position, attrs)

    def handle_starttag(self, name:str, attrs:tuple):
        if name in HtmlExtractor.EMPTY_ELEMENTS:
            return self.handle_startendtag(name, attrs)

        try:
            tag_type = self.ELEMENTS[name]
        except KeyError:
            self.L.warn('ignoring unknown element "{}"'.format(name))
            tag_type = HtmlExtractor.IGNORE

        if self._ignored:
            self._ignored.append(name)
        elif tag_type == HtmlExtractor.IGNORE:
            self._ignored.append(name)
        else:
            start = self.position
            self._elements.append((name, start, tag_type, dict(attrs)))

    def unknown_decl(self, data:str):
        pass
