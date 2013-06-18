Synopsis
========

A tool to parse MEDLINE XML files or download eUtils' PubMed XML,
bootstrapping a MEDLINE/PubMed database store,
updating and/or deleting the records, and
writing the contents of selected PMIDs into flat-files.

Entity Relationship Model
=========================

::

    [Author] → [Medline] ← [Descriptor] ← [Qualifier]
                ↑     ↑
      [Identifier]   [Section]

Medline (records)
  **pmid**:BIGINT, *status*:ENUM(state), *journal*:VARCHAR(256),
  *created*:DATE, completed:DATE, revised:DATE, modified:DATE

Author (authors)
  **pmid**:FK(Medline), **pos**:SMALLINT, *name*:TEXT,
  initials:VARCHAR(128), forename:VARCHAR(128), suffix:VARCHAR(128),

Descriptor (descriptors)
  **pmid**:FK(Medline), **pos**:SMALLINT, *name*:TEXT, major:BOOL

Qualifier (qualifiers)
  **pmid**:FK(Descriptor), **pos**:FK(Descriptor), **sub**:SMALLINT,
  *name*:TEXT, major:BOOL

Identifier (identifiers)
  **pmid**:FK(Medline), **namespace**:VARCHAR(32), **value**:VARCHAR(256)

Section (sections)
  **pmid**:FK(Medline), **seq**:SMALLINT, *name*:ENUM(section),
  label:VARCHAR(256), *content*:TEXT

- **bold** (Composite) Primary Key
- *italic* NOT NULL

Supported XML Elements
======================

- PMID
- ArticleTitle (`Section.name` ``Title``)
- VernacularTitle (`Section.name` ``Vernacular``)
- AbstractText (`Section.name` ``Abstract`` or capitalized NlmCategory)
- CopyrightInformation (`Section.name` ``Copyright``)
- DescriptorName
- QualifierName
- Author
- ELocationID
- OtherID
- ArticleId (only available in PubMed XML)
- MedlineCitation (`Medline.status` from Status)
- DateCompleted
- DateCreated
- DateRevised
- MedlineTA (`Medline.journal`)

Requirements
============

- Python 3.2+
- SQL Alchemy 0.7+
- any database SQL Alchemy can work with

Setup
=====

See the general setup instructions for libfnl in the README.

Install all dependencies/requirements::

    pip install argparse # only for python3 < 3.2
    pip install SQLAlchemy
    pip install psycopg2 # optional, can use any other DB driver

Create the database::

    dbcreate medline # for example, to create a Postgres DB

Usage
=====

``fnlmedline.py [options] URL COMMAND PMID|FILE...``

The **URL** is the DSN for the database; For example:

Postgres
    ``postgresql://host//dbname``
SQLite
    ``sqlite:////absolute/path/to/foo.db`` or
    ``sqlite:///relative/path/to/foo.db``

The tool has five **COMMAND** options:

``create``
    insert records in the DB by parsing MEDLINE XML files or
    by downloading PubMed XML from NCBI eUtils for a list of PMIDs
``write``
    write records as plaintext files to a directory, each file named as
    "<pmid>.txt", and containing most of the DB stored content or just the
    TIAB (title and abstract)
``update``
    insert or update records in the DB (instead of creating them); note that
    if a record exists, but is added with ``create``, this would throw an
    `IntegrityError`. If you are not sure if the records are in the DB or
    not, use ``update`` (N.B. that ``update`` is slower).
``delete``
    delete records from the DB for a list of PMIDs
``dump``
    does not interact with the DB, but rather creates ".tab" files for each
    table that later can be used to load a database, particularly useful when
    bootstrapping a large collection

For example, to download two PubMed records by PMID and put them into
the DB::

    fnlmedline.py create 1000 123456

To insert a MEDLINE XML file into the DB::

    fnlmedline.py create medline.xml

Write out flat-files for dumping large collections::

    fnlmedline.py parse medline*.xml.gz

Note that in the last example, because of the suffix ".gz", the parser
automatically decompresses the file(s) first. This feature *only*
works with GNU-zipped files **and** requires the ".gz" suffix.

Therefore, command line arguments are treated as follows:

integer values
    are always treated as PMIDs to download PubMed XML data
all other values
    are always treated as MEDLINE XML files to parse
values ending in ".gz"
    are always treated as gzipped MEDLINE XML files
