#############
``libfnl``\ ™
#############

Introduction
============

**libfnl** is an API and CLI to facilitate the mining of [biological] texts by
providing data management tools for this task. The library is exclusively
designed to work with Python 3k (3.2+). It is targeted to cooperate with the
txtfnnl_ text mininig library developed in parallel. In a nutshell, ``libfnl``
provides the "meta-data" for text mining tasks, while txtfnnl_ is the actual
pipeline for this job.

The library contains the following packages:

``libfnl.couch``
    provides a Py3k Apache CouchDB_ client for managing JSON_ data (when this
    project was started, there was no Py3k CouchDB_ client around, so this
    project has its own)
``libfnl.gnamed``
    providing management and storage facilities for gene/protein symbols,
    names, keywords and their references into literature based on SQLAlchemy_;
    outsourced as its own package
``libfnl.medline``
    providing a management and storage facility for MEDLINE and PubMed records
    based on SQLAlchemy_;
    outsorced as its own package
``libfnl.nlp``
    currently, just a Python wrapper for the GENIA_ Tagger_
``libfnl.stat``
    currently, only a module to evaluate inter-rate Kappa scores
``libfnl.text``
    modules to extract, annotate and tokenize text (strings)
``libfnl.utils``
    useful utilities and tools (currently, just for handling JSON_ and for
    dispalying a clean progress bar on the command line)
``scripts``
    various useful scripts to manage data/text

The library provides the following command-line tools:
 
- fnlgnamed_ A CLI to bootstrap a consolidated gene/protein repository. *Outsourced to its own PyPI package ``gnamed``.*
- fnlmedline_ A CLI to maintain a local MEDLINE data warehouse. *Outsourced to its own PyPI packagee ``medic``.*
- ``fnlkappa`` A CLI to calculate inter-rater agreement scores.
- ``fnlgpcounter`` A CLI to count gene/protein symbols in MEDLINE.
- ``fnlcorpus`` A CLIT to store corpora in JSON format in a CouchDB.
- ``fnlpst*`` Three tools to segment text into sentences using NLTK_ (3.0alpha).
- ``fnlclass[i]`` Two CLI to quickly develop a classifier for text using Scikit-Learn_.
- ``fnldictag`` A CLI to tag tokens from a dictionary in text.

.. warning:: This project is under "continuous" development (very alpha-ish).

.. _CouchDB: http://couchdb.apache.org/
.. _JSON: http://www.json.org
.. _GENIA: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/home/wiki.cgi
.. _NLTK: http://nltk.org/
.. _Scikit-Learn: http://scikit-learn.org/stable/
.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _Tagger: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/tagger/
.. _txtfnnl: http://github.com/fnl/txtfnnl
.. _fnlgnamed: http://github.com/fnl/libfnl/wiki/fnlgnamed.py
.. _fnlmedline: http://github.com/fnl/libfnl/wiki/fnlmedline.py

Requirements
============

* Python 3.0+ (3.2 or newer recommended)
* SQLAlchemy 0.8+ (A Python ORM)

Optional tools:

* Postgres 8.4+ (9.2 or newer recommended)
* psycopg2 (A Python Postgres DB client)
* GENIA Tagger (optional, latest version)
* CouchDB 1.0+ (1.3 or newer recommended)
* RE2 (Google's DFA-based regular expression library)
* Numpy, SciPy, and Scikit-Learn 0.14+ (for the document classifiers ``fnlclass[i]``)
* NLTK 3.0+ (for the sentence segmenting tools ``fnlpst*``)

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
