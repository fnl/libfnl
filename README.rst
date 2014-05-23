#############
``libfnl``\ ™
#############

Introduction
============

**libfnl** is an API and CLI facilitating data mining of text by providing a collection of easy-to-use tools.
The library is designed to play ball with Python 3.2+ and *only* targets Python 3k.
It is a complementary piece in the gnamed_ gene name repository daemon and the medic_ PubMed mirroring tool collection.

The library contains the following packages:

``fnl.couch``
    provides a Py3k Apache CouchDB_ client for managing JSON_ data (when this project was started, there was no Py3k CouchDB_ client around, so this project has its own);
``fnl.nlp``
    tools to linguistically analyze text (PoS tagging, phrase chunking, entity detection) including a Python wrapper for the GENIA_ Tagger_, a Python wrapper for the `NER Suite`_, and a handler for the GENIA_ corpus
``fnl.stat``
    a module to evaluate inter-rater Kappa scores and a module to develop text classifiers based on Scikit-Learn_
``fnl.text``
    modules to extract, tokenize, segment sentences (based on NLTK_), and map text (strings) to entries in dictionaries
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
- ``fnlsegment`` segment text into sentences using NLTK_ (3.0alpha).
- ``fnlsegtrain`` train a NLTK_ PunktSentenceTokenizer.
- ``fnltok`` a fast, pure-Python, Unicode-aware string tokenizer.

.. warning:: This project is under "continuous" development.

.. _CouchDB: http://couchdb.apache.org/
.. _JSON: http://www.json.org
.. _GENIA: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/home/wiki.cgi
.. _NER Suite: http://nersuite.nlplab.org/
.. _NLTK: http://nltk.org/
.. _Scikit-Learn: http://scikit-learn.org/stable/
.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _Tagger: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/tagger/
.. _gnamed: http://github.com/fnl/gnamed
.. _medic: http://github.com/fnl/medic

Requirements
============

* **Python 3.2+**
* Numpy, SciPy, and Scikit-Learn 0.14+ (for ``fnlclassi``)
* NLTK 3.0+ (for the sentence segmenting tools ``fnlseg*``)
* DAWG (for ``fnlgpcounter``; see Installation below)

Optional projects that work together with this project:

* GENIA Tagger (optional, latest version)
* CouchDB 1.0+ (1.3 or newer recommended, for ``fnlcorpus``)
* gnamed_ for creating gene/protein name repositories
* medic_ for mirroring and handling PubMed citations
* txtfnnl_ natural language processing tools based on Apache OpenNLP and UIMA

Installation
============

Into a **Python 3** virtual environment::

    pip install virtualenv # if virtualenv is not yet installed
    git clone git://github.com/fnl/libfnl.git libfnl
    virtualenv libfnl
    cd libfnl
    . bin/activate
    pip install argparse # for python3 < 3.2
    pip install -e . # installs all dependencies

    # if you prefer to install dependencies manually
    # and/or prefer to use setup.py instead of pip:
    # python setup.py install
    pip install sqlalchemy
    pip install psycopg2
    pip install nose
    pip install mock
    pip install sklearn
    # pip install nltk # v3.0 has to be installed manually

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
