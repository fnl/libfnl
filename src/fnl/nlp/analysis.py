import logging
from unicodedata import category
from unidecode import unidecode
from fnl.nlp.dictionary import Dictionary
from fnl.nlp.strtok import Category
from fnl.text.symbols import LATIN
from fnl.text.token import Token


class TextAnalytics:
    """
    A toolset to annotate text with multiple entity taggers and dictionaries using PoS an phrases.

    An instance needs to be configured by setting a "default" text tokenizer
    (but all taggers can use their own tokenization technique),
    a specific PoS/phrase tagger, and as many NER taggers and dictionaries as desired.
    I.e., the tokenizer and PoS tagger must be set, while NER taggers and dictionaries may be
    omitted.
    """

    logger = logging.getLogger("TextAnalytics")

    def __init__(self, tokenizer, pos_tagger, tag_all_nouns=0, use_greek_letters=False):
        """
        Create a new text analytics instance.

        :param tokenizer: the tokenizer instance to use
        :param pos_tagger: the PoS tagger instance to use
        :param tag_all_nouns: all tokens in noun phrases (and not just named entity tokens) should
               be tagged (integer, indicating for up to which dictionary this should be done:
               e.g., if three dictionaries are added and this value is set to 1, only for the
               first dictionary nouns will be matched, too)
        :param use_greek_letters: do not expand/regularize Greek letters to their Latin words
        """
        self.tag_all_nouns = tag_all_nouns
        self.use_greek_letters = use_greek_letters
        self._ner_dictionaries = []
        self._ner_taggers = []
        self._pos_tagger = pos_tagger
        self._tokenizer = tokenizer

    def addDictionary(self, d):
        """Add a[nother] dictionary for normalizing tokens in this instance."""
        self._ner_dictionaries.append(d)

    def addNerTagger(self, t):
        """Add an[other] entity tagger for this instance."""
        return self._ner_taggers.append(t)

    @property
    def pos_tagger(self):
        """The PoS [and phrase] tagger for this instance."""
        return self._pos_tagger

    @property
    def tokenizer(self):
        """The text tokenizer for this instance."""
        return self._tokenizer

    def analyze(self, text):
        """
        Analyze a piece of text using the configured tokenizer, dictionary, and taggers.

        Most commonly, a piece of text is a sentence, but this depends on the used taggers.

        :return a triple of (tokens, [ner_tags..], [normalizations...]);
                if no NER tagger was set, the PoS tagger's tags are returned.
        """
        # TOKENIZATION
        if not self.use_greek_letters:
            text = ''.join(LATIN[c] if c in LATIN else c for c in text)

        tokens = list(self.tokenizer.split(text))

        # POS TAGGING
        self.pos_tagger.send(text)
        part_of_speech = list(self.pos_tagger)

        # NER TAGGING
        ner_tags = [] if self._ner_taggers else [part_of_speech, ]

        for tagger in self._ner_taggers:
            tagger.send(part_of_speech)
            entities = list(tagger)

            if len(entities) != len(tokens):
                entities = self._alignToTokens(entities, tokens)

            ner_tags.append(entities)

        # DICTIONARY NORMALIZATION
        mappings = [list(d.walk(tokens)) for d in self._ner_dictionaries]

        # ALIGN NER TAGS AND NORMALIZATIONS
        normalizations = [
            list(self._matchMappingToNerTags(m, ner_tags, i)) for i, m in enumerate(mappings)
        ]

        return tokens, ner_tags, normalizations

    def _alignToTokens(self, tags, tokens):
        """
        Align the tags to the tokens.
        """
        # in this code, each token to align to is called a "word"
        aligned_tags = []
        t_iter = iter(tokens)
        index = 0  # of the tag currently being aligned
        skipDashes = chr(Category.Pd) in self.tokenizer.skipOrthos

        while index < len(tags):
            word = next(t_iter)
            tag = tags[index]

            while skipDashes and all(category(c) == "Pd" for c in tag.word) and index < len(tags):
                self.logger.debug('dropping dash "%s" [%s]', tag.word, tag[-1])
                index += 1
                tag = tags[index]

            if word == '"' and tag.word in ("``", "''"):
                # " is a special case (gets converted to `` or '' by GENIA)
                aligned_tags.append(Token('"', *tag[1:]))
            elif tag.word == unidecode(word):
                if tag.word == word:
                    aligned_tags.append(tag)
                else:
                    aligned_tags.append(Token(word, *tag[1:]))
            elif len(word) > len(tag.word):
                if tags[index + 1].word == "n't":
                    index += 1
                    tag = tag.replace(word=tag.word + "n't")
                    aligned_tags.extend(self._alignBySplittingToken(tag, word, t_iter))
                else:
                    index, aligned_tag = self._alignByJoiningTokens(tag, word, index, tags)
                    aligned_tags.append(aligned_tag)
            elif len(word) < len(tag.word):
                aligned_tags.extend(self._alignBySplittingToken(tag, word, t_iter))
            else:
                try:
                    next_word = next(t_iter)

                    if tag.word == unidecode(next_word):
                        rescue = Token(word, word, *tags[index-1][2:])
                        self.logger.info(
                            "word '%s' not recognized by tagger (probably due to NERSuite's "
                            "shortcoming of only working with ASCII); assigning it the "
                            "last token: %s", word, repr(rescue))
                        aligned_tags.append(rescue)
                        aligned_tags.append(tag)
                    else:
                        raise AssertionError('cannot rescue with next word "%s"' % next_word)
                except:
                    raise RuntimeError('no alignment of tag %s to word "%s" found' % (repr(tag), word))

            index += 1

        assert len(tokens) == len(aligned_tags) and tokens == [t.word for t in aligned_tags], \
                "tag2token alignment failed (%i != %i); details: %s" % (
                    len(tokens), len(aligned_tags), repr([
                        (w, t) for w, t in
                        zip(tokens, [t.word for t in aligned_tags]) if w != t
                    ])
                )
        return aligned_tags

    def _alignByJoiningTokens(self, tag, word, index, tags):
        # alignment helper
        self.logger.debug('word %s exceeds tag %s', repr(word), repr(tag.word))
        tag_words = [tag.word]
        ascii = unidecode(word)
        aligned = lambda: ascii == ''.join(tag_words)
        max_len = len(word)

        while not aligned() and sum(map(len, tag_words)) < max_len:
            index += 1

            if index < len(tags):
                tag_words.append(tags[index].word)
            else:
                self.logger.warning('illegal index offset error prevented')
                break

        if aligned():
            self.logger.debug('dropping tags "%s" and adding %s [%s]',
                              ' '.join(tag_words), repr(word), tag[-1])
            return index, Token(word, ascii, *tag[2:])
        else:
            raise RuntimeError('alignment of tokens %s to word "%s" as "%s" at %i failed' % (
                    repr(tag_words), word, ascii, index
            ))

    def _alignBySplittingToken(self, tag, word, t_iter):
        # alignment helper
        self.logger.debug('tag %s exceeds word %s', repr(tag.word), repr(word))
        tmp = list(tag)
        words = [word]
        asciis = [unidecode(word).replace('-', '')]
        tag_word = ''.join(self.tokenizer.split(tag.word))
        aligned = lambda: ''.join(asciis) == tag_word
        max_len = len(tag_word)
        aligned_tags = []

        while not aligned() and sum(map(len, asciis)) < max_len:
            words.append(next(t_iter))
            asciis.append(unidecode(words[-1]).replace('-', ''))

        if aligned():
            self.logger.debug('dropping tag %s [%s] for words "%s"',
                              repr(tag.word), tag[-1], ' '.join(words))

            for w, a in zip(words, asciis):
                tmp[0] = w
                tmp[1] = a
                self.logger.debug('adding tag %s [%s]', repr(w), tmp[-1])
                aligned_tags.append(Token(*tmp))

                for p in (3, 4):
                    if tmp[p].startswith('B-'):
                        tmp[p] = 'I' + tmp[p][1:]
        else:
            raise RuntimeError('alignment of words %s as %s to token "%s" as "%s" failed' % (
                repr(words), repr(asciis), tag.word, tag_word
            ))

        return aligned_tags

    def _matchMappingToNerTags(self, mapping, ner_tokens, didx):
        """
        Accept and yield dictionary tags if the mapping at the
        token has any entity tag annotation [or is a noun (phrase)].
        """
        self.logger.debug('assigning dictionary tags %s', mapping)
        assert len(mapping) == len(ner_tokens[0]), "%i != %i; details: %s" % (
                len(mapping), len(ner_tokens[0]),
                repr(list(zip([t.word for t in ner_tokens[0]], mapping)))
        )
        last_tag = None  # the last tag seen:
        # to determine if the yielded tag should be an open tag (B) or not (I)
        correctTag = lambda tag: tag if (tag[2:] == last_tag or tag[:2] == Dictionary.B) else \
                Dictionary.B % tag[2:]

        for tag, *tokens in zip(mapping, *ner_tokens):
            if tag != Dictionary.O:
                if any(t.entity != Dictionary.O for t in tokens):
                    # an entity-based assignment should be made
                    yield correctTag(tag)
                    last_tag = tag[2:]
                elif self.tag_all_nouns > didx and tokens[0].pos.startswith('NN') or (
                        tokens[0].pos.startswith('JJ') and tokens[0].chunk.endswith('-NP')
                        # another alternative would be to also allow tagging CDs in noun phrases:
                        # tokens[0].chunk.endswith('-NP') and tokens[0].pos[:2] in ('JJ', 'CD')
                ):
                    # a noun-[phrase]-based assignment (to a noun or NP adjective) should be made
                    yield correctTag(tag)
                    last_tag = tag[2:]
                else:
                    self.logger.debug('dropping normalization of "%s" with %s', tokens[0].word,
                                      tag)
                    yield Dictionary.O
                    last_tag = None
            else:
                yield Dictionary.O
                last_tag = None
