"""
.. py:module:: libfnl.gnamed.parsers.entrez
   :synopsis: A NCBI Entrez gene_info and gene2pubmed file parser.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
import io

from collections import namedtuple, defaultdict
from sqlalchemy.schema import Sequence

from libfnl.gnamed.constants import Namespace
from libfnl.gnamed.loader import GeneRecord, AbstractLoader, DBRef

Line = namedtuple('Line', [
    'species_id', 'id',
    'symbol', 'locus_tag', 'synonyms', 'dbxrefs', 'chromosome',
    'map_location', 'name', 'type_of_gene', 'nomenclature_symbol',
    'nomenclature_name', 'nomenclature_status', 'other_designations',
    'modification_date'
])

# name of each column on a Line (for debugging)
COLNAME = {
    0: 'species_id',
    1: 'id',
    2: 'symbol',
    3: 'locus_tag',
    4: 'synonyms',
    5: 'dbxrefs',
    6: 'chromosome',
    7: 'map_loaction',
    8: 'name',
    9: 'type_of_gene',
    10: 'nomenclature_symbol',
    11: 'nomenclature_name',
    12: 'nomenclature_status',
    13: 'other_designations',
    14: 'modification_date',
}

# frequently found names in Entrez that are just filler-trash
# fields: synonyms, name, nomenclature name, other designations
JUNK_NAMES = frozenset([
    'hypothetical protein',
    'polypeptide',
    'polyprotein',
    'predicted protein',
    'protein',
    'pseudo',
    'similar to predicted protein',
    'similar to conserved hypothetical protein',
    'similar to hypothetical protein',
    'similar to polypeptide',
    'similar to polyprotein',
    'similar to predicted protein',
    'unnamed',
])

# "translation" of dbxref names to the local Namespace names
TRANSLATE = {
    'ECOCYC': Namespace.ecocyc,
    'FLYBASE': Namespace.flybase,
    'HGNC': Namespace.hgnc,
    'MGI': Namespace.mgd,
    'RGD': Namespace.rgd,
    'SGD': Namespace.sgd,
    'TAIR': Namespace.tair,
    'WormBase': Namespace.wormbase,
    'Xenbase': Namespace.xenbase,

    'AnimalQTLdb': None,
    'APHIDBASE': None,
    'ApiDB_CryptoDB': None,
    'BEEBASE': None,
    'BEETLEBASE': None,
    'BGD': None,
    'CGNC': None,
    'dictyBase': None,
    'EcoGene': None,
    'Ensembl': None,
    'GO': None,
    'HPRD': None,
    'HPRDmbl': None,
    'IMGT/GENE-DB': None,
    'InterPro': None,
    'MaizeGDB': None,
    'MIM': None,
    'MIMC': None,
    'miRBase': None,
    'NASONIABASE': None,
    'Pathema': None,
    'PBR': None,
    'PFAM': None,
    'PseudoCap': None,
    'UniProtKB/Swiss-Prot': None, # not worth mapping those five references...
    'VBRC': None,
    'VectorBase': None,
    'Vega': None,
    'Vegambl': None,
    'ZFIN': None,
}

def isGeneSymbol(sym:str) -> bool:
    """
    Return ``true`` if `sym` fits into a GeneSymbol field and has no spaces
    or is very short.
    """
    return len(sym) < 65 and (len(sym) < 17 or " " not in sym)


class Parser(AbstractLoader):
    """
    A parser for NCBI Entrez Gene gene_info records.

    Implements the `AbstractParser._parse` method.
    """

    def _setup(self, stream:io.TextIOWrapper):
        assert len(self.files) == 2, \
            'received {} files, expected 2'.format(len(self.files))
        lines = super(Parser, self)._setup(stream)
        logging.debug("file header:\n%s", stream.readline().strip())

        if not hasattr(self, '_fileno'):
            self._fileno = 0

        idx = stream.name.rfind('/') + 1

        if stream.name.startswith('gene_info', idx):
            if not hasattr(self, '_pmidMapping'):
                raise RuntimeError(
                    'gene_info must be after gene2pubmed file')
            logging.debug("parsed PubMed mappings for %d genes",
                          len(self._pmidMapping))
            self._parse = self._parseMain
            self._generefs = set()
            self._fileno += 1
        elif stream.name.startswith('gene2pubmed', idx):
            if self._fileno != 0:
                raise RuntimeError('gene2pubmed file not parsed first')
            self._pmidMapping = defaultdict(set)
            self._parse = self._parsePubMed
            self._fileno += 1
        else:
            raise RuntimeError('unknown Entrez file "{}"'.format(stream.name))

        return lines + 1

    def _parsePubMed(self, line:str):
        logging.debug('reading %s', line)
        _, gi, pmid = line.split('\t')
        self._pmidMapping[gi].add(int(pmid))
        logging.debug('size=%d',len(self._pmidMapping))
        return 0

    def _parseMain(self, line:str):
        # remove the backslash junk in the Entrez data file
        idx = line.find('\\')

        while idx != -1:
            if len(line) > idx + 1 and line[idx + 1].isalnum():
                line = '{}/{}'.format(line[:idx], line[idx + 1:])
            else:
                line = '{}{}'.format(line[:idx], line[idx + 1:])

            idx = line.find('\\', idx)

        items = [i.strip() for i in line.split('\t')]

        # ignore the undocumented "NEWENTRY" junk in the file
        if items[2] == 'NEWENTRY':
            return 0

        cleanChromosome = items[6].find('|')
        # drop (too long!) chr. strings with multiple chromosomes listed 
        if cleanChromosome != -1:
            items[6] = items[6][0:cleanChromosome]

        for idx in range(len(items)):
            if items[idx] == '-': items[idx] = ""

        # remove any junk names from the official names/symbols
        for idx in [2, 8, 10, 11]:
            if items[idx] and items[idx].lower() in JUNK_NAMES:
                logging.debug(
                    'removing %s "%s" from %s:%s',
                    COLNAME[idx], items[idx], Namespace.entrez, items[1]
                )
                items[idx] = ""

        row = Line._make(items)
        # example of a bad symbol: gi:835054 (but accepted)
        assert not row.symbol or len(row.symbol) < 65, \
            '{}:{} has an illegal symbol="{}"'.format(
                Namespace.entrez, row.id, row.symbol
            )
        db_key = DBRef(Namespace.entrez, row.id)
        record = GeneRecord(row.species_id,
                            symbol=row.symbol,
                            name=row.name,
                            chromosome=row.chromosome,
                            location=row.map_location)
        record.addDBRef(db_key)

        # separate existing DB links and new DB references
        if row.dbxrefs:
            for xref in row.dbxrefs.split('|'):
                db, acc = xref.split(':')

                try:
                    if TRANSLATE[db]:
                        db_ref = DBRef(TRANSLATE[db], acc)

                        if db_ref not in self._generefs:
                            record.addDBRef(db_ref)
                            self._generefs.add(db_ref)
                except KeyError:
                    logging.warn('unknown dbXref to "%s"', db)

        # parsed symbol strings
        if row.nomenclature_symbol:
            record.addSymbol(row.nomenclature_symbol)

        if row.locus_tag:
            record.addSymbol(row.locus_tag)

        if row.synonyms:
            # clean up the synonym mess, moving names to where they
            # belong, e.g., gi:814702 cites "cleavage and polyadenylation
            # specificity factor 73 kDa subunit-II" as a gene symbol
            for sym in row.synonyms.split('|'):
                sym = sym.strip()

                if sym.lower() not in JUNK_NAMES:
                    if isGeneSymbol(sym):
                        record.addSymbol(sym)
                    else:
                        record.addName(sym)

        # parsed name strings
        if row.nomenclature_name:
            record.addName(row.nomenclature_name)

        if row.other_designations:
            # as with synonyms, at least skip the most frequent junk
            for name in row.other_designations.split('|'):
                name = name.strip()

                if name.lower() not in JUNK_NAMES:
                    if isGeneSymbol(name):
                        record.addSymbol(name)
                    else:
                        record.addName(name)

        # parsed keyword strings
        if row.type_of_gene and row.type_of_gene not in ('other', 'unknown'):
            record.addKeyword(row.type_of_gene)

        # add the PubMed links parsed earlier (if any):
        if db_key.accession in self._pmidMapping:
            record.pmids = self._pmidMapping[db_key.accession]

        self._loadRecord(db_key, record)
        return 1


class SpeedLoader(Parser):
    """
    Overrides the database loading methods to directly dump all data "as is".
    """

    def setDSN(self, dsn:str):
        """
        Set the DSN string for connecting psycopg2 to a Postgres DB.

        :param dsn: the DSN string
        """
        self._dsn = dsn

    def _initBuffers(self):
        self._genes = io.StringIO()
        self._gene_refs = io.StringIO()
        self._gene_strings = io.StringIO()
        self._gene2pmids = io.StringIO()
        #self._mappings = io.StringIO()

    def _setup(self, stream:io.TextIOWrapper) -> int:
        lines = super(SpeedLoader, self)._setup(stream)
        self._gene_id = self.session.execute(Sequence('genes_id_seq'))
        self._db_key2pid_map = dict()
        self._initBuffers()
        self._connect()
        #self._loadExistingLinks()
        return lines

    def _connect(self):
        import psycopg2

        self._conn = psycopg2.connect(self._dsn)

    def _loadExistingLinks(self):
        cursor = self._conn.cursor('links')
        cursor.execute("SELECT namespace, accession, id FROM protein_refs;")

        for ns, acc, pid in cursor:
            self._db_key2pid_map[DBRef(ns, acc)].add(pid)

        cursor.close()

    def _flush(self):
        cur = self._conn.cursor()
        stream = lambda buffer: io.StringIO(buffer.getvalue())

        try:
            cur.copy_from(stream(self._genes), 'genes')
            cur.copy_from(stream(self._gene_refs), 'gene_refs')
            cur.copy_from(stream(self._gene_strings), 'gene_strings')
            cur.copy_from(stream(self._gene2pmids), 'gene2pubmed')
            #cur.copy_from(stream(self._mappings), 'genes2proteins')
            cur.execute("ALTER SEQUENCE genes_id_seq RESTART WITH %s",
                        (self._gene_id,))
        finally:
            cur.close()

        self._initBuffers()

    def _cleanup(self, stream:io.TextIOWrapper) -> int:
        super(SpeedLoader, self)._cleanup(stream)
        self._flush()
        self._conn.commit()
        self._conn.close()
        return 0 # no new records

    def _loadRecord(self, db_key:DBRef, record:GeneRecord):
        """
        Overrides the `AbstractLoader._loadRecord` method.

        :param db_key: the "primary" `DBRef` for this record.
        :param record: the `GeneRecord` to load
        """
        assert not record.mappings, "speedloader does not handle mappings"
        gid = str(self._gene_id)

        self._genes.write('{}\t{}\t{}\t{}\n'.format(
            gid, str(record.species_id),
            '\\N' if record.chromosome is None else record.chromosome,
            '\\N' if record.location is None else record.location
        ))

        self._gene_refs.write('{}\t{}\t{}\t{}\t{}\n'.format(
            db_key.namespace, db_key.accession,
            '\\N' if record.symbol is None else record.symbol,
            '\\N' if record.name is None else record.name, gid
        ))

        for ns, acc in record.refs:
            if ns != db_key.namespace or acc != db_key.accession:
                self._gene_refs.write(
                    '{}\t{}\t\\N\t\\N\t{}\n'.format(ns, acc, gid)
                )

        for cat, values in record.strings.items():
            for val in values:
                self._gene_strings.write(
                    '{}\t{}\t{}\n'.format(gid, cat, val)
                )

        for pmid in record.pmids:
            self._gene2pmids.write('{}\t{}\n'.format(pmid, gid))

        self._gene_id += 1
