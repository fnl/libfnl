"""
.. py:module:: libfnl.gnamed.parsers.hgnc
   :synopsis: A HGNC (genenames.org) parser.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import io
import logging

from collections import namedtuple
from shlex import shlex

from libfnl.gnamed.constants import Species, Namespace
from libfnl.gnamed.loader import GeneRecord, AbstractLoader, DBRef, DuplicateEntityError
from libfnl.gnamed.orm import GeneRef
from sqlalchemy.orm.exc import NoResultFound

Line = namedtuple('Line', [
    'id', 'symbol', 'name',
    'previous_symbols', 'previous_names', 'synonyms', 'name_synonyms',
    'location', 'pmids',
    'gene_family_symbols', 'gene_family_names',
    Namespace.entrez, 'Namespace_ensemble', Namespace.mgd,
    Namespace.uniprot, Namespace.rgd
])

DB_REFS = [Namespace.entrez,
           Namespace.uniprot]
FIX_ACCESSION = frozenset({Namespace.mgd, Namespace.rgd})

# Mapping of references to other DBs that are not correct to their
# right IDs; This mostly is about HGNC linking to wrong Entrez Gene IDs.
WRONG_DB_REFS = {
    #DBRef(Namespace.entrez, ''): DBRef(Namespace.entrez, ''),
    # HGNC:3633
    DBRef(Namespace.entrez, '619190'): DBRef(Namespace.entrez, '392063'),
    # HGNC:9135
    DBRef(Namespace.entrez, '100132832'): DBRef(Namespace.entrez, '5391'),
    # HGNC:10300
    DBRef(Namespace.entrez, '100288252'): DBRef(Namespace.entrez, '54030'),
    # HGNC:18906 maps to KRTAP2-4, but should map to -3; Entrez has the correct
    # mapping back to HGNC:
    DBRef(Namespace.entrez, '730755'): DBRef(Namespace.entrez, '85295'),
    # HGNC:20616
    DBRef(Namespace.entrez, '448990'): DBRef(Namespace.entrez, '338397'),
    # HGNC:31023
    DBRef(Namespace.entrez, '100287637'): DBRef(Namespace.entrez, '654504'),
    # HGNC:31420
    DBRef(Namespace.entrez, '100129250'): DBRef(Namespace.entrez, '548324'),
    # HGNC:32000
    DBRef(Namespace.entrez, '100288142'): DBRef(Namespace.entrez, '641590'),
    # HGNC:32062
    DBRef(Namespace.entrez, '100506642'): DBRef(Namespace.entrez, '574432'),
    # HGNC:32078 and 32077 have the links to Entrez convoluted/inverted;
    # Entrez has the correct mappings for the two genes:
    DBRef(Namespace.entrez, '574445'): DBRef(Namespace.entrez, '574446'),
    DBRef(Namespace.entrez, '574446'): DBRef(Namespace.entrez, '574445'),
    # HGNC:32284
    DBRef(Namespace.entrez, '100132396'): DBRef(Namespace.entrez, '441330'),
    # HGNC:32409 should map to TBC1D3P4, not TBC1D3P; Entrez has the correct
    # mapping back to HGNC:
    DBRef(Namespace.entrez, '100631253'): DBRef(Namespace.entrez, '653018'),
    # HGNC:32473 maps to ZNF479, but should map to ZNF733; Entrez has the
    # correct mapping back to HGNC:
    DBRef(Namespace.entrez, '643955'): DBRef(Namespace.entrez, '100170646'),
    # HGNC:37758
    DBRef(Namespace.entrez, '100420293'): DBRef(Namespace.entrez, '80699'),
    }


class Parser(AbstractLoader):
    """
    A parser for HGNC (genenames.org) records.

    Implements the `AbstractParser._parse` method.
    """

    def _setup(self, stream:io.TextIOWrapper):
        lines = super(Parser, self)._setup(stream)
        logging.debug('correcting wrong links by Entrez')

        try:
            hgnc = self.session.query(GeneRef).filter(
                GeneRef.namespace == Namespace.hgnc,
                GeneRef.accession == '31739').one()
            entrez = self.session.query(GeneRef).filter(
                GeneRef.namespace == Namespace.entrez,
                GeneRef.accession == '648809').one()

            if hgnc.id != entrez.id:
                hgnc.id = entrez.id
                logging.info(
                    'correcting wrong link of %s:31739 from %s:388159 to %s:648809'
                    , Namespace.hgnc, Namespace.entrez, Namespace.entrez)
                self.session.commit() # commit, because otherwise multiple
                # parsers would hang here waiting for each others commit
        except NoResultFound:
            pass

        logging.debug("file header:\n%s", stream.readline().strip())
        return lines + 1

    def _parse(self, line:str):
        items = [i.strip() for i in line.split('\t')]
        assert len(items) > 1, line

        for idx in range(len(items)):
            if items[idx] == '-':
                items[idx] = ''

        while len(items) < 16:
            items.append('')

        row = Line._make(items)
        record = GeneRecord(Species.human, symbol=row.symbol, name=row.name,
                            location=row.location if row.location else None)
        db_key = DBRef(Namespace.hgnc, row.id)
        record.addDBRef(db_key)

        # link DB references
        for ns in DB_REFS:
            acc = getattr(row, ns)

            if acc:
                if ns in FIX_ACCESSION:
                    # noinspection PyUnresolvedReferences
                    acc = acc[acc.find(":") + 1:]

                ref = DBRef(ns, acc)

                if ref in WRONG_DB_REFS:
                    new_ref = WRONG_DB_REFS[ref]
                    logging.info('correcting wrong ref %s->%s',
                                 '{}:{}'.format(*ref),
                                 '{}:{}'.format(*new_ref))
                    ref = new_ref

                record.addDBRef(ref)

        # parse symbol strings
        for field in (row.previous_symbols, row.synonyms):
            if field:
                for symbol in Parser._parseCD(field):
                    record.addSymbol(symbol)

        # parse name strings
        for field in (row.previous_names, row.name_synonyms):
            if field:
                for name in Parser._parseQCD(field):
                    record.addName(name)

        # parse keywords strings
        if row.gene_family_symbols:
            for kwd in Parser._parseCD(row.gene_family_symbols):
                record.addKeyword(kwd)

        # location with ALT_REF_LOCI values - eliminate them
        if row.location and " ALT_REF_LOCI" in row.location:
            record.location = row.location[:row.location.find(" ALT_REF_LOCI")]

        for name in Parser._parseQCD(row.gene_family_names):
            for subname in name.split(' / '):
                for subsubname in subname.split(' : '):
                    subsubname = subsubname.strip()

                    if subsubname.lower() not in ('other', '"other"'):
                        record.addKeyword(subsubname)

        try:
            self._loadRecord(db_key, record)
        except DuplicateEntityError:
            if len(record.refs) == 2:
                # assume all HGNC links that do not coincide with the
                # Entrez back-link are bad, as it seems it is mostly
                # HGNC that is not up-to-date.
                logging.warn('removing likely bad Entrez ref in %s:%s',
                             *db_key)
                assert any(r.namespace == Namespace.entrez
                    for r in record.refs), record.refs
                record.refs = {r for r in record.refs if
                               r.namespace == Namespace.hgnc}
                assert len(record.refs) == 1, record.refs
                self._loadRecord(db_key, record)
            else:
                raise

        return 1

    def _cleanup(self, file:io.TextIOWrapper):
        records = super(Parser, self)._cleanup(file)
        return records

    @staticmethod
    def _parseQCD(content:str) -> shlex:
        parser = shlex(content, posix=True)
        parser.whitespace += ','
        parser.whitespace_split = True

        for value in parser:
            value = value.strip()

            if value:
                yield value

    @staticmethod
    def _parseCD(content:str) -> shlex:
        for value in content.split(','):
            value = value.strip()

            if value:
                yield value

