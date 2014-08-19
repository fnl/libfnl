"""
.. py:module:: fnl.nlp.sentence
   :synopsis: Classes to generate features from (sentence-based) token sequences and
   semantic annotations on them.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
from fnl.text.token import Token


class Sentence:

    """
    Sentences are token list containers that make working with phrase chunks and annotations on
    those chunks easier.

    Annotations can be added to Sentences; The words and stems of Tokens of the Sentence that
    coincide with an Annotation can be "masked"; That is, instead of the actual word or stem, the
    `Annotation.type` value is used. This is useful to generate features for classifiers that
    should not "learn" the actual words, but rather the entity type, for example.
    """

    def __init__(self, tokens):
        """
        :param tokens: An iterable over `fnl.nlp.token.Token` instances or a `Sentence` instance.
        :return: A new Sentence instance.
        """
        if isinstance(tokens, Sentence):
            self.tokens = tuple(tokens.tokens)
            self.annotations = {
                key: set(values) for key, values in tokens.annotations.items()
            }
            self._mask = list(tokens._mask)
            self._phrases = list(tokens._phrases)
            self._words = dict(tokens._words)
        else:
            self.tokens = tuple(tokens)
            self.annotations = {}
            self._mask = [None] * len(self.tokens)
            self._phrases = []
            self._words = {}
            number = 0
            start = -1

            for i, t in enumerate(self.tokens):
                if t.chunk == 'O':
                    if start != -1:
                        self._words[number] = (start, i)
                        start = -1

                    self._phrases.append(0)
                else:
                    if t.chunk.startswith('B-'):
                        if start != -1:
                            self._words[number] = (start, i)

                        number += 1
                        start = i

                    self._phrases.append(number)

            if start != -1:
                self._words[number] = (start, len(self.tokens))

    def __len__(self):
        "Return the number of tokens this sentence contains."
        return len(self.tokens)

    def __iter__(self):
        "Iterate over the tokens this sentence contains."
        return iter(self.tokens)

    def _getMaskedTokenAttributes(self, attr, start=0, end=None):
        end = len(self.tokens) if end is None else end
        last_mask = None

        for i in range(start, end):
            if self._mask[i] is None:
                yield getattr(self.tokens[i], attr)
                last_mask = None
            else:
                if last_mask != self._mask[i]:
                    yield self._mask[i]

                last_mask = self._mask[i]

    def _getTokenAttributes(self, attr, start=0, end=None):
        end = len(self.tokens) if end is None else end

        for i in range(start, end):
            yield getattr(self.tokens[i], attr)

    def addAnnotation(self, mask, start, end=None, value=None):
        """
        Add a new annotation grouped by a `mask` key, over a span of tokens, and with an
        optional value.

        :param mask: A unique string describing the annotation `mask` key.
        This string will be used to **mask** words or stems.
        :param start: The token start index of this annotation.
        :param end: The token end index (+1 after last token) of this annotation.
        :param value: Any optional object to store with the annotation.
        :return: A new Annotation instance.
        """
        ann = Annotation(self, start, end, value)

        if mask in self.annotations:
            self.annotations[mask].add(ann)
        else:
            self.annotations[mask] = {ann}

        for i in range(ann.start, ann.end):
            if self._mask[i] is None:
                self._mask[i] = mask

        return ann

    def getAnnotations(self, mask):
        "Return the (possibly empty) set of all annotations for a `mask` key."
        if mask in self.annotations:
            return set(self.annotations[mask])
        else:
            return set()

    def maskedStems(self, start=0, end=None):
        """
        Get all token stems [from `start` [to `end`] index], but masking any stem that is
        part of an annotation with the first `Annotation.type` that was assigned to that token.

        :param start: The start index for the first stem.
        :param end: The end index after the last stem.
        :return: A token stem generator, but annotated stems are replaced with their type "mask".
        """
        return self._getMaskedTokenAttributes('stem', start, end)

    def maskedWords(self, start=0, end=None):
        """
        Get all token words [from `start` [to `end`] index], but masking any word that is
        part of an annotation with the first `Annotation.type` that was assigned to that token.

        :param start: The start index for the first word.
        :param end: The end index after the last word.
        :return: A token word generator, but annotated words are replaced with their type "mask".
        """
        return self._getMaskedTokenAttributes('word', start, end)

    def phraseNumber(self, index):
        """
        Return the phrase number (1-based count!) at the given token index.

        :param index: The token index to check for the phrase number.
        :return: The phrase number or **zero** if the token is not part of a phrase.
        """
        return self._phrases[index]

    def phraseNumbers(self, start=0, end=None):
        """
        Get the phrase numbers for each phrase in the span.

        :param start: The index of the first token for the first tag.
        :param end: The index after the last token for the last tag.
        :return: A phrase number generator.
        """
        last = -1
        end = len(self) if end is None else end

        for idx in range(start, end):
            num = self.phraseNumber(idx)

            if num == 0:
                continue
            elif num != last:
                yield num
                last = num

    def phraseOffsetFor(self, number):
        """
        Return the token offset (start, end) for a phrase number (1-based count!).

        :param number: The phrase number to fetch the offset for.
        :return: The start, end token offset for the given phrase number.
        """
        return self._words[number]

    def phraseTagFor(self, number):
        """
        Get the phrase tag for a phrase `number`.

        :param number: The phrase number to fetch the tag for.
        :return: The phrase tag.
        """
        idx, _ = self._words[number]
        return self.tokens[idx].chunk[2:]

    def phraseTags(self, start=0, end=None):
        """
        Get the phrase tags for each phrase.

        :param start: The index of the first token for the first tag.
        :param end: The index after the last token for the last tag.
        :return: A phrase tag generator.
        """
        first = True

        for current in self._getTokenAttributes('chunk', start, end):
            if current == 'O':
                first = False
            else:
                if first:
                    yield current[2:]
                    first = False
                elif current.startswith('B-'):
                    yield current[2:]

    def posTags(self, start=0, end=None):
        """
        Get all token PoS tags [from `start` [to `end`] index].

        :param start: The start index for the first stem.
        :param end: The end index after the last stem.
        :return: A token PoS tag generator.
        """
        return self._getTokenAttributes('pos', start, end)

    def stems(self, start=0, end=None):
        """
        Get all token stems [from `start` [to `end`] index].

        :param start: The start index for the first stem.
        :param end: The end index after the last stem.
        :return: A token stem generator.
        """
        return self._getTokenAttributes('stem', start, end)

    def words(self, start=0, end=None):
        """
        Get all token words [from `start` [to `end`] index].

        :param start: The start index for the first word.
        :param end: The end index after the last word.
        :return: A token word generator.
        """
        return self._getTokenAttributes('word', start, end)


class Annotation:

    """
    Annotations are spans on a sentence that can be used to generate features relative to itself
    and other annotations.

    Methods suffixed with a ``_`` (underscore) are *unsafe* in the sense that they will raise a
    `ValueError` if the annotation isn't "inside a phrase" (i.e., when `Annotation.isInsidePhrase()
    is False`).
    """

    def __init__(self, sentence, start, end=None, value=None):
        """
        :param sentence: The Sentence instance to annotate.
        :param start: The token start index of this annotation.
        :param end: The token end index of this annotation.
        :param value: An optional value to store with the annotation.
        :return: A new annotation instance.
        """
        self.start = int(start)
        self.end = self.start + 1 if end is None else int(end)
        self.sentence = sentence
        self.value = value
        assert self.start < self.end, \
            "Annotation offset %d < %d not consecutive" % (self.start, self.end)
        assert self.start >= 0, "Annotation start=%d < 0" % self.start
        assert self.end <= len(sentence), "Annotation end=%d > len(Sentence)" % self.end

    def __hash__(self):
        return 17 * self.start * self.end * id(self.sentence)

    def __eq__(self, other):
        if not isinstance(other, Annotation):
            return False

        return self.start == other.start and \
            self.end == other.end and \
            self.sentence == other.sentence

    def __lt__(self, other):
        if not isinstance(other, Annotation):
            raise TypeError("%s not an Annotation" % repr(other))

        if self.sentence != other.sentence:
            raise ValueError("cannot compare annotations on different sentences")

        if self.start == other.start:
            return self.end < other.end
        elif self.start < other.start:
            return True
        else:
            return False

    def __repr__(self):
        return '<fnl.nlp.sentence.Annotation %X:%d:%d>' % (id(self.sentence), self.start, self.end)

    def _startEndIndicesBetween(self, other):
        if self.sentence != other.sentence:
            raise ValueError("annotations on different sentences")

        return min(self.end, other.end), max(self.start, other.start)

    def getPhraseNumber_(self):
        """
        Return the phrase number of this annotation if it is inside a phrase.

        :return: The phrase number (1-based count) or zero.
        :raises ValueError: If the annotation spans more than a single phrase (that is, if
        `Annotation.isInsidePhrase()` returns ``False``).
        """
        s = self.sentence
        number = s.phraseNumber(self.start)

        if number != s.phraseNumber(self.end - 1):
            raise ValueError("%s not part of a [single] phrase" % repr(self))

        if number == 0 and not self.isInsidePhrase():
            raise ValueError("%s covers phrase- and non-phrase-regions" % repr(self))

        return number

    def getPhraseOffset(self):
        """
        Return the token offset of this annotation, or if it is inside a phrase, return the
        offset of the surrounding phrase.

        :return: The (start, end) token offset of the annotation or surrounding phrase.
        """
        try:
            number = self.getPhraseNumber_()
        except ValueError:
            return self.start, self.end
        else:
            if number == 0:
                return self.start, self.end
            else:
                return self.sentence.phraseOffsetFor(number)

    def getPhraseStems(self):
        """
        Return the token stems of the phrase that contains this annotation.

        :return: The masked token stems of the surrounding phrase (or the masked stems only if
        the annotation is not part of a phrase).
        """
        start, end = self.getPhraseOffset()
        return self.sentence.maskedStems(start, end)

    def getPhraseTag_(self):
        """
        Return the phrase tag of the annotation, or 'O' is not inside a phrase.

        :return: The phrase tag or the string "O".
        :raises ValueError: If the annotation spans more than a single phrase (that is, if
        `Annotation.isInsidePhrase()` returns ``False``).
        """
        number = self.getPhraseNumber_()

        if number == 0:
            return 'O'
        else:
            return self.sentence.phraseTagFor(number)

    def getPhraseWords(self):
        """
        Return the token words of the phrase that contains this annotation.

        :return: The masked token words of the surrounding phrase (or the masked words only if
        the annotation is not part of a phrase).
        """
        start, end = self.getPhraseOffset()
        return self.sentence.maskedWords(start, end)

    def getPhrasePrefix(self):
        """
        Return the prefix tokens in the phrase that contains this annotation.

        :return: The token words before the annotation.
        """
        start, end = self.getPhraseOffset()

        if self.sentence._mask[start] is None:
            idx = start + 1

            while idx < end and self.sentence._mask[idx] is None:
                idx += 1

            return self.sentence.maskedStems(start, idx)
        else:
            return iter(())

    def getPhraseSuffix(self):
        """
        Return the suffix tokens in the phrase that contains this annotation.

        :return: The token words after the annotation.
        """
        start, end = self.getPhraseOffset()

        if self.sentence._mask[end - 1] is None:
            idx = end - 1

            while idx > start and self.sentence._mask[idx - 1] is None:
                idx -= 1

            return self.sentence.maskedStems(idx, end)
        else:
            return iter(())

    def getPrepositionedNounPhrase_(self):
        """
        If the annotation is prefixed by a preposition phrase that in turn has a noun phrase,
        return that noun phrase; E.g., "The Theme of Annotation" returns the (masked) stems ["the",
        "theme"]; Otherwise, return ``None``.

        :return: A generator for the prepositioned noun phrase's masked stems or ``None``.
        :raises ValueError: If the annotation spans more than a single phrase (that is, if
        `Annotation.isInsidePhrase()` returns ``False``).
        """
        num = self.getPhraseNumber_()
        s = self.sentence

        if num > 2 and s.phraseTagFor(num - 1) == 'PP' and s.phraseTagFor(num - 2) == 'NP':
            start, end = s.phraseOffsetFor(num - 2)
            return s.maskedStems(start, end)
        else:
            return None

    def isInsidePhrase(self):
        "Return ``True`` if this annotation is fully contained within a chunk (including 'O')."
        chunk = self.sentence.tokens[self.start].chunk[2:]
        tokens = self.sentence.tokens

        for idx in range(self.start + 1, self.end):
            if not tokens[idx].chunk[2:] == chunk:
                return False
            elif tokens[idx].chunk.startswith('B-'):
                return False

        return True

    def phraseDistanceTo(self, other):
        """
        Return the number of phrases separating two annotations.

        If an annotation does not cover an entire phrase, the phrase could be counted:
        Any token encountered between the two annotations that is part of a phrase
        that has not yet been counted will increment the distance by one.

        **Special case**: if the annotations span the same tokens, the distance is ``-1``.

        :param other: The other annotation to measure the distance to.
        :return: The distance in number of phrases or -1 if equal annotations.
        :raises ValueError: If the annotations are on different sentences.
        """
        start, end = self._startEndIndicesBetween(other)
        return sum(1 for _ in self.sentence.phraseTags(start, end)) - (self == other)

    def phraseNumbersBetween(self, other):
        """
        Get the tags of all phrases found *between* this and the other annotation.

        Any token encountered between the two annotations that is part of a phrase
        will lead to a phrase tag being emitted (e.g., in the case of annotations
        that only partially annotate a phrase).

        :param other: The other annotation to create the span.
        :return: All phrase tags found between the two annotations.
        :raises ValueError: If the annotations are on different sentences.
        """
        s = self.sentence
        start, end = self._startEndIndicesBetween(other)
        first, last = 0, 0

        while first == 0 and end > start:
            first = s.phraseNumber(start)
            start += 1

        if first == 0:
            return iter(())

        while last == 0 and end >= start:
            last = s.phraseNumber(end - 1)
            end -= 1

        return range(first, last + 1)

    def phraseTagsBetween(self, other):
        """
        Get the tags of all phrases found *between* this and the other annotation.

        Any token encountered between the two annotations that is part of a phrase
        will lead to a phrase tag being emitted (e.g., in the case of annotations
        that only partially annotate a phrase).

        :param other: The other annotation to create the span.
        :return: All phrase tags found between the two annotations.
        :raises ValueError: If the annotations are on different sentences.
        """
        start, end = self._startEndIndicesBetween(other)
        return self.sentence.phraseTags(start, end)

    def posTagsBetween(self, other):
        start, end = self._startEndIndicesBetween(other)
        return self.sentence.posTags(start, end)

    def tokenDistanceTo(self, other):
        """
        Return the number of tokens separating two annotations.

        For *overlapping annotations* a **negative** distance will be reported that represents
        the negative count of the number of overlapping tokens.

        :param other: The other annotation to measure the distance to.
        :return: The distance in number of tokens or the negative count of overlapping tokens.
        :raises ValueError: If the annotations are on different sentences.
        """
        start, end = self._startEndIndicesBetween(other)
        return end - start

    def verbPhraseBetween(self, other):
        """
        Return the single verb phrase' masked stems between the current annotation and the
        `other` annotation, or ``None`` if there is no VP or more than one.

        :param other: The other annotation between which the VP must be found.
        :return: A generator of the verb phrase stems or ``None``.
        """
        tags = list(self.phraseTagsBetween(other))

        if sum(1 for t in tags if t == 'VP') == 1:
            numbers = list(self.phraseNumbersBetween(other))
            assert len(numbers) == len(tags), "%s != %s" % (repr(numbers), repr(tags))
            num = numbers[tags.index('VP')]
            start, end = self.sentence.phraseOffsetFor(num)
            return self.sentence.maskedStems(start, end)
        else:
            return None


def SentenceParser(lines, entity_masks, id_columns=None, sep='\t'):
    if id_columns is not None:
        entity_col = id_columns + 5
        num_columns = id_columns + len(entity_masks) + 5  # token items
    else:
        entity_col = -1
        num_columns = -1

    tokens = []
    entities = []
    sent_id = None

    for l in lines:
        l = l.strip()

        if not l:
            if len(tokens) == 0:
                continue

            yield makeSentence(entities, entity_masks, id_columns, sent_id, tokens)

            tokens = []
            entities = []
            sent_id = None
        else:
            items = l.split(sep)

            if id_columns is None:
                num_columns = len(items)
                id_columns = num_columns - len(entity_masks) - 5  # token items
                logging.info("guessed number of ID columns: %s", id_columns)
                assert id_columns > 0, "no sentence ID columns"
                entity_col = id_columns + 5

            assert len(items) >= num_columns, \
                "lower number of columns (%d) than expected (%d)" % (len(items), num_columns)

            if id_columns:
                if sent_id is None:
                    sent_id = items[:id_columns]
                else:
                    assert items[:id_columns] == sent_id, "IDs don't match (%s != %s)" % (
                        ':'.join(items[:id_columns]), ':'.join(sent_id)
                    )

            tokens.append(Token(*items[id_columns:entity_col]))
            entities.append(items[entity_col:num_columns])

    if len(tokens) > 0:
        yield makeSentence(entities, entity_masks, id_columns, sent_id, tokens)


def entityIterator(entity_tags):
    start = -1
    value = None

    for idx, tag in enumerate(entity_tags):
        if value is not None:
            if tag == 'O':
                yield start, idx, value
                start = -1
                value = None
            elif tag.startswith('B-'):
                yield start, idx, value
                start = idx
                value = tag[2:]
            elif tag.startswith('I-'):
                pass
            else:
                raise RuntimeError('illegal tag "%s" at %d' % (tag, idx))
        else:
            if tag == 'O':
                pass
            elif tag.startswith('B-'):
                start = idx
                value = tag[2:]
            else:
                raise RuntimeError('illegal tag "%s" at %d' % (tag, idx))


def makeSentence(entities, entity_masks, id_columns, sent_id, tokens):
    sentence = Sentence(tokens)

    for mask, tags in zip(entity_masks, zip(*entities)):
        for start, end, value in entityIterator(tags):
            sentence.addAnnotation(mask, start, end, value)

    if id_columns:
        return tuple(sent_id), sentence
    else:
        return sentence
