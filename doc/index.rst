.. libfnl documentation master file, created by
   sphinx-quickstart on Fri Jun  3 18:15:08 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

####################################
libfnl: A toolset for real-world NLP
####################################

Introduction
============

**libfnl** is an API for interactively processing natural language (**NLP**)
and associated statistical functions. In addition, it provides a collection of
command line scripts to do some of this work in a (UNIX) shell. The library
is exclusively designed to work with Python 3000 (3.x). All data storage is
managed via CouchDB_. Heavy statistical processing and machine learning
algorithms are provided as wrapped Python classes of C or C++ implementations
available on the Internet, for example the GENIA_ Tagger_. This design choice
ensures a high performance of this library sufficient for real-world NLP
problems.

.. _CouchDB: http://couch.apache.org
.. _GENIA: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/home/wiki.cgi
.. _Tagger: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/tagger/

Environment
===========

The following environment variables can be configured or default to the presented values:

:py:data:`libfnl.couch.broker.COUCHDB_URL`

    The URL where the CouchDB server is located.

:py:data:`libfnl.nlp.genia.tagger.GENIATAGGER_DIR`

    The directory where the ``geniatagger`` binary and the ``morphdic`` directory are located.

Contents
========

.. toctree::
   :numbered:
   :maxdepth: 2

   couch
   nlp
   nlp/genia
   nlp/medline
   stat

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Command Line Scripts
====================

The following command line scripts are installed by this package:

``fnlcorpus.py``

    A script to read corpus files.

``fnlkappa.py``

    A script to calculate inter-annotator agreement.

``fnlmedline.py``

    A script to manage a mirror of PubMed/MEDLINE records and external document attachments as a CouchDB.

