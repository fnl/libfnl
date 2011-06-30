#!/usr/bin/env python3

"""Create PubMed/MEDLINE documents with attached abstracts in a Couch DB."""

import logging
import os
import sys
from libfnl.couch import COUCHDB_URL, Server
from libfnl.nlp.medline import ABSTRACT_FILE, Dump

__author__ = "Florian Leitner"
__version__ = "0.1"

CREATE = 1
READ = 2
UPDATE = 3
REPLACE = 4
DELETE = 5

def main(pmids:list, action:int=CREATE, couch_db:str=COUCHDB_URL,
         database:str='medline'):
    db = Server(couch_db)[database]
    checked = False

    if not pmids and action in (UPDATE, READ):
        pmids = list(db) # read/update all records...
        checked = True

    logging.info("processing %i PMIDs", len(pmids))

    if action is DELETE:
        for id in pmids:
            if checked or id in db: del db[id]
            else: logging.warn("PMID {} not in DB".format(id))
    elif action is READ:
        for id in pmids:
            if checked or id in db:
                att = db.getAttachment(id, ABSTRACT_FILE)
                file = open("{}.txt".format(id), mode='w', encoding='utf-8')
                file.write(att.data)
                file.close()
            else:
                logging.warn("PMID {} not in DB".format(id))
    else:
        Dump(pmids, db, action is UPDATE, action is REPLACE)

    return 0

if __name__ == '__main__':
    from optparse import OptionParser

    usage = "%prog [options] <infile or PMID>..."
    epilog = "infile format: newline-separated lists of PMIDs"

    parser = OptionParser(
        usage=usage, version=__version__, description=__doc__,
        prog=os.path.basename(sys.argv[0]), epilog=epilog
    )

    parser.set_defaults(loglevel=logging.WARNING)
    parser.set_defaults(action=CREATE)

    parser.add_option(
        "-x", "--read", action="store_const", const=READ, dest="action",
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
        "-f", "--replace", action="store_const", const=REPLACE, dest="action",
        help="download all records, even if they are stored already"
    )
    parser.add_option(
        "-d", "--delete", action="store_const", const=DELETE, dest="action",
        help="delete records from the database"
    )
    parser.add_option(
        "--couch-db", help="URL of the Couch Server [{}]".format(COUCHDB_URL)
    )
    parser.add_option(
        "--database", help="name of the Couch DB to use [medline]"
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

    pmids = []

    for item in args:
        try:
            if os.path.isfile(item):
                with open(item) as infile:
                    pmids.extend(str(int(line)) for line in infile)
            else:
                pmids.append(str(int(item)))
        except ValueError:
            parser.error("{} not PMID or file".format(item))
        except IOError:
            parser.error("could not read {}".format(item))

    logging.basicConfig(
        filename=opts.logfile, level=opts.loglevel,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s"
    )

    kwds = opts.__dict__
    del kwds["logfile"]
    del kwds["loglevel"]
    sys.exit(main(list(set(pmids)), **kwds))
