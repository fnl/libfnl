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

.. warning:: This API is currently under heavy development and by no means to be
    considered stable.

Requirements
============

* Python 3.0+ (3.1 or newer recommended)
* CouchDB 1.0+

Installation
============

Has to be done manually, for now...