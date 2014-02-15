"""
.. py:module:: libfnl.gnamed.orm
   :synopsis: The gnamed DB schema and ORM classes.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import sqlalchemy

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import engine
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.schema import Column, ForeignKey, Sequence, Table
from sqlalchemy.types import BigInteger, Integer, String, Text

_Base = declarative_base()
_db = None
_session = lambda *args, **kwds: None

def InitDb(*args, **kwds):
    """
    Create a new DBAPI connection pool.

    The most common and only really required argument is the connection URL.

    see `sqlalchemy.engine.create_engine<http://docs.sqlalchemy.org/en/rel_0_7/core/engines.html#sqlalchemy.create_engine>`_
    """
    global _db
    global _session
    _db = engine.create_engine(*args, **kwds)
    _Base.metadata.create_all(_db)
    _session = sessionmaker(bind=_db)
    return None

def Session(*args, **kwds) -> sqlalchemy.orm.session.Session:
    """
    Start a new DB session.

    see `sqlalchemy.orm.session.Session<http://docs.sqlalchemy.org/en/rel_0_7/orm/session.html#sqlalchemy.orm.session>`_.Session
    """
    return _session(*args, **kwds)

class Species(_Base):

    __tablename__ = 'species'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey(
        'species.id', onupdate='CASCADE', ondelete='CASCADE'
    ))
    rank = Column(String(32), nullable=False)
    unique_name = Column(Text, nullable=False)
    genbank_name = Column(Text)

    genes = relationship('Gene', cascade='all', backref='species')
    proteins = relationship('Protein', cascade='all', backref='species')
    names = relationship('SpeciesName', cascade='all', backref='species')
    children = relationship('Species', cascade='all',
                            backref=backref('parent', remote_side=[id]))

    def __init__(self, id:int, parent_id:int, rank:str):
        self.id = id
        self.parent_id = parent_id
        self.rank = rank

    def __repr__(self) -> str:
        return '<Species:{}>'.format(self.id)

    def __str__(self) -> str:
        return self.unique_name

class SpeciesName(_Base):

    __tablename__ = 'species_names'

    id = Column(Integer, ForeignKey(
        'species.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True)
    cat = Column(String(32), primary_key=True)
    name = Column(Text, primary_key=True)

    def __init__(self, id:int, cat:str, name:str):
        self.id = id
        self.cat = cat
        self.name = name

    def __repr__(self):
        return '<SpeciesName:{}:{} "{}">'.format(self.id, self.cat,
                                                 self.name)

    def __str__(self):
        return self.name

mapping = Table(
    'genes2proteins', _Base.metadata,
    Column('gene_id', BigInteger, ForeignKey(
        'genes.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True),
    Column('protein_id', BigInteger, ForeignKey(
        'proteins.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True),
)


class Gene(_Base):

    __tablename__ = 'genes'

    id = Column(BigInteger, Sequence('genes_id_seq', optional=True),
                primary_key=True)
    species_id = Column(Integer, ForeignKey(
        'species.id', onupdate='CASCADE', ondelete='CASCADE'
    ), nullable=False)
    chromosome = Column(String(32))
    location = Column(String(64))

    strings = relationship('GeneString', cascade='all', backref='gene')
    refs = relationship('GeneRef', cascade='all', backref='gene')
    pmids = relationship('Gene2PubMed', cascade='all', backref='gene')
    proteins = relationship('Protein', secondary=mapping, backref='genes')

    def __init__(self, species_id:int, chromosome:str=None, location:str=None):
        self.species_id = species_id
        self.chromosome = chromosome
        self.location = location

    def __repr__(self) -> str:
        return "<Gene {} ({})>".format(self.id, self.species_id)

    def __str__(self) -> str:
        return "gene:{}".format(self.id)

class Protein(_Base):

    __tablename__ = 'proteins'

    id = Column(BigInteger, Sequence('proteins_id_seq', optional=True),
                primary_key=True)
    species_id = Column(Integer, ForeignKey(
        'species.id', onupdate='CASCADE', ondelete='CASCADE'
    ), nullable=False)
    length = Column(Integer)
    mass = Column(Integer)

    strings = relationship('ProteinString', cascade='all', backref='protein')
    refs = relationship('ProteinRef', cascade='all', backref='protein')
    pmids = relationship('Protein2PubMed', cascade='all', backref='protein')
    # genes = relationship('Gene', secondary=mapping, backref='proteins')

    def __init__(self, species_id:int, mass:int=None, length:int=None):
        self.species_id = species_id
        self.mass = mass
        self.length = length

    def __repr__(self) -> str:
        return "<Protein {} ({})>".format(self.id, self.species)

    def __str__(self) -> str:
        return "protein:{}".format(self.id)

class EntityRef:

    namespace = Column(String(8), primary_key=True)
    accession = Column(String(64), primary_key=True)
    symbol = Column(String(64))
    name = Column(Text)

    def __init__(self, namespace:str, accession:str,
                 symbol:str=None, name:str=None):
        self.namespace = namespace
        self.accession = accession
        self.symbol = symbol
        self.name = name

    def __str__(self) -> str:
        return "{}:{}".format(self.namespace, self.accession)


class GeneRef(EntityRef, _Base):

    __tablename__ = 'gene_refs'

    id = Column(BigInteger, ForeignKey(
        'genes.id', onupdate='CASCADE', ondelete='SET NULL'
    ))

    def __init__(self, namespace:str, accession:str,
                 symbol:str=None, name:str=None, id:int=None):
        super(GeneRef, self).__init__(namespace, accession,
                                      symbol=symbol, name=name)
        self.id = id

    def __repr__(self) -> str:
        return "<GeneDBRef:{}:{}>".format(self.namespace, self.accession)


class ProteinRef(EntityRef, _Base):

    __tablename__ = 'protein_refs'

    id = Column(BigInteger, ForeignKey(
        'proteins.id', onupdate='CASCADE', ondelete='SET NULL'
    ))

    def __init__(self, namespace:str, accession:str,
                 symbol:str=None, name:str=None, id:int=None):
        super(ProteinRef, self).__init__(namespace, accession,
                                         symbol=symbol, name=name)
        self.id = id

    def __repr__(self) -> str:
        return "<ProteinDBRef:{}:{}>".format(self.namespace, self.accession)


class Gene2PubMed(_Base):

    __tablename__ = 'gene2pubmed'

    id = Column(BigInteger, ForeignKey(
        'genes.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True)
    pmid = Column(Integer, primary_key=True)

    def __init__(self, id:int, pmid:int):
        self.id = id
        self.pmid = pmid

    def __str__(self) -> str:
        return "gene:{}->PMID:{}".format(self.id, self.pmid)

    def __repr__(self) -> str:
        return "<Gene2PubMed:{}:{}>".format(self.id, self.pmid)


class Protein2PubMed(_Base):

    __tablename__ = 'protein2pubmed'

    id = Column(BigInteger, ForeignKey(
        'proteins.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True)
    pmid = Column(Integer, primary_key=True)

    def __init__(self, id:int, pmid:int):
        self.id = id
        self.pmid = pmid

    def __str__(self) -> str:
        return "protein:{}->PMID:{}".format(self.id, self.pmid)

    def __repr__(self) -> str:
        return "<Protein2PubMed:{}:{}>".format(self.id, self.pmid)


class GeneString(_Base):

    __tablename__ = 'gene_strings'

    id = Column(BigInteger, ForeignKey(
        'genes.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True)
    cat = Column(String(32), primary_key=True)
    value = Column(Text, primary_key=True)

    def __init__(self, id:int, cat:str, value:str):
        self.id = id
        self.cat = cat
        self.value = value

    def __repr__(self) -> str:
        return '<GeneString:{}:{} "{}">'.format(
            self.id, self.cat, self.value
        )

    def __str__(self) -> str:
        return self.value


class ProteinString(_Base):

    __tablename__ = 'protein_strings'

    id = Column(BigInteger, ForeignKey(
        'proteins.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True)
    cat = Column(String(32), primary_key=True)
    value = Column(Text, primary_key=True)

    def __init__(self, id:int, cat:str, value:str):
        self.id = id
        self.cat = cat
        self.value = value

    def __repr__(self) -> str:
        return '<ProteinString:{}:{} "{}">'.format(
            self.id, self.cat, self.value
        )

    def __str__(self) -> str:
        return self.value

