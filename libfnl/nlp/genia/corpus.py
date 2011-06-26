"""
.. py:module:: corpus
   :synopsis: Read GENIA XML files.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
"""
from collections import defaultdict
from io import StringIO, TextIOBase
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

# To make for better keys or remapping of "wrong" GENIA tags:
REMAPPED_TAGS = {
    "$": "CUR",
    "``": "Q_O",
    "''": "Q_C",
    "(": "P_O",
    ")": "P_C",
    ",": "COMMA",
    ".": "STOP",
    ":": "PUNC",
}

# Any sentences containing these tags will be skipped:
KNOWN_PROBLEM_TAGS = PENN_TAGSET.union({
    '*',
})

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
        self.article_key = article_tag

    def toUnicode(self, stream:TextIOBase, offset:int=0) -> Unicode:
        self.str_buffer = StringIO()
        self.pos_tags = defaultdict(list)
        self.sentence_tags = []
        self.abstract_tags = []
        self.title_tags = []
        self.article_tags = []
        self._parse(stream, offset)
        text = Unicode(self.str_buffer.getvalue())

        for key, tags in [
            (self.sentence_key, self.sentence_tags),
            (self.abstract_key, self.abstract_tags),
            (self.title_key, self.title_tags),
            (self.article_key, self.article_tags)
        ]:
            for offsets in tags:
                text.addTag(self.namespace, key, offsets)

        for key, tags in self.pos_tags.items():
            text.addOffsets(self.pos_tag_ns, key, tags)

        return text

    def _parse(self, stream:TextIOBase, offset:int):
        for event, element in iterparse(stream, events=("end",)):
            if element.tag == self.article_key:
                offset = self._parseArticle(element, offset)

    def _parseArticle(self, element:Element, offset:int) -> int:
        start = offset

        for section_name in (self.title_key, self.abstract_key):
            section = element.find(section_name)
            if section is not None: offset = self._parseSection(section, offset)

        return self._store(self.article_tags, start, offset)

    def _parseSection(self, element:Element, offset:int) -> int:
        start = offset

        for sentence in element.findall(self.sentence_key):
            offset = self._parseSentence(sentence, offset)

        tagset = self.abstract_tags if element.tag == self.abstract_key else \
                 self.title_tags
        return self._store(tagset, start, offset)

    def _parseSentence(self, element:Element, offset:int) -> int:
        start = offset
        words = list(element.findall(self.token_tag))
        offset = self._analyzeWords(words, offset)
        return self._store(self.sentence_tags, start, offset, " ")

    def _store(self, collection, start, offset, separator="\n"):
        if offset != start:
            collection.append((start, offset))
            self.str_buffer.write(separator)
            offset += 1

        return offset

    def _analyzeWords(self, elements:list([Element]), offset:int) -> int:
        # Skip any sentences where words have bad tags that cannot be fixed
        if any(map(lambda w: w.attrib["c"] not in PENN_TAGSET, elements)):
            unknown_tags = ", ".join(
                "%s/%s" % (w.text, w.attrib["c"]) for w in elements
                if w.attrib['c'] not in KNOWN_PROBLEM_TAGS
            )
            if unknown_tags: self.L.info("Skipping %s", unknown_tags)
        else:
            for word in elements:
                start = offset
                self.str_buffer.write(word.text)
                offset += len(word.text)
                penn_tag = word.attrib["c"]

                if penn_tag in REMAPPED_TAGS:
                    penn_tag = REMAPPED_TAGS[penn_tag]

                self.pos_tags[penn_tag].append((start, offset))

                if word.tail: # is not None:
                    self.str_buffer.write(word.tail)
                    offset += len(word.tail)
        
        return offset


