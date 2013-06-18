#############
``libfnl``\ ™
#############

Introduction
============

**libfnl** is an API and CLI for mining biological texts by
providing data management tools to facilitate this task. The library is
exclusively designed to work with Python 3000 (3.x). It is targeted
to cooperate with the parallel txtfnnl_ UIMA text mininig library.

The library contains the following packages:

``libfnl.gnamed``
    providing management and storage facilities for gene/protein symbols,
    names, keywords and their references into literature
``libfnl.medline``
    providing a management and storage facility for MEDLINE and PubMed records
``libfnl.nlp``
    currently, just a Python wrapper for the GENIA_ Tagger_
``libfnl.stat``
    currently, only a module to evaluate inter-rate Kappa scores
``libfnl.text``
    modules to annotate and tokenize text (strings)
``libfnl.utils``
    utilities/tools

The library provides the following command-line tools:

- fnlgnamed_ A CLI to create a gene/protein repository.
- fnlmedline_ A CLI to manage a local MEDLINE storage.
- ``fnlkappa`` A CLI to calculate inter-rater agreement scores.

.. warning:: This API is under development (alpha).

.. _JSON: http://www.json.org
.. _GENIA: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/home/wiki.cgi
.. _Tagger: http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/tagger/
.. _txtfnnl: http://github.com/fnl/txtfnnl
.. _fnlgnamed: http://github.com/fnl/libfnl/wiki/fnlgnamed.py
.. _fnlmedline: http://github.com/fnl/libfnl/wiki/fnlmedline.py

Requirements
============

External binaries:

* Python 3.0+ (3.3 or newer recommended)
* Postgres 8.0+ (9.0 or newer recommended)
* SQLite 3.5+ (3.7 or newer recommended)
* GENIA Tagger (optional, latest version)
* Git (optional, to clone the library from GitHub)

Python packages:

* virtualenv (suggested/optional)
* SQL Alchemy 0.8+ (0.8.1 or newer recommended)
* Psycopg2 2.2+ (2.5 or newer recommended)

Installation
============

Into a **Python 3** environment::

    pip install virtualenv # optional; if virtualenv is not yet installed
    git clone git://github.com/fnl/libfnl.git libfnl
    virtualenv libfnl # optional; if using a virtual environment
    cd libfnl
    . bin/activate # optional; if using a virual environment
    pip install argparse # only required for python3 < 3.2
    python setup.py install

License
=======

All parts of this library are licensed under the `GNU Affero GPL v3`_

.. _GNU Affero GPL v3: http://www.gnu.org/licenses/agpl.html

Copyright
=========

.. include:: <isonum.txt>

© 2006-2013 fnl™. All rights reserved.
