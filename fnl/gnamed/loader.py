"""
.. py:module:: libfnl.gnamed.loader
   :synopsis: Classes for loading gene/protein name records into a DB.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging

from collections import defaultdict, namedtuple
from libfnl.gnamed.constants import GENE_SPACES, PROTEIN_SPACES, SPECIES_SPACES, \
    Namespace
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import and_
from sys import getdefaultencoding

from libfnl.gnamed.orm import \
    Gene, Protein, GeneRef, ProteinRef, GeneString, ProteinString, mapping, Gene2PubMed, Protein2PubMed
from libfnl.gnamed.parsers import AbstractParser

DBRef = namedtuple('DBRef', ['namespace', 'accession'])


class DuplicateEntityError(RuntimeError):
    pass


class AbstractRecord:
    """
    The abstract representation of a gene/protein name record to store.

    This representation is used by the Parsers' loadRecord methods to add any
    relevant, novel data to the DB.
    """

    def __init__(self, species_id:int, symbol:str=None, name:str=None):
        """
        Initialize a new record with the species ID, the official symbol and
        name of that gene/protein as found in the originating DB.

        Add additional `symbols` and `names` as strings after initialization
        to these corresponding sets.

        The set of `links` is a collection of (namespace, accession)
        tuples. Add `links` to other records in other namespaces after
        initialization using the `Record.addLink` method.

        Note that, while proteins have lengths and masses and genes have
        locations and chromosomes, this data is handled directly in the parsers
        and is not added to the `Record` instances.
        """
        self.species_id = int(species_id)
        self.symbol = symbol
        self.name = name
        self.strings = defaultdict(set)
        self.refs = set()
        self.mappings = set()
        self.pmids = set()

        if symbol:
            self.addSymbol(symbol)

        if name:
            self.addName(name)

    def __repr__(self):
        return '<Record species:{} {} "{}">'.format(
            self.species_id, self.symbol, self.name
        )

    #noinspection PyUnusedLocal
    def addDBRef(self, db_ref:DBRef):
        raise NotImplementedError('abstract')

    def addKeyword(self, keyword:str):
        self.strings['keyword'].add(keyword)

    def addName(self, name:str):
        self.strings['name'].add(name)

    def addSymbol(self, symbol:str):
        self.strings['symbol'].add(symbol)

    def addString(self, cat:str, value:str):
        self.strings[cat].add(value)

    def addPubMedId(self, pmid:int):
        self.pmids.add(pmid)

    def _sameSpecies(self, db_ref:DBRef) -> bool:
        ns_species = SPECIES_SPACES[db_ref.namespace]

        if self.species_id not in ns_species:
            msg = '{}:{} (species:{}) should not map to entities of species:{}'
            logging.warn(msg.format(
                db_ref.namespace, db_ref.accession,
                ','.join(str(s) for s in ns_species), self.species_id
            ))
            return False
        else:
            return True

    def _checkSpecies(self, db_ref:DBRef):
        if self.species_id not in SPECIES_SPACES[db_ref.namespace]:
            refs = ', '.join('{}:{}'.format(*key) for key in self.refs)
            logging.debug('cross-species mapping for %s:%s to [%s] species:%s',
                          db_ref.namespace, db_ref.accession, refs,
                          self.species_id)


class GeneRecord(AbstractRecord):
    def __init__(self, species_id:int, symbol:str=None, name:str=None,
                 chromosome:str=None, location:str=None):
        super(GeneRecord, self).__init__(species_id, symbol=symbol, name=name)
        self.chromosome = chromosome
        self.location = location

    def addDBRef(self, db_ref:DBRef):
        if db_ref.namespace in GENE_SPACES:
            if db_ref.namespace == Namespace.entrez or \
                    self._sameSpecies(db_ref):
                self.refs.add(db_ref)
        else:
            if db_ref.namespace != Namespace.uniprot:
                self._checkSpecies(db_ref)

            self.mappings.add(db_ref)


class ProteinRecord(AbstractRecord):
    def __init__(self, species_id:int, symbol:str=None, name:str=None,
                 length:int=None, mass:int=None):
        super(ProteinRecord, self).__init__(species_id,
                                            symbol=symbol, name=name)
        self.length = length
        self.mass = mass

    def addDBRef(self, db_ref:DBRef):
        if db_ref.namespace in PROTEIN_SPACES:
            if db_ref.namespace == Namespace.uniprot or \
                    self._sameSpecies(db_ref):
                self.refs.add(db_ref)
        else:
            if db_ref.namespace != Namespace.entrez:
                self._checkSpecies(db_ref)

            self.mappings.add(db_ref)


class AbstractLoader(AbstractParser):
    """
    Database loading functionality common to both gene and protein entities.
    """

    def __init__(self, *files:str, encoding:str=getdefaultencoding()):
        """
        :param files: any number of files (pathnames) to load
        :param encoding: the character encoding used by these files
        """
        super(AbstractLoader, self).__init__(*files, encoding=encoding)
        self.db_refs = {}

    def _flush(self):
        """
        Write session objects into the DB to allow the GC to free some memory.
        """
        self.session.flush()
        self.db_refs = {}

    def _loadRecord(self, db_key:DBRef, record:AbstractRecord):
        """
        Load an `AbstractRecord` into the database.

        :param db_key: the "primary" namespace, accession from the parsed
                       record
        :param record: either a `GeneRecord` or `ProteinRecord` representation
                       of the parsed data
        """
        logging.debug('loading %s', ", ".join(
            "{}:{}".format(*r) for r in record.refs
        ))

        # the entity associated to this record
        entity = None
        # this list ensures that there will be only one entity
        entities = list()
        # set of ns, acc keys that have not yet been loaded
        missing_db_keys = set(
            ns_acc for ns_acc in record.refs if ns_acc not in self.db_refs
        )
        # set of ns, acc keys that have been loaded already
        existing_db_keys = record.refs.difference(missing_db_keys)
        # update DB references
        update_entity = list()
        # `setEntityAttributeFunction`s by attribute name
        assign = {}

        def setEntityAttributeFunction(attr:str):
            return lambda entity: setattr(entity, attr, getattr(record, attr))

        for name in ['length', 'mass', 'location', 'chromosome']:
            if hasattr(record, name) and getattr(record, name):
                assign[name] = setEntityAttributeFunction(name)
            else:
                assign[name] = lambda entity: None

        def addEntity(e):
            assign['length'](e)
            assign['mass'](e)
            assign['location'](e)
            assign['chromosome'](e)
            entities.append(e)

        # set the object types according to the record type
        if isinstance(record, GeneRecord):
            EntityRef = GeneRef
            OtherRef = ProteinRef
            Entity = Gene
            EntityString = GeneString
            Entity2PubMed = Gene2PubMed
            entity_col = mapping.c.gene_id
            other_col = mapping.c.protein_id
            entity_name = 'gene'
            other_name = 'protein'
        else:
            EntityRef = ProteinRef
            OtherRef = GeneRef
            Entity = Protein
            EntityString = ProteinString
            Entity2PubMed = Protein2PubMed
            entity_col = mapping.c.protein_id
            other_col = mapping.c.gene_id
            entity_name = 'protein'
            other_name = 'gene'

        if missing_db_keys:
            # split the keys into two lists of namespaces and accessions
            ns_list, acc_list = zip(*missing_db_keys)

            # load *everything* relevant to the record in one large query
            # SELECT * FROM <entity>_refs
            #     LEFT OUTER JOIN <entity>s USING (id)
            #     LEFT OUTER JOIN <entity>_strings USING (id)
            #     LEFT OUTER JOIN <entity>2pubmed USING (id)
            #     WHERE <entity>_refs.namespace IN (...)
            #         AND <entity>_refs.accession IN (...);
            # noinspection PyUnresolvedReferences
            for db_ref in self.session.query(EntityRef).options(
                    joinedload(getattr(EntityRef, entity_name)),
                    joinedload(entity_name + '.strings'),
                    joinedload(entity_name + '.pmids')
            ).filter(and_(EntityRef.namespace.in_(ns_list),
                          EntityRef.accession.in_(acc_list))):
                key = DBRef(db_ref.namespace, db_ref.accession)
                self.db_refs[key] = db_ref

                if key in missing_db_keys:
                    missing_db_keys.remove(key)
                    existing_db_keys.add(key)

        # get the entity for each existing EntityRef object
        for key in existing_db_keys:
            db_ref = self.db_refs[key]
            entity = getattr(db_ref, entity_name)

            if key == db_key:
                db_ref.symbol = record.symbol
                db_ref.name = record.name

            if entity:
                if entity not in entities:
                    addEntity(entity)
            else:
                update_entity.append(db_ref)

        # create the entity or ensure we have exactly one
        if not entities:
            logging.debug('creating a new %s entity for %s:%s',
                          entity_name, *db_key)
            entity = Entity(record.species_id)
            self.session.add(entity)
            addEntity(entity)
        elif len(entities) > 1:
            # raise an error when more than one entity was found
            raise DuplicateEntityError(
                "{} {}s ({}) found for {}:{} ({})".format(
                    len(entities), entity_name,
                    ", ".join(str(e.id) for e in entities), db_key.namespace,
                    db_key.accession, ', '.join(
                        '{}:{}'.format(r.namespace,
                                       r.accession) for r in record.refs
                    )
                )
            )

        # update all EntityRef objects that were not pointing to the entity
        for db_ref in update_entity:
            setattr(db_ref, entity_name, entity)

        # create all missing EntityRef objects
        for key in missing_db_keys:
            if key.namespace == db_key.namespace:
                logging.debug('creating new reference object %s:%s', *key)
            else:
                logging.info('creating new reference object %s:%s', *key)

            db_ref = EntityRef(*key)
            setattr(db_ref, entity_name, entity)
            self.session.add(db_ref)
            self.db_refs[key] = db_ref

            if key == db_key:
                db_ref.symbol = record.symbol
                db_ref.name = record.name

        # update the entity with any new strings
        known = defaultdict(set)

        for s in entity.strings:
            known[s.cat].add(s.value)

        for cat in record.strings:
            for value in record.strings[cat].difference(known[cat]):
                logging.debug('adding %s="%s" to %s', cat, value, entity)
                obj = EntityString(entity.id, cat, value)
                entity.strings.append(obj)
                self.session.add(obj)

        # update the PubMed references (entity2pubmed)
        known = set()

        for p in entity.pmids:
            known.add(p.pmid)

        for pmid in record.pmids.difference(known):
            logging.debug('adding PMID:%s to %s', pmid, entity)
            obj = Entity2PubMed(entity.id, pmid)
            entity.pmids.append(obj)
            self.session.add(obj)

        # update the entity mappings (genes2proteins)
        if record.mappings:
            known = {}
            ns_list, acc_list = zip(*record.mappings)

            # SELECT * FROM <other>_refs
            #     LEFT OUTER JOIN genes2proteins
            #         ON <other>_refs.id = genes2proteins.<this>_id
            #     WHERE <other>_refs.namespace IN (...)
            #         AND <other>_refs.accession IN (...);
            # noinspection PyUnresolvedReferences
            for ref, this_id in self.session.query(OtherRef,
                                                   entity_col).outerjoin(
                    mapping, OtherRef.id == other_col).filter(
                    and_(OtherRef.namespace.in_(ns_list),
                         OtherRef.accession.in_(acc_list))):
                if DBRef(ref.namespace, ref.accession) in record.mappings:
                    if ref.id not in known:
                        known[ref.id] = {this_id, }
                    else:
                        known[ref.id].add(this_id)

            for other_id, this_ids in known.items():
                if entity.id not in this_ids:
                    if entity.id is None:
                        self.session.flush()
                        assert entity.id is not None

                    logging.debug('adding mapping {}:{}->{}:{}'.format(
                        entity_name, entity.id, other_name, other_id
                    ))
                    self.session.execute(mapping.insert().values(**{
                        '{}_id'.format(entity_name): entity.id,
                        '{}_id'.format(other_name): other_id
                    }))

