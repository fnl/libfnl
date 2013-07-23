"""
.. py:module:: libfnl.gnamed.parsers.mgd
   :synopsis: A MGI (Mouse Genome Informatics) Database (MGD) file parser.

`ftp://ftp.informatics.jax.org/pub/reports/index.html`_

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import io
import logging

from collections import namedtuple

from libfnl.gnamed.constants import Species, Namespace
from libfnl.gnamed.loader import GeneRecord, AbstractLoader, DBRef, DuplicateEntityError

List1_Line = namedtuple('List1_Line', [
    'id', 'chromosome', 'cM_position', 'start', 'end', 'strand', 'symbol',
    'status', 'name', 'marker_type', 'feature_types', 'synonyms'
])

SwissProt_TrEMBL_Line = namedtuple('SwissProt_TrEMBL_Line', [
    'id', 'symbol', 'status', 'name', 'cM_position', 'chromosome', 'accessions'
])

EntrezGene_Line = namedtuple('EntrezGene_Line', [
    'id', 'symbol', 'status', 'name', 'cM_position', 'chromosome',
    'marker_type',
    'accessions', 'gene_id', 'synonyms', 'feature_types', 'start',
    'end', 'strand', 'bio_types'
])


class Parser(AbstractLoader):
    """
    A parser for MGD (informatics.jax.org) records.

    Implements the `AbstractParser._parse` method.
    """

    def _setup(self, stream:io.TextIOWrapper):
        assert len(self.files) == 3,\
        'received {} files, expected 3'.format(len(self.files))
        lines = super(Parser, self)._setup(stream)

        if not hasattr(self, '_records'):
            self._records = dict()

        if not hasattr(self, '_fileno'):
            self._fileno = 0

        if stream.name.endswith('List1.rpt'):
            content = stream.readline().strip()
            lines += 1
            logging.debug("file header:\n%s", content)
            self._parse = self._parseList1
            self._fileno += 1
        elif stream.name.endswith('SwissProt_TrEMBL.rpt'):
            logging.debug('parsing UniProt links')
            self._parse = self._parseUniProt
            self._fileno += 1
        elif stream.name.endswith('EntrezGene.rpt'):
            logging.debug('parsing EntrezGene links')
            self._parse = self._parseEntrez
            self._fileno += 1
        else:
            raise RuntimeError('unknown MGD file "%s"'.format(stream.name))

        return lines

    @staticmethod
    def _toItems(line:str, num_items:int):
        count = 0

        for item in line.split('\t'):
            item = item.strip()
            count += 1

            if count == 1:
                assert item.startswith('MGI:'), item
                item = item[4:]

            if not item or item == '-':
                yield None
            else:
                yield item

        while count < num_items:
            count += 1
            yield None

    def _parseList1(self, line:str):
        if line.startswith('NULL'):
            return 0

        row = List1_Line._make(Parser._toItems(line, 12))
        db_key = DBRef(Namespace.mgd, row.id)
        record = self._getRecord(db_key)
        record.chromosome = row.chromosome

        # parse symbol strings
        if row.symbol:
            record.symbol = row.symbol
            record.addSymbol(row.symbol)

        if row.synonyms:
            for syn in row.synonyms.split('|'):
                record.addSymbol(syn.strip())

        # parse name strings
        if row.name:
            record.name = row.name
            record.addName(row.name)

        # parse keywords strings
        if row.marker_type:
            record.addKeyword(row.marker_type)

        if row.feature_types:
            for feat in row.feature_types.split('|'):
                record.addKeyword(feat.strip())

        logging.debug('parsed %s:%s (%s)', Namespace.mgd, row.id, row.symbol)
        return 1

    def _parseUniProt(self, line:str):
        row = SwissProt_TrEMBL_Line._make(Parser._toItems(line, 7))

        if row.accessions:
            db_key = DBRef(Namespace.mgd, row.id)
            record = self._getRecord(db_key)

            for acc in row.accessions.split():
                record.addDBRef(DBRef(Namespace.uniprot, acc))

            logging.debug('parsed links to UniProt: %s', row.accessions)

        return 1

    def _parseEntrez(self, line:str):
        row = EntrezGene_Line._make(Parser._toItems(line, 15))

        if row.gene_id:
            db_key = DBRef(Namespace.mgd, row.id)
            record = self._getRecord(db_key)
            ref = DBRef(Namespace.entrez, row.gene_id)
            record.addDBRef(ref)
            logging.debug('parsed link to %s:%s', *ref)

        return 1

    def _getRecord(self, db_key:DBRef):
        if db_key in self._records:
            record = self._records[db_key]
        else:
            logging.debug('creating a new record for %s:%s', *db_key)
            record = GeneRecord(Species.mouse)
            record.addDBRef(db_key)
            self._records[db_key] = record

        return record

    def _cleanup(self, file:io.TextIOWrapper):
        num_records = super(Parser, self)._cleanup(file)

        if self._fileno == 3:
            logging.info('loading %s parsed records', len(self._records))

            for db_key, record in self._records.items():
                try:
                    self._loadRecord(db_key, record)
                except DuplicateEntityError:
                    if len(record.refs) == 2:
                        # assume all MGI links that do not coincide with the
                        # Entrez back-link are bad, as it seems it is always
                        # (mostly?) MGI that is not up-to-date.
                        logging.info('removing likely bad Entrez ref in %s:%s',
                                     *db_key)
                        assert any(r.namespace == Namespace.entrez
                                   for r in record.refs), record.refs
                        record.refs = {r for r in record.refs if
                                       r.namespace == Namespace.mgd}
                        assert len(record.refs) == 1, record.refs
                        self._loadRecord(db_key, record)
                    else:
                        raise

        return num_records

