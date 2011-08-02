"""
.. py:module:: corpus
   :synopsis: Read GENIA XML files.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from io import TextIOBase
from libfnl.nlp.text import Text
from libfnl.nlp.penn import AMBIGUITY_SEP, AMBIGUOUS, TAGSET, REMAPPED
import logging
from xml.etree.ElementTree import iterparse, Element

DROPPED_TOKENS = frozenset('*')
"""
Used in the corpus to mark tokens dropped by the tagger.

As this destroys the correct sequence dependency of tags, sentences where these
tags occur are dropped.
"""

REMAPPED_GENIA = {
    "-": "--", # They use '-' as the dash tag, but Penn rules are to use '--'
    "CT": "DT", # funny use of special determiner, 4x in corpus
    "XT": "DT", # even more peculiar use, only once, on the DT token "a"
    "N": "NN", # probably an error, committed once, on "CD80"
    "PP": "PRP$", # probably an error on possessive use of "ours", once
}
"""
Mapping of erroneous Penn tags in the GENIA corpus to valid Penn tags.
"""

class Reader:
    """
    Read GENIA PoS XML files.
    """

    L = logging.getLogger("Reader")

    def __init__(self, section_ns="genia", pos_tag_ns="penn",
                 token_element="w", pos_attribute="c",
                 sentence_element="sentence", title_element="title",
                 abstract_element="abstract", article_element="article",
                 article_id_path="articleinfo/bibliomisc"):
        """
        :param section_ns: The tag namespace to use for the article sections
            (abstract, sentence, and title elements).
        :param pos_tag_ns: The tag namespace to use for the PoS tags (token
            elements).
        :param token_element: The name of the XML element containing a (PoS)
            token.
        :param pos_attribute: The name of the *token_element*'s attribute that
            contains the (Penn) PoS tag ID.
        :param sentence_element: The name of the XML element containing a
            sentence.
        :param title_element: The name of the XML element containing the
            article's title.
        :param abstract_element: The name of the XML element containing the
            article's abstract.
        :param article_element: The name of the XML element containing an
            article.
        :param article_id_path: The path to the XML element containing the
            article ID starting from the article element.
        """
        self.pos_tag_ns = pos_tag_ns
        self.pos_tags = None # will be a list of PoS tags
        self.section_tag_ns = section_ns
        self.section_tags = None # will a list of sentence tags
        self.abstract_elem = abstract_element
        self.article_elem = article_element
        self.pos_attr = pos_attribute
        self.sentence_elem = sentence_element
        self.title_elem = title_element
        self.token_elem = token_element
        self.article_id_path = article_id_path

    def toText(self, stream:TextIOBase) -> iter([Text]):
        """
        Read an open XML stream, yielding article ID, :class:`.Text` instance
        tuples, one per article.

        The PoS attributes on the XML token elements are used to create tags on
        the text, using the Penn tag name as tag IDs. The start and end
        positions of the title, abstract, and sentences are stored in the
        section tag namespace, using their XML element name as tag ID.
        """
        for event, element in iterparse(stream, events=('end',)):
            if element.tag == self.article_elem:
                self.article = []
                self.section_tags = []
                self.pos_tags = []

                length = self._parseArticle(element)

                if length:
                    text = Text(''.join(self.article))
                    text.add(self.section_tags, self.section_tag_ns)
                    text.add(self.pos_tags, self.pos_tag_ns)
                    article_id = element.find(self.article_id_path)
                    yield article_id.text.strip(), text

    def _parseArticle(self, element:Element) -> int:
        # Returns the length of the article, all partial strings of the article
        # in :attr:`.article`, and sets the tags on :attr:`.tags`.
        offset = 0

        for section_name in (self.title_elem, self.abstract_elem):
            section = element.find(section_name)

            if element is not None:
                if self.article: offset += 1
                start = offset
                offset, section = self._parseSection(section, offset)

                if section:
                    if self.article: self.article.append("\n")
                    self.article.extend(section)
                    tag = (self.section_tag_ns, section_name, (start, offset))
                    self.section_tags.append((tag, None))
                elif self.article:
                    offset -= 1

        return offset

    def _parseSection(self, element:Element, offset:int) -> int:
        # Returns the final *offset* for this section *element* and the list
        # of partial strings for this section.
        sentences = list(element.findall(self.sentence_elem))
        increment = 0
        section = []

        for sentence in sentences:
            offset, sentence = self._parseSentence(sentence, offset, increment)

            if sentence:
                section.append(" " * increment)
                increment = 1
                section.extend(sentence)

        return offset, section

    def _parseSentence(self, element:Element, offset:int, inc:int) -> int:
        # Returns the final *offset* for this sentence *element*, and list of
        # partial strings for this sentence.
        # If a sentence will later be separated by whitespace from the
        # previous sentences, the length of that whitespace token should be
        # indicated by *inc*.
        start = offset
        words = list(element.findall(self.token_elem))
        offset, sentence = self._analyzeWords(words, offset, inc)

        if sentence:
            start += inc
            tag = (self.section_tag_ns, self.sentence_elem, (start, offset))
            self.section_tags.append((tag, None))

        return offset, sentence

    def _analyzeWords(self, elements:list([Element]), offset:int,
                      inc:int) -> int:
        # Returns the final *offset* for the word *elements*, and list of
        # partial strings for this list of words.
        # If a sentence will later be separated by whitespace from a
        # previous sentences, the length of that whitespace token should be
        # indicated by *inc*.
        words = []
        tags = list(self._splitAmbiguousTags(elements))
        assert all(len(ts) for ts in tags), tags

        # Skip any sentences where words have bad tags that cannot be fixed
        if any(any(tag not in TAGSET for tag in tagset) for tagset in tags):
            # and report, except those only with a DROPPED_TOKENS tag
            # unless logging is DEBUG, in which case even those are reported
            if self.L.isEnabledFor(logging.WARN):
                unknown_tags = []
                debug = self.L.isEnabledFor(logging.DEBUG)

                for idx, tagset in enumerate(tags):
                    for tag in tagset:
                        if tag not in TAGSET:
                            if debug or tag not in DROPPED_TOKENS:
                                text = elements[idx].text
                                tok_tag = "{}/{}".format(text, tag)
                                unknown_tags.append(tok_tag)

                if unknown_tags:
                    self.L.warning("skipping %s", ', '.join(unknown_tags))
                    self.L.info("skipped sentence: '%s'", ''.join(
                        '{}{}'.format(w.text, w.tail if w.tail else '')
                        for w in elements
                    ))
        else:
            offset += inc

            for idx, word in enumerate(elements):
                if word.text:
                    if word.text == "n't":
                        start = None
                        offset += 3
                        words.append(word.text)

                        if len(tags[idx - 1]) > 1: self.pos_tags.pop()

                        for _ in tags[idx - 1]:
                            tag = self.pos_tags.pop()
                            start = tag[0][2][0]

                        for tag in tags[idx - 1]:
                            t = (self.pos_tag_ns, tag, (start, offset))
                            self.pos_tags.append((t, None))

                        if len(tags[idx - 1]) > 1:
                            t = (self.pos_tag_ns, AMBIGUOUS, (start, offset))
                            self.pos_tags.append((t, None))
                    else:
                        start = offset
                        offset += len(word.text)
                        words.append(word.text)

                        for tag in tags[idx]:
                            if tag in REMAPPED: tag = REMAPPED[tag]
                            t = (self.pos_tag_ns, tag, (start, offset))
                            self.pos_tags.append((t, None))

                        if len(tags[idx]) > 1:
                            t = (self.pos_tag_ns, AMBIGUOUS, (start, offset))
                            self.pos_tags.append((t, None))

                if word.tail:
                    words.append(word.tail)
                    offset += len(word.tail)

            if not words:
                offset -= inc
        
        return offset, words

    def _splitAmbiguousTags(self, elements:list([Element])) -> iter:
        # Split word tag PoS tokens into a tuples of all PoS tokens annotated
        # on each word.
        # The tuple has one value only if an unambiguous assignment, and all
        # PoS tags for ambiguous tags.
        # Ambiguous PoS tags means that attribute ``c`` is, fe., ``"JJ|VBN"``
        for w in elements:
            pos_tag = w.attrib[self.pos_attr]

            if AMBIGUITY_SEP in pos_tag:
                yield tuple((t if t not in REMAPPED_GENIA else
                             REMAPPED_GENIA[t])
                            for t in pos_tag.split(AMBIGUITY_SEP)
                            if t not in DROPPED_TOKENS)
            else:
                if pos_tag in REMAPPED_GENIA: pos_tag = REMAPPED_GENIA[pos_tag]
                yield (pos_tag,)


