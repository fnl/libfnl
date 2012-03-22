#!/usr/bin/env python3

"""Create PubMed/MEDLINE documents with attached abstracts in a Couch DB."""
from _socket import error

import logging
import os
import re
import sys
from libfnl.couch import COUCHDB_URL, Server
from libfnl.couch.network import ResourceNotFound
from libfnl.couch.serializer import Encode
from libfnl.nlp.medline import Attach, Dump, ABSTRACT_ELEMENTS

__author__ = "Florian Leitner"
__version__ = "0.1"

ATTACH = 0
CREATE = 1
READ = 2
UPDATE = 3
DELETE = 4
READ_ATT = 5

ACTIONS = {
    ATTACH: 'attach',
    CREATE: 'creat',
    READ: 'extract',
    UPDATE: 'updat',
    DELETE: 'delet',
    READ_ATT: 'extract',
}

NULL_VALUE = '\\N'

def main(pmids:list, action:int=CREATE, couchdb_url:str=COUCHDB_URL,
         database:str='medline', encoding:str='utf-8', extract_fields=None,
         force:bool=False) -> int:
    logging.info("%sing %i %s%s in %s/%s", ACTIONS[action], len(pmids),
                 'PMIDs' if action else 'files',
                 ' (forced)' if force else '', couchdb_url, database)
    try:
        db = Server(couchdb_url)[database]
    except error:
        logging.error('cannot connect to %s', couchdb_url)
        return 1

    done = 0

    if action is READ and extract_fields:
        # Print the TSV table header as the field names
        print('PMID\t{}'.format('\t'.join(extract_fields)))

        for idx in range(len(extract_fields)):
            extract_fields[idx] = [int(f) if f.isnumeric() else f
                                   for f in extract_fields[idx].split('/')]

    if action == ATTACH:
        # "attach" (fulltext) files to PubMed records in the DB
        done = sum(len(i) for i in Attach(pmids, db, encoding, force).values())
    else:
        if not pmids and action in (UPDATE, READ, READ_ATT):
            # command to read/update *all* records: collect the known PMIDs
            pmids = [id for id in db if len(id) <= 10 and id.isdigit()]

        if action is DELETE:
            # delete PubMed records from the DB
            for id in pmids:
                try:
                    del db[id]
                    done += 1
                except ResourceNotFound:
                    logging.warn("PMID {} not in DB".format(id))
                    print(id, file=sys.stderr)
        elif action is READ:
            # read PubMed records from the DB (and write to file system)
            for id in pmids:
                try:
                    record = db[id]
                except ResourceNotFound:
                    logging.warn("PMID %s not in DB", id)
                    print(id, file=sys.stderr)
                else:
                    if extract_fields:
                        values = Extract(record, extract_fields)
                        print('{}'.format('\t'.join(values)))
                        done += 1
                    else:
                        try:
                            text = record['text']
                        except KeyError:
                            logging.warn("PMID %s has no text", id)
                            print(id, file=sys.stderr)
                        else:
                            done += WriteFile('{}.txt'.format(id),
                                              text, encoding, id)
        elif action is READ_ATT:
            # read attachment plain-text from the DB (and write to file system)
            for id in pmids:
                try:
                    rows = list(db.view('attachment/xrefs', key=id))
                except ResourceNotFound:
                    logging.error('attachment/xrefs view not installed')
                    return 1

                for r in rows:
                    try:
                        text = db[r.id]['text']
                    except KeyError:
                        logging.warn("attachment %s has no text", r.id)
                        print('{}@{}'.format(id, r.id), file=sys.stderr)
                    else:
                        done += WriteFile('{}.{}.txt'.format(id, r.id),
                                          text, encoding,
                                          '{}@{}'.format(id, r.id))
        else:
            # create/update PubMed records in the DB
            done, failed_ids = Dump(pmids, db, action is UPDATE, force)

            for id in failed_ids:
                print(id, file=sys.stderr)

    logging.info("%sed %i %s", ACTIONS[action], done,
                 'PMIDs' if action else 'files')

    return 0

def Extract(doc, fields):
    """
    Extract the given *fields* from the *doc* and return these fields'
    values.

    :param doc: a PubMed/MEDLINE :class:`libfnl.couch.broker.Document` from the
                DB
    :param fields: a list of lists with the paths to each field to extract
    :return: a list of strings; if the value is an integer or float, it is
             given unquoted; if the field value was not a string, it is
             JSON-encoded and quoted; otherwise, it is the quoted string value
    """
    data = [doc.id]

    for f_path in fields:
        val = doc

        for f in f_path:
            try:
                val = val[f]
            except KeyError:
                logging.warn("PMID %s has no field '%s' in %s",
                             doc.id, f, f_path)
                val = None

        if val is None:
            data.append(NULL_VALUE)
            continue

        if f_path == ['Article', 'Abstract']:
            val = '\n\n'.join([val[key] for key in ABSTRACT_ELEMENTS
                               if key in val])

        if not isinstance(val, str): val = Encode(val)

        if val.isnumeric():
            pass # an integer value - nothing to do
        elif re.match('\d*\.\d+', val, re.A):
            pass # a float value - nothing to do, either
        else:
            # a string value - replace newlines, tabs, quotes
            val = val.replace('\n', '\\n')
            val = val.replace('\t', '\\t')
            val = val.replace('"', '\\"')
            # surround the string with quotes
            val = '"{}"'.format(val)

        data.append(val)

    return data

def WriteFile(name, text, encoding, id):
    try:
        file = open(name, mode='w', encoding=encoding)
        file.write(text)
        file.close()
        return 1
    except IOError:
        logging.warn('could not write %s', name)
        print(id, file=sys.stderr)
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
        "-r", "--read", action="store_const", const=READ, dest="action",
        help="save the abstracts (incl. titles) of existing records to files "\
             "named <PMID>.txt in the current directory; "\
             "extracts all records if no PMIDs are given"
    )
    parser.add_option(
        "--read-attachments", action="store_const", const=READ_ATT,
        dest="action",
        help="save the attachment texts of existing records to files "\
             "named <PMID>.<ATT_ID>.txt in the current directory; "\
             "extracts all attachment texts if no PMIDs are given"
    )
    parser.add_option(
        "-u", "--update", action="store_const", const=UPDATE, dest="action",
        help="update records that are likely to have been revised or "\
             "completed; updates all records if no PMIDs are given; " \
             "use --force to update all records"
    )
    parser.add_option(
        "-d", "--delete", action="store_const", const=DELETE, dest="action",
        help="delete records from the database"
    )
    parser.add_option(
        "-a", "--attach", action="store_const", const=ATTACH, dest="action",
        help="upload files that are related to MEDLINE records; the files' "\
             "names (w/o extension) should be the PMIDs to attach to, eg., "\
             "1234567.html; use --force to replace existing attachments"
    )
    parser.add_option(
        "-f", "--force", action="store_true", default=False,
        help="force writing documents, even if they are stored already"
    )
    parser.add_option(
        "-x", "--extract-fields", action="append",
        help="one or more fields to extract as TSV (using --read); "\
             "the field's path should be separated by slashes; to extract "\
             "the entire abstract as a single field, use Article/Abstract"
    )
    parser.add_option(
        "--encoding", action="store", default="utf-8",
        help="the encoding of the files to attach or write [%default]"
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
