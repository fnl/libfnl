#############
``libfnl``\ ™
#############

Introduction
============

**libfnl** is an API and CLI facilitating data and text mining by providing a collection of easy-to-use tools.
The library is designed to work with Python 3 (*only*).
It is specifically tuned towards mining biomedical/scientific texts, but can be used in other contexts if need be, too.
It is a complementary piece in the gnamed_ gene name repository daemon and the medic_ PubMed mirroring tool collection.
In addtion, an (orphan) couchpy_ repository could provide a document storage facility.

The library contains the following packages:

``fnl.nlp``
    tools to linguistically analyze text (tokenization, PoS tagging, phrase chunking, entity detection);
    modules to segment sentences (based on NLTK_), and map text (strings) to entries in dictionaries
    this includes a Python wrapper for the GENIA_ Tagger_, a Python wrapper for the `NER Suite`_, and a handler for the GENIA_ corpus;
    furthermore, via NLTK_ 's wrapper for MegaM_, a Maximum Entropy classifier is available, too;
``fnl.stat``
    a module to evaluate inter-rater Kappa scores and a module to develop text classifiers based on Scikit-Learn_
``fnl.text``
    wrappers to work with text data (strings, tokens, segments, annotations, etc.)
``fnl.utils``
    additional utilities and tools (currently, just for handling JSON_)
``scripts``
    the CLI scripts to manage data/text, representing the main value provided by this collection

The script directory provides the following command-line interfaces:
 
- ``fnlclassi`` generate a classifier for [NER-tagged] text using Scikit-Learn_.
- ``fnlcorpus`` store corpora in JSON format in a CouchDB.
- ``fnldgrep`` "grep" for tokens using a dictionary.
- ``fnldictag`` tag semantic tokens from a dictionary in linguistically annotated text.
- ``fnlgpcounter`` count gene/protein symbols in MEDLINE.
- ``fnlkappa`` calculate inter-rater agreement scores.
- ``fnlsegment`` segment text into sentences using NLTK_ (`PunktSentenceTokenizer`).
- ``fnlsegtrain`` train a `nltk.punkt.PunktSentenceTokenizer`.
- ``fnltok`` a fast, pure-Python, Unicode-aware string tokenizer.

.. warning:: This project is under "continuous development", better take your own snapshot.

.. _CouchDB: http://couchdb.apache.org/
.. _JSON: http://www.json.org
.. _GENIA: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/home/wiki.cgi
.. _MegaM: http://www.umiacs.umd.edu/~hal/megam/
.. _NER Suite: http://nersuite.nlplab.org/
.. _NLTK: http://nltk.org/
.. _Scikit-Learn: http://scikit-learn.org/stable/
.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _Tagger: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/tagger/
.. _gnamed: http://github.com/fnl/gnamed
.. _medic: http://github.com/fnl/medic
.. _couchpy: http://github.com/fnl/couchpy

Requirements
============

* **Python 3.2+**
* Numpy, SciPy, and Scikit-Learn 0.14+ (for ``fnlclassi``)
* NLTK 3.0+ (for the sentence segmenting tools ``fnlseg*``)
* DAWG_ (for ``fnlgpcounter``; see Installation below)

Optional projects that work together with this project:

* GENIA_ Tagger_ (optional, latest version)
* `NER Suite`_ (optional, latest version)
* MegaM_ - a MaxEnt classifier for NLTK_ with a (fast) L-BFGS optimizer
* gnamed_ for creating gene/protein name repositories
* medic_ for mirroring and handling PubMed citations
* txtfnnl_ natural language processing tools based on Apache OpenNLP and UIMA

.. _DAWG: https://pypi.python.org/pypi/DAWG
.. _txtfnnl: https://github.com/fnl/txtfnnl

Installation
============

Into a **Python 3** virtual environment::

    pip install virtualenv # if virtualenv is not yet installed
    git clone git://github.com/fnl/libfnl.git libfnl
    virtualenv libfnl
    cd libfnl
    . bin/activate
    pip install argparse # for python3 < 3.2
    pip install numpy # because installing scipy fails if numpy isn't installed already
    pip install -e . # installs all other dependencies

    # if you prefer to install all other dependencies manually
    # and/or prefer to use setup.py instead of pip:
    # python setup.py install
    pip install sqlalchemy
    pip install sklearn
    pip install nltk --pre # to get 3.0

    # if you want to install the test environment:
    pip install pytest

    # special steps to install DAWG
    git clone git@github.com:fnl/DAWG.git
    cd DAWG
    python setup.py install
    cd ..

License
=======

All parts of this library are licensed under the `GNU Affero GPL v3`_

.. _GNU Affero GPL v3: http://www.gnu.org/licenses/agpl.html

See the attached LICENSE.txt file.

Copyright
=========

© 2006-2014 Florian Leitner. All rights reserved.
