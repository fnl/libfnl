####################################
libfnl: A toolset for real-world NLP
####################################

Introduction
============

**libfnl** is an API for interactively processing natural language (**NLP**) and provides statistical functions and storage mechanisms associated to this task. In addition, it provides a collection of command line scripts to do some of this work in a (UNIX) shell. The library is exclusively designed to work with Python 3000 (3.x). All data storage is managed via CouchDB_, although highly relational data will be stored in Posgres, and Neo4j might be used one day for graph data. External algorithms are provided as wrapped Python classes of C or C++ implementations if available off the Internet, for example the GENIA_ Tagger_. These design choices should ensure a good performance of this library, sufficient for many NLP problems, while maintaining, storing, and sharing data is straight-forward because of CouchDB. For NLP researchers, this library is (1) targeted at BioNLP, and (2) entirely based on offset-based annotations using "plain text" and JSON_ for the annotations, while avoiding XML as much as possible.

.. _CouchDB: http://couch.apache.org
.. _GENIA: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/home/wiki.cgi
.. _JSON: http://www.json.org
.. _Tagger: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/tagger/

.. warning:: This API is currently under heavy development and by no means to be
    considered stable.

License
=======

The entire API/code-base is licensed under the `GNU Affero GPL v3`_

.. _GNU Affero GPL v3: http://www.gnu.org/licenses/agpl.html

Requirements
============

* Python 3.0+ (3.1 or newer recommended)
* CouchDB 1.0+ (1.0.1 or newer recommended)
* GENIA Tagger (optional, latest version)

Planned extensions of this library will also require:

* CRFSuite (A CRF tagger in pure C)
* Cython (C/C++ bindings in Python)
* Neo4j (A open-source graph database)
* Postgres (The open-source relational database)
* psycopg2 (A Python Postgres client)
* RE2 (Google's DFA-based regular expression library)
* SVMlib (A Support Vector Machine library)

Installation
============

Has to be done manually, for now...