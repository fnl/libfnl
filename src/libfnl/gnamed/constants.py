"""
.. py:module:: libfnl.gnamed.constants
   :synopsis: All settings used by gnamed in one place.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

REPOSITORIES = {
    'taxa': {
        'url': 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/',
        'resources': [('taxdump.tar.gz', 'taxdump.tar.gz', None)],
        'description': "NCBI Taxonomy database dump (nodes.dmp, names.dmp)",
        },
    'entrez': {
        'url': 'ftp://ftp.ncbi.nih.gov/gene/DATA/',
        'resources': [
            ('gene_info.gz', 'gene_info.gz', None),
            ('gene2pubmed.gz', 'gene2pubmed.gz', None),
        ],
        'description': "NCBI Entrez Gene gene2pubmed and gene_info file",
        },
    'uniprot': {
        'url': 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/'
        ,
        'resources': [
            ('uniprot_sprot.dat.gz', 'uniprot_sprot.dat.gz', None),
            ('uniprot_trembl.dat.gz', 'uniprot_trembl.dat.gz', None)
        ],
        'description': "UniProtKB TrEMBL/Swiss-Prot text files",
        },
    'hgnc': {
        # see http://www.genenames.org/cgi-bin/hgnc_downloads.cgi for more info
        'url': 'http://www.genenames.org/cgi-bin/hgnc_downloads.cgi?',
        'resources': [(
            'title=HGNC%20output%20data&col=gd_hgnc_id&col=gd_app_sym&col=gd_app_name&col=gd_prev_sym&col=gd_prev_name&col=gd_aliases&col=gd_name_aliases&col=gd_pub_chrom_map&col=gd_pubmed_ids&col=gd_gene_fam_name&col=gd_gene_fam_pagename&col=gd_pub_eg_id&col=gd_pub_ensembl_id&col=gd_mgd_id&col=md_prot_id&col=md_rgd_id&status=Approved&status_opt=2&where=&order_by=&format=text&limit=&submit=submit&.cgifields=&.cgifields=status&.cgifields=chr&.cgifields=hgnc_dbtag'
            , 'hgnc.csv', 'ISO-8859-1')],
        'description': "Human Genome Nomenclature Consortium (genenames.org)",
        },
    'rgd': {
        'url': 'ftp://rgd.mcw.edu/pub/data_release/',
        'resources': [
            ('GENES_RAT.txt', 'GENES_RAT.txt', 'UTF-8'),
        ],
        'description': "Rat Genome Database rat GENE text file",
    },
    'mgi': {
        'url': 'ftp://ftp.informatics.jax.org/pub/reports/',
        'resources': [
            ('MRK_List1.rpt', 'MRK_List1.rpt', 'UTF-8'),
            ('MRK_SwissProt_TrEMBL.rpt', 'MRK_SwissProt_TrEMBL.rpt', 'UTF-8'),
            ('MGI_EntrezGene.rpt', 'MGI_EntrezGene.rpt', 'UTF-8'),
        ],
        'description': 'Mouse Geneome Database text files',
    },
    'tair': {
        'url': 'ftp://ftp.arabidopsis.org/home/tair/Genes/',
        'resources': [
            ('Locus_Primary_Gene_Symbol_20130117.txt', 'gene_names.txt', 'UTF-8'),
            ('gene_aliases.20120207.txt', 'gene_aliases.txt', 'UTF-8'),
            ('TAIR10_genome_release/TAIR10_NCBI_mapping_files/TAIR10_NCBI_GENEID_mapping', 'entrez2tair.txt', 'UTF-8'),
        ],
        'description': 'The A. thaliana database gene name and alias files',
    },
    'sgd': {
        'url': 'http://yeastmine.yeastgenome.org/yeastmine/service/query/results?',
        'resources': [
            # SGDID, Qualifier(Verified, Uncharacterized, Dubious, NULL), Std Name(Symbol OR NULL - use Systematic Name then), Name OR NULL, Systematic Name(Location, 2nd char = chromosome), Length OR NULL, Protein Name OR NULL, Alias(incl. Std Name and Systematic Name)
            ('query=%3Cquery+name%3D%22%22+model%3D%22genomic%22+view%3D%22Gene.primaryIdentifier+Gene.qualifier+Gene.symbol+Gene.name+Gene.secondaryIdentifier+Gene.length+Gene.proteins.symbol+Gene.synonyms.value%22+sortOrder%3D%22Gene.primaryIdentifier+asc%22%3E%3Cjoin+path%3D%22Gene.proteins%22+style%3D%22OUTER%22%2F%3E%3Cconstraint+path%3D%22Gene.status%22+op%3D%22%3D%22+value%3D%22Active%22%2F%3E%3C%2Fquery%3E&format=tab', 'names.tsv', 'US-ASCII'),
        ],
        'description': 'Yeast Genome Database gene (and protein) names',
    },
    'flybase': {
        'url': 'ftp://ftp.flybase.net/releases/current/precomputed_files/',
        'resources': [
            ('synonyms/fb_synonym_fb_2013_03.tsv.gz', 'fb_synonym.tsv.gz', None),
            ('genes/fbgn_NAseq_Uniprot_fb_2013_03.tsv.gz', 'fbgn_NAseq_Uniprot.tsv.gz', None),

        ],
        'description': 'FlyBase D. melanogaster gene names and alias files',
    }
}

class Namespace:
    # general DBs
    entrez = 'gi'
    uniprot = 'uni'
    # organism-specific DBs
    hgnc = 'hgnc' # human
    mgd = 'mgi' # mouse
    rgd = 'rgd' # rat
    flybase = 'fly' # (fruit) fly
    sgd = 'sgd' # bakers yeast (S. cerevisiae)
    pombase = 'pb' # fission yeast (S. pombe)
    tair = 'tair' # (thale) cress (A. thaliana)
    ecocyc = 'eco' # E. coli
    wormbase = 'wb' # nematode (C. elegans)
    xenbase = 'xb' # african and western frog (X. laevis and X. tropicalis)


NAMESPACES = frozenset({
    Namespace.entrez,
    Namespace.uniprot,
    Namespace.hgnc,
    Namespace.mgd,
    Namespace.rgd,
    Namespace.flybase,
    Namespace.sgd,
    Namespace.pombase,
    Namespace.tair,
    Namespace.ecocyc,
    Namespace.wormbase,
    Namespace.xenbase,
    })


GENE_SPACES = frozenset({
    Namespace.entrez,
    Namespace.hgnc,
    Namespace.mgd,
    Namespace.rgd,
    Namespace.flybase,
    Namespace.sgd,
    Namespace.pombase,
    Namespace.tair,
    Namespace.ecocyc,
    Namespace.wormbase,
    Namespace.xenbase,
    })

PROTEIN_SPACES = frozenset({
    Namespace.uniprot,
    })


class Species:
    human = 9606 # H. sapiens
    mouse = 10090 # M. musculus
    rat = 10116 # R. norvegus
    fly = 7227 # D. melanogaster
    budding_yeast = 4932 # S. cerevisiae
    fission_yeast = 4896 # S. pombe
    cress = 3702 # A. thaliana
    e_coli = 562 # E. coli
    nematode = 6239 # C. elegans
    african_frog = 8355 # X. laevis
    western_frog = 8364 # X. tropicalis
    unidentified = 32644 # unknown/unclassified species


SPECIES = frozenset({
    Species.human,
    Species.mouse,
    Species.rat,
    Species.fly,
    # various Drosophila species in FlyBase:
    46245, 7217, 7220, 7222, 7230, 7234, 7238, 7240, 7244, 7245, 7260,
    Species.budding_yeast ,
    # additional yeast strains in SGD:
    559292,
    Species.fission_yeast,
    Species.cress,
    Species.e_coli,
    # e. coli strain in EcoCyc
    511145,
    Species.nematode,
    # various nematode species in WormBase:
    6238, 31234, 135651, 860376, 54126, 6289, 6305, 6306, 6279,
    Species.african_frog,
    Species.western_frog,
    })

SPECIES_SPACES = {
    Namespace.hgnc: frozenset({Species.human}),
    Namespace.mgd: frozenset({Species.mouse}),
    Namespace.rgd: frozenset({Species.human, Species.rat}),
    Namespace.flybase: frozenset({Species.fly, 46245, 7217, 7220, 7222, 7230,
                                  7234, 7238, 7240, 7244, 7245, 7260}),
    Namespace.sgd: frozenset({Species.budding_yeast, 559292}),
    Namespace.pombase: frozenset({Species.fission_yeast}),
    Namespace.tair: frozenset({Species.cress}),
    Namespace.ecocyc: frozenset({Species.e_coli, 511145}),
    Namespace.wormbase: frozenset({Species.nematode, 6238, 31234, 135651,
                                   860376, 54126, 6289, 6305, 6306, 6279}),
    Namespace.xenbase: frozenset({Species.western_frog, Species.african_frog}),
    }
