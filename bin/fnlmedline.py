#!/usr/bin/env python3
"""Maintain a MEDLINE/PubMed repository:

"parse"   PubMed XML files into raw table files for DB dumping -
"insert"  PubMed XML files or a list of PMIDs (contacting EUtils) into the DB
          (but slower than using "parse" and a DB dump) -
"update"  existing or add new records from PubMed XML files or a list of PMIDs (slow!) -
"write"   DB records to a directory starting from a given list of PMIDs -
"delete"  records from the DB for a given list of PMIDs"""
import logging
import os
import sys

from sqlalchemy.exc import OperationalError


__author__ = 'Florian Leitner'
__version__ = '1'


def Main(command, files_or_pmids, session, uniq=False):
    """
    :param command: one of create/read/update/delete
    :param files_or_pmids: the list of files or PMIDs to process
    :param session: the DB session
    :param uniq: flag to skip duplicate records on insert
    """
    from libfnl.medline.crud import insert, select, update, delete

    if command == 'insert':
        return insert(session, files_or_pmids, uniq)
    elif command == 'write':
        return select(session, [int(i) for i in files_or_pmids])
    elif command == 'update':
        return update(session, files_or_pmids)
    elif command == 'delete':
        return delete(session, [int(i) for i in files_or_pmids])


def WriteRecords(query, tiab:bool, output_dir:str):
    for rec in query:
        logging.debug("writing%s PMID %i", " TIAB from" if tiab else "", rec.pmid)
        file = open(os.path.join(output_dir, "{}.txt".format(rec.pmid)), 'wt')
        WriteSection(file, rec, 'Title')

        if not tiab:
            WriteSection(file, rec, 'Vernacular')

            for author in rec.authors:
                print(author.fullName(), file=file)

            print('', file=file)

        for sec in ('Abstract', 'Background', 'Objective', 'Methods', 'Results',
                    'Conclusions', 'Unlabelled'):
            WriteSection(file, rec, sec)

        if not tiab:
            WriteSection(file, rec, 'Copyright')
            for desc in rec.descriptors:
                print('+' if desc.major else '-', desc.name, file=file)
                for qual in desc.qualifiers:
                    print('+' if qual.major else '-', qual.name, file=file)
                print('', file=file)
            for ns, i in rec.identifiers.items():
                print('{}:{}'.format(ns, i.value), file=file)


def WriteSection(file, rec, sec):
    for s in rec.sections:
        if s.name == sec:
            if (s.label is not None):
                print(s.label, file=file)
            print(s.content, end='\n\n', file=file)


if __name__ == '__main__':
    from argparse import ArgumentParser
    from libfnl.medline.orm import InitDb, Session

    epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())

    parser = ArgumentParser(
        usage='%(prog)s [options] URL CMD FILE/PMID ...',
        description=__doc__, epilog=epilog,
        prog=os.path.basename(sys.argv[0])
    )

    parser.set_defaults(loglevel=logging.WARNING)

    parser.add_argument(
        'url', metavar='URL', help='a database URL string'
    )
    parser.add_argument(
        'command', metavar='CMD', help='command: [parse|insert|write|update|delete]'
    )
    parser.add_argument(
        'files', metavar='FILE/PMID', nargs='+', help='MEDLINE XML files or PMIDs'
    )
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--tiab', action='store_true', help='write only title/abstract')
    parser.add_argument(
        '--uniq', action='store_true',
        help='do not insert/dump duplicate records'
    )
    parser.add_argument(
        '--pmid-lists', action='store_true',
        help='assume input files are lists of PMIDs, not XML files'
    )
    parser.add_argument(
        '--output', metavar='DIR', default=os.path.curdir,
        help='dump/write to a specific directory'
    )
    parser.add_argument(
        '--error', action='store_const', const=logging.ERROR,
        dest='loglevel', help='error log level only [warn]'
    )
    parser.add_argument(
        '--info', action='store_const', const=logging.INFO,
        dest='loglevel', help='info log level [warn]'
    )
    parser.add_argument(
        '--debug', action='store_const', const=logging.DEBUG,
        dest='loglevel', help='debug log level [warn]'
    )
    parser.add_argument('--logfile', metavar='FILE', help='log to file, not STDERR')

    args = parser.parse_args()
    logging.basicConfig(
        filename=args.logfile, level=args.loglevel,
        format='%(asctime)s %(name)s %(levelname)s: %(message)s'
    )

    if args.command not in ('parse', 'write', 'insert', 'update', 'delete'):
        parser.error('illegal command "{}"'.format(args.command))

    if args.pmid_lists:
        args.files = [int(line) for f in args.files for line in open(f)]

    if (args.command == 'parse'):
        from libfnl.medline.crud import dump
        result = dump(args.files, args.output, args.uniq)
    else:
        try:
            InitDb(args.url)
        except OperationalError as e:
            parser.error(str(e))

        result = Main(args.command, args.files, Session(), args.uniq)

        if args.command == 'write':
            WriteRecords(result, args.tiab, args.output)
            result = True

    sys.exit(0 if result else 1)
