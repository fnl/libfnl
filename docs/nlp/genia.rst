###################################
nlp.genia -- GENIA corpus and tools
###################################

.. automodule:: libfnl.nlp.genia

=============================
corpus -- GENIA Corpus Reader
=============================

.. automodule:: libfnl.nlp.genia.corpus

Reader
------

.. autoclass:: libfnl.nlp.genia.corpus.Reader
    :members:

======================
tagger -- GENIA Tagger
======================

.. automodule:: libfnl.nlp.genia.tagger

Usage example:

>>> from libfnl.nlp.genia.tagger import GeniaTagger
>>> tagger = GeniaTagger()
>>> sentence = "Inhibition of NF-kappa beta activation reversed the anti-apoptotic effect of isochamaejasmin."
>>> tagger.send(sentence)
>>> for token in tagger:
...     print(token)
...
Token(word='Inhibition', stem='Inhibition', pos='NN', chunk='B-NP', entity='O')
Token(word='of', stem='of', pos='IN', chunk='B-PP', entity='O')
Token(word='NF-kappa', stem='NF-kappa', pos='NN', chunk='B-NP', entity='B-protein')
Token(word='beta', stem='beta', pos='NN', chunk='I-NP', entity='I-protein')
Token(word='activation', stem='activation', pos='NN', chunk='I-NP', entity='O')
Token(word='reversed', stem='reverse', pos='VBD', chunk='B-VP', entity='O')
Token(word='the', stem='the', pos='DT', chunk='B-NP', entity='O')
Token(word='anti-apoptotic', stem='anti-apoptotic', pos='JJ', chunk='I-NP', entity='O')
Token(word='effect', stem='effect', pos='NN', chunk='I-NP', entity='O')
Token(word='of', stem='of', pos='IN', chunk='B-PP', entity='O')
Token(word='isochamaejasmin', stem='isochamaejasmin', pos='NN', chunk='B-NP', entity='O')
Token(word='.', stem='.', pos='.', chunk='O', entity='O')

Note that initalizing a new tagger will take a while due to reading the models. Sentences should be strings and not contain line-breaking (eg., ``\n``) characters. After sending the sentence, the tagger instance can be used as iterator yielding :py:class:`libfnl.nlp.genia.tagger.Token` instances::

            tagger.send(sentence)

            for token in tagger:
                # do something with token...

.. autodata:: libfnl.nlp.genia.tagger.GENIATAGGER_DIR

.. autodata:: libfnl.nlp.genia.tagger.GENIATAGGER

GeniaTagger
-----------

.. autoclass:: libfnl.nlp.genia.tagger.GeniaTagger
   :members:

Token
-----

.. autoclass:: libfnl.nlp.genia.tagger.Token
   :members: asDict, replace
