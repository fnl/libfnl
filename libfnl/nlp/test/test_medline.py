from datetime import date
from io import StringIO
import os
import unittest

from libfnl.nlp.medline import Fetch, Parse, MakeDocuments, TextFromAbstract

PARSED_SAMPLE = [
{
    'Article': {
        'Abstract': {
            'AbstractText': 'This study subdivides the cryopreservation procedure for Diplodus puntazzo spermatozoa into three key phases, fresh, prefreezing (samples equilibrated in cryosolutions), and postthawed stages, and examines the ultrastructural anomalies and motility profiles of spermatozoa in each stage, with different cryodiluents. Two simple cryosolutions were evaluated: 0.17 M sodium chloride containing a final concentration of 15% dimethyl sulfoxide (Me(2)SO) (cryosolution A) and 0.1 M sodium citrate containing a final concentration of 10% Me(2)SO (cryosolution B). Ultrastructural anomalies of the plasmatic and nuclear membranes of the sperm head were common and the severity of the cryoinjury differed significantly between the pre- and the postfreezing phases and between the two cryosolutions. In spermatozoa diluted with cryosolution A, during the prefreezing phase, the plasmalemma of 61% of the cells was absent or damaged compared with 24% in the fresh sample (P < 0.001). In spermatozoa diluted with cryosolution B, there was a pronounced increase in the number of cells lacking the head plasmatic membrane from the prefreezing to the postthawed stages (from 32 to 52%, P < 0.01). In both cryosolutions, damages to nuclear membrane were significantly higher after freezing (cryosolution A: 8 to 23%, P < 0.01; cryosolution B: 5 to 38%, P < 0.001). With cryosolution A, the after-activation motility profile confirmed a consistent drop from fresh at the prefreezing stage, whereas freezing and thawing did not affect the motility much further and 50% of the cells were immotile by 60-90 s after activation. With cryosolution B, only the postthawing stage showed a sharp drop of motility profile. This study suggests that the different phases of the cryoprocess should be investigated to better understand the process of sperm damage.',
            'CopyrightInformation': 'Copyright 2001 Elsevier Science.'
        },
        'Affiliation': 'Dipartimento di Scienze Ambientali, Università degli Studi della Tuscia, 01100 Viterbo, Italy.',
        'ArticleTitle': 'Is cryopreservation a homogeneous process? Ultrastructure and motility of untreated, prefreezing, and postthawed spermatozoa of Diplodus puntazzo (Cetti).',
        'AuthorList': [
            'A. R. Taddei',
            'F. Barbato',
            'L. Abelli',
            'S. Canese',
            'F. Moretti',
            'K. J. Rana',
            'A. M. Fausto',
            'M. Mazzini'
        ],
        'Journal': {
            'ISOAbbreviation': 'Cryobiology',
            'ISSN': ('Print', '0011-2240'),
            'JournalIssue': {
                'CitedMedium': 'Print',
                'Issue': '4',
                'PubDate': date(2001, 6, 1),
                'Volume': '42'
            },
            'Title': 'Cryobiology'
        },
        'Language': 'eng',
        'Pagination': {'MedlinePgn': '244-55'},
        'PubModel': 'Print',
        'PublicationTypeList': [
            'Journal Article',
            "Research Support, Non-U.S. Gov't"
        ]
    },
    'ArticleIds': {
        'doi': '10.1006/cryo.2001.2328',
        'pii': 'S0011-2240(01)92328-4',
        'pubmed': '11748933'
    },
    'CitationSubset': 'IM',
    'DateCompleted': date(2002, 3, 4),
    'DateCreated': date(2001, 12, 25),
    'DateRevised': date(2006, 11, 15),
    'MedlineJournalInfo': {
        'Country': 'United States',
        'ISSNLinking': '0011-2240',
        'MedlineTA': 'Cryobiology',
        'NlmUniqueID': '0006252'
    },
    'MeshHeadingList': [
            (False, 'Animals', {}),
            (False, 'Cell Membrane', {'ultrastructure': False}),
            (False, 'Cryopreservation', {'methods': True}),
            (False, 'Male', {}),
            (False, 'Microscopy, Electron', {}),
            (False, 'Microscopy, Electron, Scanning', {}),
            (False, 'Nuclear Envelope', {'ultrastructure': False}),
            (False, 'Sea Bream', {'anatomy & histology': True,
                                  'physiology': False}),
            (False, 'Semen Preservation', {'methods': True,
                                           'adverse effects': False}),
            (True, 'Sperm Motility', {}),
            (False, 'Spermatozoa', {'physiology': False,
                                    'ultrastructure': True})
    ],
    'Owner': 'NLM',
    'PMID': ('11748933', 1),
    'Status': 'MEDLINE'
},
{
    'Article': {
        'Abstract': {
            'AbstractText': 'The sensitivity of (13)C NMR imaging can be considerably favored by detecting the (1)H nuclei bound to (13)C nuclei via scalar J-interaction (X-filter). However, the J-editing approaches have difficulty in discriminating between compounds with similar J-constant as, for example, different glucose metabolites. In such cases, it is almost impossible to get J-edited images of a single-compound distribution, since the various molecules are distinguishable only via their chemical shift. In a recent application of J-editing to high-resolution spectroscopy, it has been shown that a more efficient chemical selectivity could be obtained by utilizing the larger chemical shift range of (13)C. This has been made by introducing frequency-selective (13)C pulses that allow a great capability of indirect chemical separation. Here a double-resonance imaging approach is proposed, based on both J-editing and (13)C chemical shift editing, which achieves a powerful chemical selectivity and is able to produce full maps of specific chemical compounds. Results are presented on a multicompartments sample containing solutions of glucose and lactic and glutamic acid in water.',
            'CopyrightInformation': 'Copyright 2001 Academic Press.'
        },
        'Affiliation': "INFM and Department of Physics, University of L'Aquila, I-67100 L'Aquila, Italy.",
        'ArticleTitle': 'Proton MRI of (13)C distribution by J and chemical shift editing.' ,
        'AuthorList': [
            'C. Casieri',
            'C. Testa',
            'G. Carpinelli',
            'R. Canese',
            'F. Podo',
            'F. De Luca'
        ],
        'Journal': {
            'ISOAbbreviation': 'J. Magn. Reson.',
            'ISSN': ('Print', '1090-7807'),
            'JournalIssue': {
                'CitedMedium': 'Print',
                'Issue': '1',
                'PubDate': date(2001, 11, 1),
                'Volume': '153'
            },
            'Title': 'Journal of magnetic resonance (San Diego, Calif. : 1997)'
        },
        'Language': 'eng',
        'Pagination': {'MedlinePgn': '117-23'},
        'PubModel': 'Print',
        'PublicationTypeList': ['Journal Article']
    },
    'ArticleIds': {
        'doi': '10.1006/jmre.2001.2429',
        'pii': 'S1090-7807(01)92429-2',
        'pubmed': '11700088'
    },
    'DateCompleted': date(2001, 12, 20),
    'DateCreated': date(2001, 11, 8),
    'DateRevised': date(2003, 10, 31),
    'MedlineJournalInfo': {
        'Country': 'United States',
        'ISSNLinking': '1090-7807',
        'MedlineTA': 'J Magn Reson',
        'NlmUniqueID': '9707935'
    },
    'Owner': 'NLM',
    'PMID': ('11700088', 1),
    'Status': 'PubMed-not-MEDLINE'
}]

class TestMedline(unittest.TestCase):
    def setUp(self):
        this_dir = os.path.dirname(__file__)
        self.xml_stream = open(os.path.join(this_dir, "medline_sample.xml"),
                               encoding="utf-8")
        self.count = 0

    def tearDown(self):
        self.xml_stream.close()

    def testDownloader(self):
        pmids = (11700088, 11748933)
        stream = Fetch(pmids)

        for record in Parse(stream):
            self.assertEqual(pmids[self.count], int(record['PMID'][0]))
            self.count += 1

        self.assertEqual(self.count, len(pmids))

    def testParser(self):
        for record in Parse(self.xml_stream):
            self.assertDictEqual(PARSED_SAMPLE[self.count], record)
            self.count += 1

        self.assertEqual(len(PARSED_SAMPLE), self.count)

    def testMakeDocuments(self):
        revs = {'11700088': {
            '_rev': 'maintain', 'created': 'keep me', 'text': 'clear me',
            'tags': {'clear': {'me': [(1,2)]}}, '_id': '11700088',
            'medline': 'gone',
        }}
        docs = iter(MakeDocuments(self.xml_stream, revs))
        d = next(docs)
        self.assertTrue('medline' in d, d)
        self.assertEqual(d['medline']['PMID'][0], d['_id'])
        self.assertTrue('_rev' not in d, d)
        self.assertEqual(date.today(), d['created'])
        self.assertEqual(date.today(), d['modified'])
        d = next(docs)
        self.assertNotEqual('gone', d['medline'])
        self.assertEqual(d['medline']['PMID'][0], d['_id'])
        self.assertEqual('maintain', d['_rev'])
        self.assertEqual('keep me', d['created'])
        self.assertEqual(date.today(), d['modified'])
        self.assertNotEqual('clear me', d['text'])
        self.assertTrue('clear' not in d['tags'])
        self.assertRaises(StopIteration, next, docs)

    def testTextFromAbstract(self):
        section_tags = {"title": [(0, 10)]}
        title = "1234567890"
        abstract = {
            "AbstractText": "1234567890",
            "CopyrightNotice": "1234567890"
        }
        buffer = StringIO()
        buffer.write(title)

        result = TextFromAbstract(buffer, abstract, section_tags)
        self.assertSequenceEqual('\n\n'.join(["1234567890"] * 3), result)
        self.assertDictEqual({"title": [(0, 10)],
                              "abstract": [(12, 22)],
                              "copyright": [(24, 34)]}, section_tags)


if __name__ == '__main__':
    unittest.main()