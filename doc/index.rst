.. libfnl documentation master file, created by
   sphinx-quickstart on Fri Jun  3 18:15:08 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

####################################
libfnl: A toolset for real-world NLP
####################################

Introduction
============

**libfnl** is an API for interactively processing natural language (**NLP**) and associated statistical functions. In addition, it provides a collection of command line scripts to do some of this work in a (UNIX) shell. Finally, a server can be used to visualize the data and interact with the text annotations. The library is exclusively designed to work with Python 3000 (3.x). The main data storage is managed via CouchDB_. External algorithms are preferentially provided as wrapped Python classes of C or C++ implementations available on the Internet, for example the GENIA_ Tagger_. These design choices should ensure a good performance of this library, sufficient for real-world NLP problems, and at the same time make the data created easily sharable via the server and CouchDB.

.. _CouchDB: http://couch.apache.org
.. _GENIA: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/home/wiki.cgi
.. _Tagger: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/tagger/

License
=======

The entire API/code-base is licensed under the `GNU Affero GPL v3`_

.. _GNU Affero GPL v3: http://www.gnu.org/licenses/agpl.html

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
   nlp/text
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

