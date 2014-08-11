"""
.. py:module:: fnl.nlp
   :synopsis: Modules for natural language processing.

Tagger modules (PoS, phrase, and/or entity) are expected adhere to a simple interface specification::

	tagger.send(data)
	tags = [t for t in tagger]

In the case of "base" taggers (PoS) that start with text,
``data`` should be a piece of text (i.e., a string).
In all cases where the tagger uses the tags of a "base" tagger (e.g., a NER tagger),
``data`` should be the list of tags to examine.
The tags accepted by the interfaces should be `fnl.nlp.token.Token` instances.
The `fnl.nlp.analysis.TextAnalysis` class then can work with
any kind of tagger that adheres to this specification.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
