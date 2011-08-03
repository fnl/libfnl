#!/usr/bin/env python3

"""Create PubMed/MEDLINE documents with attached abstracts in a Couch DB."""
from _socket import error

import logging
import os
import sys
from libfnl.couch import COUCHDB_URL, Server
from libfnl.couch.network import ResourceNotFound
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

def main(pmids:list, action:int=CREATE, couchdb_url:str=COUCHDB_URL,
         database:str='medline', encoding:str='utf-8',
         force:bool=False) -> int:
    logging.info("%sing %i %s%s in %s/%s", ACTIONS[action], len(pmids),
                 'PMIDs' if action else 'files',
                 ' (forced)' if force else '', couchdb_url, database)
    try:
        db = Server(couchdb_url)[database]
    except error:
        logging.error('cannot connect to %s', couchdb_url)
        return 1
    
    checked = False
    done = 0

    if action == ATTACH:
        done = sum(len(i) for i in Attach(pmids, db, encoding, force).values())
    else:
        if not pmids and action in (UPDATE, READ):
            # read/update all records...
            pmids = [id for id in db if len(id) <= 10 and id.isdigit()]

        if action is DELETE:
            for id in pmids:
                try:
                    del db[id]
                    done += 1
                except ResourceNotFound:
                    logging.warn("PMID {} not in DB".format(id))
                    print(id, file=sys.stderr)
        elif action is READ:
            for id in pmids:
                try:
                    text = db[id]['text']
                except ResourceNotFound:
                    logging.warn("PMID %s not in DB", id)
                    print(id, file=sys.stderr)
                except KeyError:
                    logging.warn("PMID %s has no text", id)
                    print(id, file=sys.stderr)
                else:
                    try:
                        file = open("{}.txt".format(id), mode='w',
                                    encoding='utf-8')
                        file.write(text)
                        file.close()
                        done += 1
                    except IOError:
                        logging.warn("could not write %s.txt", id)
                        print(id, file=sys.stderr)
        else:
            done, failed_ids = Dump(pmids, db, action is UPDATE, force)

            for id in failed_ids:
                print(id, file=sys.stderr)

    logging.info("%sed %i %s", ACTIONS[action], done,
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
        help="upload files that are related to MEDLINE records; the files' "\
             "names (w/o extension) must be the PMIDs to attach to, eg., "\
             "1234567.html; use --force to replace sections on existing files"
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
        "--couchdb-url", default=COUCHDB_URL,
        help="COUCHDB_URL [%default]"
    )
    parser.add_option(
        "--database", default='medline',
        help="Couch DB name [%default]"
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
    pmid_list = []

    if opts.action == ATTACH:
        for item in args:
            if not os.path.isfile(item):
                parser.error('{} not a file'.format(item))

            base = os.path.basename(item)
            pmid, ext = os.path.splitext(base)

            if not pmid.isdigit():
                parser.error('name {} of {} not a PMID'.format(pmid, item))

        pmid_list = args
    else:
        for item in args:
            if os.path.isfile(item):
                found = len(pmid_list)

                try:
                    with open(item) as file:
                        pmid_list.extend(pmid.strip() for pmid in file if
                                      pmid.strip().isdigit())
                except IOError:
                    parser.error("could not read {}".format(item))

                found = len(pmid_list) - found
                if not found: parser.error('no PMIDs in {}'.format(item))
                else: logging.info('read %s PMIDs from %s', found, item)
            elif item.isdigit():
                pmid_list.append(item)
            else:
                parser.error("{} not a PMID or file".format(item))

    sys.exit(main(list(frozenset(pmid_list)), **kwds))
