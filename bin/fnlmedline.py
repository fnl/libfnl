#!/usr/bin/env python3

"""Create PubMed/MEDLINE documents with attached abstracts in a Couch DB."""

import logging
import os
import sys
from libfnl.couch import COUCHDB_URL, Server
from libfnl.nlp.medline import ABSTRACT_FILE, Attach, Dump

__author__ = "Florian Leitner"
__version__ = "0.1"

ATTACH = 0
CREATE = 1
READ = 2
UPDATE = 3
DELETE = 4

ACTIONS = {
    0: 'attach',
    1: 'creat',
    2: 'extract',
    3: 'updat',
    4: 'delet',
}

def main(pmids:list, action:int=CREATE, couch_db:str=COUCHDB_URL,
         database:str='medline', encoding:str='utf-8',
         force:bool=False) -> int:
    logging.info("%sing %i %s%s in %s/%s", ACTIONS[action], len(pmids),
                 'PMIDs' if action else 'files',
                 ' (forced)' if force else '', couch_db, database)
    db = Server(couch_db)[database]
    checked = False
    processed_docs = 0

    if action == ATTACH:
        processed_docs = sum(len(i) for i in
                             Attach(pmids, db, encoding, force).values())
    else:
        if not pmids and action in (UPDATE, READ):
            # read/update all records...
            pmids = [id for id in db if len(id) != 64 and id.isdigit()]
            checked = True

        if action is DELETE:
            for id in pmids:
                if checked or id in db:
                    del db[id]
                    processed_docs += 1
                else:
                    logging.warn("PMID {} not in DB".format(id))
        elif action is READ:
            for id in pmids:
                if checked or id in db:
                    att = db.getAttachment(id, ABSTRACT_FILE)
                    file = open("{}.txt".format(id), mode='w',
                                encoding='utf-8')
                    file.write(att.data)
                    file.close()
                    processed_docs += 1
                else:
                    logging.warn("PMID {} not in DB".format(id))
        else:
            processed_docs = Dump(pmids, db, action is UPDATE, force)

    logging.info("%sed %i %s", ACTIONS[action], processed_docs,
                 'PMIDs' if action else 'files')

    return 0


if __name__ == '__main__':
    from optparse import OptionParser

    usage = "%prog [options] <infile or PMID>..."
    epilog = "infile format: newline-separated lists of PMIDs; "\
             "attachments: HTML or text"

    parser = OptionParser(
        usage=usage, version=__version__, description=__doc__,
        prog=os.path.basename(sys.argv[0]), epilog=epilog
    )

    parser.set_defaults(loglevel=logging.WARNING)
    parser.set_defaults(action=CREATE)

    parser.add_option(
        "-c", "--create", action="store_const", const=CREATE, dest="action",
        help="only create records if they do not exist already [default]"
    )
    parser.add_option(
        "-r", "--extract", action="store_const", const=READ, dest="action",
        help="save the abstracts (incl. titles) of existing records to files "\
             "named <PMID>.txt in the current directory; "\
             "extracts all records if no arguments"
    )
    parser.add_option(
        "-u", "--update", action="store_const", const=UPDATE, dest="action",
        help="update records that are likely to have been revised or "\
             "completed; updates all records if no arguments"
    )
    parser.add_option(
        "-d", "--delete", action="store_const", const=DELETE, dest="action",
        help="delete records from the database"
    )
    parser.add_option(
        "-a", "--attach", action="store_const", const=ATTACH, dest="action",
        help="upload files that are attached to MEDLINE records; the files' "\
             "names (w/o extension) must be the PMIDs to attach to, eg., "\
             "1234567.html"
    )
    parser.add_option(
        "-f", "--force", action="store_true", default=False,
        help="force writing documents, even if they are stored already"
    )
    parser.add_option(
        "--encoding", action="store", default="utf-8",
        help="the encoding of the files too attach [%default]"
    )
    parser.add_option(
        "--couch-db", default=COUCHDB_URL,
        help="URL of the Couch Server [%default]"
    )
    parser.add_option(
        "--database", default='medline',
        help="name of the Couch DB to use [%default]"
    )
    parser.add_option(
        "--error", action="store_const", const=logging.ERROR,
        dest="loglevel", help="error log level only [warn]"
    )
    parser.add_option(
        "--info", action="store_const", const=logging.INFO,
        dest="loglevel", help="info log level [warn]"
    )
    parser.add_option(
        "--debug", action="store_const", const=logging.DEBUG,
        dest="loglevel", help="debug log level [warn]"
    )
    parser.add_option("--logfile", help="log to file, not STDERR")

    opts, args = parser.parse_args()
    if len(args) < 1 and opts.action not in (UPDATE, READ):
        parser.error("no input files or PMIDs")

    logging.basicConfig(
        filename=opts.logfile, level=opts.loglevel,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s"
    )
    kwds = opts.__dict__
    del kwds["logfile"]
    del kwds["loglevel"]
    pm_ids = []

    if opts.action == ATTACH:
        for item in args:
            if not os.path.isfile(item):
                parser.error('{} not a file'.format(item))

            base = os.path.basename(item)
            pmid, ext = os.path.splitext(base)

            if not pmid.isdigit():
                parser.error('name {} of {} not a PMID'.format(pmid, item))

        pm_ids = args
    else:
        for item in args:
            if os.path.isfile(item):
                found = len(pm_ids)

                try:
                    with open(item) as file:
                        pm_ids.extend(pmid for pmid in file if pmid.isdigit())
                except IOError:
                    parser.error("could not read {}".format(item))

                found = len(pm_ids) - found
                if not found: parser.error('no PMIDs in ()'.format(item))
                else: logging.info('read %s PMIDs from %s', found, item)
            elif item.isdigit():
                pm_ids.append(item)
            else:
                parser.error("{} not a PMID or file".format(item))

    sys.exit(main(list(frozenset(pm_ids)), **kwds))
