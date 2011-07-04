"""
.. py:module:: penn
   :synopsis: The Penn tag-set.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

TAGSET = frozenset({
    "$", # Currency symbols
    "``", # Opening quotation mark
    "''", # Closing quotation mark
    "(", # Opening parentheses
    ")", # Closing parentheses
    ",", # Comma
    "--", # Dash: - or --
    ".", # Sentence terminal: .?! and possibly ;: -- if abbreviation use of ., use SYM, or use the previous token's tag
    ":", # Non-sentence terminal use of ;:/ or ellipsis (...)
    "CC", # Coordinating conjunction: &, 'n, et, versus, and, but, or, ...
    "CD", # Cardinal Number: mid-1890, fourty-two, 1974, '60s, .025, ...
    "DT", #	Determiner: all an the this these those neither no
    "EX", # Existential there: there
    "FW", # Foreign word
    "IN", # Preposition or subordinating conjunction: astride, among, whether, out, pro, despite, on, by, throughout, if, ...
    "JJ", # Adjective or ordinal numeral: first, third, pre-war, regrettable, ...
    "JJR", # Adjective, comparative: better, briefer, clearer, ...
    "JJS", # Adjective, superlative: best, briefest, clearest, ...
    "LS", # List item marker: A, B., C), (D), *, -, ...
    "MD", # Modal auxiliary: can, cannot, couldn't, might, may, shouldn't,...
    "NN", # Common noun, singular or mass: afghan, hyena, subhumanity, knuckle-duster,...
    "NNP", # Proper noun, singular: Chrysler, Florian, Anarcho-Syndicalist, ...
    "NNPS", # Proper noun, plural: Anarcho-Syndicalists, Angels, Apaches, ...
    "NNS", # Common noun, plural: scotches, clubs, factory-jobs, ...
    "PDT", # Predeterminer: all, both, many, sure, ... -- when they precede an article
    "POS", # Possessive ending/genetive marker: ie., nouns ending in 's
    "PRP", # Personal pronoun: I, me, you, he, hers, himself, thee, thou, ours...
    "PRP$", # Possessive pronoun: my, your, mine, yours, ours, our, his,...
    "RB", # Adverb, most words that end in -ly as well as degree words like quite, too and very
    "RBR", # Adverb, comparative: Adverbs with the comparative ending -er, with a strictly comparative meaning.
    "RBS", # Adverb, superlative: best, biggest, least, worst, ...
    "RP", # Particle: about, apart, ever, for, go, high, i.e., ...
    "SYM", # Symbol; incl. mathematical, scientific or technical symbols, and abbrev. marks
    "TO", # to (as preposition or infinitive marker)
    "UH", # Interjection e.g. uh, well, yes, my, dammit,...
    "VB", # Verb, base form: subsumes imperatives, infinitives and subjunctives
    "VBD", # Verb, past tense: includes the conditional form of the verb to be
    "VBG", # Verb, gerund or persent participle: verbs ending in -ing
    "VBN", # Verb, past participle: verbs ending in -ed but not past tense
    "VBP", # Verb, non-3rd person singular present tense: lengthen, attract
    "VBZ", # Verb, 3rd person singular present tense: lengthens, attracts
    "WDT", # WH-determiner: which, that, what, ... -- when it is used as a relative pronoun
    "WP", # WH-pronoun: that, what, who, whom...
    "WP$", # WH-pronoun, possessive: whose
    "WRB", # WH-adverb: how, where, why, whence, ...
})
"""
The list of accepted tags, ie., the exact Penn tagset.
"""

AMBIGUITY_SEP = "|"
"""
A separator of tags used on tokens where the exact meaning is ambiguous and
multiple tags can be applied to the token. These tags should be listed and
separated with this symbol; eg.: ``documented/JJ|VBN``.
"""

AMBIGUOUS = "AMBI"
"""
Special tag to use when an ambiguous token has been encountered to make the
existence of it explicit.

Ie., in a tagged text, the ambiguous token should be split, each token
annotated separately, and this tag should be also used. For example, with the
case shown in :data:`.AMBIGUITY_SEP`, the tags should look like::

    { ...
      "penn": { ...
                "JJ": [ ... (87, 97), ...],
                "VBN": [ ... (87, 97), ...],
                "AMBI": [ ... (87, 97), ...],
                ... }
      ... }
"""

REMAPPED = {
    "PRP$": "PRPP",
    "WP$": "WPP",
    "$": "CUR",
    "``": "Q_O",
    "''": "Q_C",
    "(": "P_O",
    ")": "P_C",
    ",": "COMMA",
    ".": "STOP",
    ":": "PUNCT",
    "--": "DASH",
}
"""
Mapping of tags containing symbol characters in the Penn tag-set to letter
characters, as they are more versatile in various ways of handling them.
"""
