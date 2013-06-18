"""
.. py:module:: libmedlinedb.crud
   :synopsis: I/O CRUD to manage a MEDLINE/PubMed DB.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging

from gzip import open as gunzip
from os.path import join
from io import TextIOWrapper
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from libfnl.medline.orm import Medline, Section, Descriptor, Qualifier, Author, Identifier
from libfnl.medline.parser import Parse
from libfnl.medline.web import Download


def _createOrMerge(session:Session, files_or_pmids:iter, update):
    pmid_buffer = []
    count = 0
    initial = session.query(Medline).count()
    pubmed = True

    try:
        for arg in files_or_pmids:
            try:
                pmid = int(arg)
                pmid_buffer.append(pmid)
                stream = Download(pmid_buffer) if (len(pmid_buffer) == 100) else None
            except ValueError:
                logging.debug("reading infile %s", arg)
                pubmed = False
                if arg.lower().endswith('.gz'):
                    # use wrapper to support pre-3.3
                    stream = TextIOWrapper(gunzip(arg, 'r'))
                else:
                    stream = open(arg)

            if stream is not None:
                pmid_buffer = []
                for i in Parse(stream, pubmed=pubmed):
                    count += 1
                    update(i)
                pubmed = True

        if len(pmid_buffer):
            for i in Parse(Download(pmid_buffer), pubmed=True):
                count += 1
                update(i)

        session.commit()
        final = session.query(Medline).count()
        logging.info("parsed %i entities (records before/after: %i/%i)",
                     count, initial, final)
        return True
    except IntegrityError as e:
        logging.info(str(e))
        logging.fatal('non-unique Entities added to DB')
        session.rollback()
        return False
    except Exception as e:
        logging.exception('create failed')
        if session.dirty:
            session.rollback()
        return False


def create(session:Session, files_or_pmids:iter) -> bool:
    "Create all records in the *files* (paths) or download the *PMIDs*."
    _createOrMerge(session, files_or_pmids, lambda i: session.add(i))


def read(session:Session, pmids:list([int])) -> iter([Medline]):
    "Return an iterator over all `Medline` records for the *PMIDs*."
    count = 0
    # noinspection PyUnresolvedReferences
    for record in session.query(Medline).filter(Medline.pmid.in_(pmids)):
        count += 1
        yield record
    logging.info("wrote %i records", count)


def dump(files:iter, output_dir:str) -> bool:
    "Parse MEDLINE XML files into tabular flat-files for each DB table."
    out_stream = {
        Medline.__tablename__: open(join(output_dir, "records.tab"), "wt"),
        Section.__tablename__: open(join(output_dir, "sections.tab"), "wt"),
        Descriptor.__tablename__: open(join(output_dir, "descriptors.tab"), "wt"),
        Qualifier.__tablename__: open(join(output_dir, "qualifiers.tab"), "wt"),
        Author.__tablename__: open(join(output_dir, "authors.tab"), "wt"),
        Identifier.__tablename__: open(join(output_dir, "identifiers.tab"), "wt"),
    }
    count = 0

    for f in files:
        if f.lower().endswith('.gz'):
            # use wrapper to support pre-3.3
            in_stream = TextIOWrapper(gunzip(f, 'r'))
        else:
            in_stream = open(f)

        for i in Parse(in_stream):
            out_stream[i.__tablename__].write(str(i))

            if i.__tablename__ == Medline.__tablename__:
                count += 1

    for stream in out_stream.values():
        stream.close()

    logging.info("parsed %i records", count)


def update(session:Session, files_or_pmids:iter) -> bool:
    "Update all records in the *files* (paths) or download the *PMIDs*."
    _createOrMerge(session, files_or_pmids, lambda i: session.merge(i))


# noinspection PyUnusedLocal
def delete(session:Session, pmids:list([int])) -> bool:
    "Delete all records for the *PMIDs*."
    # noinspection PyUnresolvedReferences
    count = session.query(Medline).filter(Medline.pmid.in_(pmids)).delete(
        synchronize_session=False
    )
    session.commit()
    logging.info("deleted %i records", count)
    return True
