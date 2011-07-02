"""
.. py:module:: corpus
   :synopsis: Read GENIA XML files.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from collections import defaultdict
from io import TextIOBase
from libfnl.nlp.text import Unicode
from libfnl.nlp.penn import AMBIGUITY_SEP, AMBIGUOUS, TAGSET, REMAPPED
import logging
from xml.etree.ElementTree import iterparse, Element

DROPPED_TOKENS = '*'
"""
Used in the corpus to mark tokens dropped by the tagger.

As this destroys the correct sequence dependency of tags, sentences where this
tag is occurs are dropped.
"""

REMAPPED_GENIA = {
    "-": "--", # They use '-' as the dash tag, but Penn rules are to use '--'
    "CT": "DT", # funny use of special determiner, 4x in corpus
    "XT": "DT", # even more peculiar use, only once, on an "a" DT token
    "N": "NN", # probably an error, committed once, on "CD80"
    "PP": "PRP$", # probably an error on possessive use of "ours", once
}
"""
Mapping of non-existing Penn tags in the GENIA corpus to valid Penn tags.
"""

class Reader:
    """
    Read GENIA PoS XML files.
    """

    L = logging.getLogger("Reader")

    def __init__(self, section_ns="section", pos_tag_ns="penn",
                 token_tag="w", pos_attribute="c",
                 sentence_tag="sentence", title_tag="title",
                 abstract_tag="abstract", article_tag="article"):
        """
        :param section_ns: The tag namespace for the article section tags.
        :param pos_tag_ns: The tag namespace for the PoS tags.
        :param token_tag: The name of the XML tag containing a (PoS) token.
        :param pos_attribute: The name of the *token tag*'s attribute that
            contains the PoS tag.
        :param sentence_tag: The name of the XML tag containing a sentence.
        :param title_tag: The name of the XML tag containing a title.
        :param abstract_tag: The name of the XML tag containing an abstract.
        :param article_tag:  The name of the XML tag containing an article.
        """
        self.section_ns = section_ns
        self.pos_tag_ns = pos_tag_ns
        self.pos_tags = None # will be: { pos_tag: [(start, end)] }
        self.token_tag = token_tag
        self.pos_attr = pos_attribute
        self.sentence_tag = sentence_tag
        self.sentence_tags = None # will be: [(start, end)]
        self.title_tag = title_tag
        self.abstract_tag = abstract_tag
        self.article_tag = article_tag

    def toUnicode(self, stream:TextIOBase) -> iter([Unicode]):
        """
        Read an open XML stream, yielding :class:`.Unicode` text instances,
        one per article.

        The PoS attributes on the XML token tags are used to create tags on
        the text, using the Penn tag name as keys. The start and end positions
        of sections (title, abstract) and sentences are stored in the section
        namespace, keyed by their XML tag name (ie., "title", "abstract", and
        "sentence").
        """
        for event, element in iterparse(stream, events=("end",)):
            if element.tag == self.article_tag:
                self.article = []
                self.tags = {
                    self.section_ns: {
                        self.sentence_tag: [],
                    },
                    self.pos_tag_ns: defaultdict(list)
                }
                self.pos_tags = self.tags[self.pos_tag_ns]
                self.sentence_tags = \
                    self.tags[self.section_ns][self.sentence_tag]
                
                length = self._parseArticle(element)

                if length:
                    text = Unicode(''.join(self.article))
                    assert len(text) == length
                    text.tags = self.tags
                    yield text

    def _parseArticle(self, element:Element) -> int:
        # Returns the length of the article, all partial strings of the article
        # in :attr:`.article`, and sets the tags on :attr:`.tags`.
        offset = 0

        for section_name in (self.title_tag, self.abstract_tag):
            section = element.find(section_name)

            if element is not None:
                if self.article: offset += 1
                start = offset
                offset, section = self._parseSection(section, offset)

                if section:
                    if self.article: self.article.append("\n")
                    self.article.extend(section)
                    self.tags[self.section_ns][section_name] = [(start, offset)]
                elif self.article:
                    offset -= 1

        return offset

    def _parseSection(self, element:Element, offset:int) -> int:
        # Returns the final *offset* for this section *element* and the list
        # of partial strings for this section.
        sentences = list(element.findall(self.sentence_tag))
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
        words = list(element.findall(self.token_tag))
        offset, sentence = self._analyzeWords(words, offset, inc)

        if sentence:
            start += inc
            self.sentence_tags.append((start, offset))

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
                            if debug or tag != DROPPED_TOKENS:
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
                        offset += 3
                        words.append(word.text)

                        for tag in tags[idx - 1]:
                            start, _ = self.pos_tags[tag].pop()
                            self.pos_tags[tag].append((start, offset))

                        if len(tags[idx - 1]) > 1:
                            start, _ = self.pos_tags[AMBIGUOUS].pop()
                            self.pos_tags[AMBIGUOUS].append((start, offset))
                    else:
                        start = offset
                        offset += len(word.text)
                        words.append(word.text)

                        for tag in tags[idx]:
                            if tag in REMAPPED:
                                tag = REMAPPED[tag]

                            self.pos_tags[tag].append((start, offset))

                        if len(tags[idx]) > 1:
                            self.pos_tags[AMBIGUOUS].append((start, offset))

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
                            if t != DROPPED_TOKENS)
            else:
                if pos_tag in REMAPPED_GENIA: pos_tag = REMAPPED_GENIA[pos_tag]
                yield (pos_tag,)


