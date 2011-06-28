"""
.. py:module:: corpus
   :synopsis: Read GENIA XML files.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
"""
from collections import defaultdict
from io import TextIOBase
from libfnl.nlp.text import Unicode
import logging
from xml.etree.ElementTree import iterparse, Element

PENN_TAGSET = frozenset({
    "CC", # Coordinating conjunction e.g. and,but,or...
    "DT", #	Determiner 
    "EX", # Existential there 
    "FW", # Foreign word
    "IN", # Preposision or subordinating conjunction 
    "JJ", # Adjective 
    "JJR", # Adjective, comparative 
    "JJS", # Adjective, superlative
    "MD", # Modal e.g. can, could, might, may...
    "NN", # Noun, singular or mass 
    "NNP", # Proper noun, singular
    "NNPS", # Proper noun, plural
    "NNS", # Noun, plural 
    "PDT", # Predeterminer e.g. all, both ... when they precede an article
    "POS", # Possessive Ending e.g. Nouns ending in 's
    "PRP", # Personal Pronoun e.g. I, me, you, he...
    "PRP$", # Possessive Pronoun e.g. my, your, mine, yours...
    "RB", # Adverb, most words that end in -ly as well as degree words like quite, too and very
    "RBR", # Adverb, comparative; Adverbs with the comparative ending -er, with a strictly comparative meaning.
    "RBS", # Adverb, superlative 
    "RP", # Particle 
    "TO", # to 
    "UH", # Interjection e.g. uh, well, yes, my...
    "VB", # Verb, base form; subsumes imperatives, infinitives and subjunctives
    "VBD", # Verb, past tense; includes the conditional form of the verb to be
    "VBG", # Verb, gerund or persent participle 
    "VBN", # Verb, past participle 
    "VBP", # Verb, non-3rd person singular present 
    "VBZ", # Verb, 3rd person singular present 
    "WDT", # ", # Wh-determiner e.g. which, and that when it is used as a relative pronoun
    "WP", # Wh-pronoun e.g. what, who, whom...
    "WP$", # Possessive wh-pronoun
    "WRB", # Wh-adverb e.g. how, where, why
    "CD", # Cardinal Number
    "LS", # List Item Marker 
    "SYM", # Symbol; incl. mathematical, scientific or technical symbols, and abbrev. marks
    "$", # Currency symbols
    "``", # Opening quotation mark
    "''", # Closing quotation mark
    "(", # Opening parentheses
    ")", # Closing parentheses
    ",", # Comma
    ".", # Sentence terminal (.?! and possibly ;:); if abbreviation ., use SYM, or join . with the token's tag
    ":", # Non-sentence terminal use of ;:/
})
"""
The list of accepted tags, ie., the exact Penn tagset.
"""

# To make for better keys or remapping of "wrong" GENIA tags:
REMAPPED_TAGS = {
    "PRP$": "PPRP",
    "WP$": "PWP",
    "$": "CUR",
    "``": "Q_O",
    "''": "Q_C",
    "(": "P_O",
    ")": "P_C",
    ",": "COMMA",
    ".": "STOP",
    ":": "PUNC",
}
"""
Mapping of tags consisting of symbol character in the Penn tagset to letter
characters that are more versatile in usage/handling.
"""

# Any sentences containing these tags will be skipped:
KNOWN_PROBLEM_TAGS = PENN_TAGSET.union({
    '*', # Used when the GENIA tagger dropped the token. As this destroys the
         # correct sequence dependency of tags, sentences where any token
         # uses this tag are dropped.
})
"""
Tags that are not correct Penn Tags; Any sentences containing these tags are
dropped from the parsed corpus.
"""

class CorpusReader:
    """
    Read PoS XML files.
    """

    L = logging.getLogger("CorpusReader")

    def __init__(self, namespace="genia", pos_tag_ns="penn", token_tag="w",
                 sentence_tag="sentence", title_tag="title",
                 abstract_tag="abstract", article_tag="article"):
        self.namespace = namespace
        self.pos_tag_ns = pos_tag_ns
        self.token_tag = token_tag
        self.sentence_key = sentence_tag
        self.title_key = title_tag
        self.abstract_key = abstract_tag
        self.article_tag = article_tag

    def toUnicode(self, stream:TextIOBase) -> iter([Unicode]):
        for event, element in iterparse(stream, events=("end",)):
            if element.tag == self.article_tag:
                self.article = []
                self.tags = {
                    self.namespace: {
                        self.sentence_key: [],
                        self.title_key: [],
                        self.abstract_key: [],
                    },
                    self.pos_tag_ns: defaultdict(list)
                }
                self.pos_tags = self.tags[self.pos_tag_ns]
                self.sentence_tags = self.tags[self.namespace][self.sentence_key]
                
                length = self._parseArticle(element)

                if length:
                    text = Unicode(''.join(self.article))
                    assert len(text) == length
                    text.tags = self.tags
                    yield text

    def _parseArticle(self, element:Element) -> int:
        offset = 0

        for section_name in (self.title_key, self.abstract_key):
            section = element.find(section_name)

            if element is not None:
                if self.article: offset += 1
                start = offset
                offset, section = self._parseSection(section, offset)

                if section:
                    if self.article: self.article.append("\n")
                    self.article.extend(section)
                    self.tags[self.namespace][section_name] = [(start, offset)]
                elif self.article:
                    offset -= 1

        return offset

    def _parseSection(self, element:Element, offset:int) -> int:
        sentences = list(element.findall(self.sentence_key))
        increment = 0
        section = []

        for sentence in sentences:
            offset, sentence = self._parseSentence(sentence, offset, increment)

            if sentence:
                section.append(" " * increment)
                increment = 1
                section.extend(sentence)

        return offset, section

    def _parseSentence(self, element:Element, offset:int, increment:int) -> int:
        start = offset
        words = list(element.findall(self.token_tag))
        offset, sentence = self._analyzeWords(words, offset, increment)

        if sentence:
            start += increment
            self.sentence_tags.append((start, offset))

        return offset, sentence

    def _analyzeWords(self, elements:list([Element]), offset:int, increment:int) -> int:
        words = []

        # Skip any sentences where words have bad tags that cannot be fixed
        if any(map(lambda w: w.attrib["c"] not in PENN_TAGSET, elements)):
            unknown_tags = ", ".join(
                "%s/%s" % (w.text, w.attrib["c"]) for w in elements
                if w.attrib['c'] not in KNOWN_PROBLEM_TAGS
            )
            if unknown_tags: self.L.info("Skipping %s", unknown_tags)
        else:
            offset += increment
            last_tag = None

            for word in elements:
                if word.text:
                    if word.text == "n't":
                        start, _ = self.pos_tags[last_tag].pop()
                        offset += 3
                        words.append(word.text)
                        self.pos_tags[last_tag].append((start, offset))
                    else:
                        start = offset
                        offset += len(word.text)
                        words.append(word.text)
                        penn_tag = word.attrib["c"]

                        if penn_tag in REMAPPED_TAGS:
                            penn_tag = REMAPPED_TAGS[penn_tag]

                        self.pos_tags[penn_tag].append((start, offset))
                        last_tag = penn_tag

                if word.tail: # is not None:
                    words.append(word.tail)
                    offset += len(word.tail)

            if not words:
                offset -= increment
        
        return offset, words


