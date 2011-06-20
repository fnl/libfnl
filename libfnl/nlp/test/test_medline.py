import datetime
from logging import basicConfig
import os
import unittest

from libfnl.nlp.medline import FetchMedlineXml, ParseMedlineXml

PARSED_SAMPLE = [
{'Article': {'Abstract': {'AbstractText': 'This study subdivides the cryopreservation procedure for Diplodus puntazzo spermatozoa into three key phases, fresh, prefreezing (samples equilibrated in cryosolutions), and postthawed stages, and examines the ultrastructural anomalies and motility profiles of spermatozoa in each stage, with different cryodiluents. Two simple cryosolutions were evaluated: 0.17 M sodium chloride containing a final concentration of 15% dimethyl sulfoxide (Me(2)SO) (cryosolution A) and 0.1 M sodium citrate containing a final concentration of 10% Me(2)SO (cryosolution B). Ultrastructural anomalies of the plasmatic and nuclear membranes of the sperm head were common and the severity of the cryoinjury differed significantly between the pre- and the postfreezing phases and between the two cryosolutions. In spermatozoa diluted with cryosolution A, during the prefreezing phase, the plasmalemma of 61% of the cells was absent or damaged compared with 24% in the fresh sample (P < 0.001). In spermatozoa diluted with cryosolution B, there was a pronounced increase in the number of cells lacking the head plasmatic membrane from the prefreezing to the postthawed stages (from 32 to 52%, P < 0.01). In both cryosolutions, damages to nuclear membrane were significantly higher after freezing (cryosolution A: 8 to 23%, P < 0.01; cryosolution B: 5 to 38%, P < 0.001). With cryosolution A, the after-activation motility profile confirmed a consistent drop from fresh at the prefreezing stage, whereas freezing and thawing did not affect the motility much further and 50% of the cells were immotile by 60-90 s after activation. With cryosolution B, only the postthawing stage showed a sharp drop of motility profile. This study suggests that the different phases of the cryoprocess should be investigated to better understand the process of sperm damage.',
                          'CopyrightInformation': 'Copyright 2001 Elsevier Science.'},
             'Affiliation': 'Dipartimento di Scienze Ambientali, Università degli Studi della Tuscia, 01100 Viterbo, Italy.',
             'ArticleTitle': 'Is cryopreservation a homogeneous process? Ultrastructure and motility of untreated, prefreezing, and postthawed spermatozoa of Diplodus puntazzo (Cetti).',
             'AuthorList': [{'ForeName': 'A R',
                             'Initials': 'AR',
                             'LastName': 'Taddei',
                             'ValidYN': 'Y'},
                            {'ForeName': 'F',
                             'Initials': 'F',
                             'LastName': 'Barbato',
                             'ValidYN': 'Y'},
                            {'ForeName': 'L',
                             'Initials': 'L',
                             'LastName': 'Abelli',
                             'ValidYN': 'Y'},
                            {'ForeName': 'S',
                             'Initials': 'S',
                             'LastName': 'Canese',
                             'ValidYN': 'Y'},
                            {'ForeName': 'F',
                             'Initials': 'F',
                             'LastName': 'Moretti',
                             'ValidYN': 'Y'},
                            {'ForeName': 'K J',
                             'Initials': 'KJ',
                             'LastName': 'Rana',
                             'ValidYN': 'Y'},
                            {'ForeName': 'A M',
                             'Initials': 'AM',
                             'LastName': 'Fausto',
                             'ValidYN': 'Y'},
                            {'ForeName': 'M',
                             'Initials': 'M',
                             'LastName': 'Mazzini',
                             'ValidYN': 'Y'}],
             'Journal': {'ISOAbbreviation': 'Cryobiology',
                         'ISSN': {'ISSN': '0011-2240', 'IssnType': 'Print'},
                         'JournalIssue': {'CitedMedium': 'Print',
                                          'Issue': '4',
                                          'PubDate': datetime.date(2001, 6, 1),
                                          'Volume': '42'},
                         'Title': 'Cryobiology'},
             'Language': 'eng',
             'Pagination': {'MedlinePgn': '244-55'},
             'PubModel': 'Print',
             'PublicationTypeList': ['Journal Article',
                                     "Research Support, Non-U.S. Gov't"]},
 'ArticleIds': {'doi': '10.1006/cryo.2001.2328',
                'pii': 'S0011-2240(01)92328-4',
                'pubmed': '11748933'},
 'CitationSubset': 'IM',
 'DateCompleted': datetime.date(2002, 3, 4),
 'DateCreated': datetime.date(2001, 12, 25),
 'DateRevised': datetime.date(2006, 11, 15),
 'MedlineJournalInfo': {'Country': 'United States',
                        'ISSNLinking': '0011-2240',
                        'MedlineTA': 'Cryobiology',
                        'NlmUniqueID': '0006252'},
 'MeshHeadingList': [{'Descriptor': {'Animals': False}},
                     {'Descriptor': {'Cell Membrane': False},
                      'Qualifiers': {'ultrastructure': False}},
                     {'Descriptor': {'Cryopreservation': False},
                      'Qualifiers': {'methods': True}},
                     {'Descriptor': {'Male': False}},
                     {'Descriptor': {'Microscopy, Electron': False}},
                     {'Descriptor': {'Microscopy, Electron, Scanning': False}},
                     {'Descriptor': {'Nuclear Envelope': False},
                      'Qualifiers': {'ultrastructure': False}},
                     {'Descriptor': {'Sea Bream': False},
                      'Qualifiers': {'anatomy & histology': True,
                                     'physiology': False}},
                     {'Descriptor': {'Semen Preservation': False},
                      'Qualifiers': {'adverse effects': False,
                                     'methods': True}},
                     {'Descriptor': {'Sperm Motility': True}},
                     {'Descriptor': {'Spermatozoa': False},
                      'Qualifiers': {'physiology': False,
                                     'ultrastructure': True}}],
 'Owner': 'NLM',
 'PMID': '11748933',
 '_id': '11748933',
 'Status': 'MEDLINE'},
{'Article': {'Abstract': {'AbstractText': 'The sensitivity of (13)C NMR imaging can be considerably favored by detecting the (1)H nuclei bound to (13)C nuclei via scalar J-interaction (X-filter). However, the J-editing approaches have difficulty in discriminating between compounds with similar J-constant as, for example, different glucose metabolites. In such cases, it is almost impossible to get J-edited images of a single-compound distribution, since the various molecules are distinguishable only via their chemical shift. In a recent application of J-editing to high-resolution spectroscopy, it has been shown that a more efficient chemical selectivity could be obtained by utilizing the larger chemical shift range of (13)C. This has been made by introducing frequency-selective (13)C pulses that allow a great capability of indirect chemical separation. Here a double-resonance imaging approach is proposed, based on both J-editing and (13)C chemical shift editing, which achieves a powerful chemical selectivity and is able to produce full maps of specific chemical compounds. Results are presented on a multicompartments sample containing solutions of glucose and lactic and glutamic acid in water.',
                          'CopyrightInformation': 'Copyright 2001 Academic Press.'},
             'Affiliation': "INFM and Department of Physics, University of L'Aquila, I-67100 L'Aquila, Italy.",
             'ArticleTitle': 'Proton MRI of (13)C distribution by J and chemical shift editing.',
             'AuthorList': [{'ForeName': 'C',
                             'Initials': 'C',
                             'LastName': 'Casieri',
                             'ValidYN': 'Y'},
                            {'ForeName': 'C',
                             'Initials': 'C',
                             'LastName': 'Testa',
                             'ValidYN': 'Y'},
                            {'ForeName': 'G',
                             'Initials': 'G',
                             'LastName': 'Carpinelli',
                             'ValidYN': 'Y'},
                            {'ForeName': 'R',
                             'Initials': 'R',
                             'LastName': 'Canese',
                             'ValidYN': 'Y'},
                            {'ForeName': 'F',
                             'Initials': 'F',
                             'LastName': 'Podo',
                             'ValidYN': 'Y'},
                            {'ForeName': 'F',
                             'Initials': 'F',
                             'LastName': 'De Luca',
                             'ValidYN': 'Y'}],
             'Journal': {'ISOAbbreviation': 'J. Magn. Reson.',
                         'ISSN': {'ISSN': '1090-7807', 'IssnType': 'Print'},
                         'JournalIssue': {'CitedMedium': 'Print',
                                          'Issue': '1',
                                          'PubDate': datetime.date(2001, 11, 1),
                                          'Volume': '153'},
                         'Title': 'Journal of magnetic resonance (San Diego, Calif. : 1997)'},
             'Language': 'eng',
             'Pagination': {'MedlinePgn': '117-23'},
             'PubModel': 'Print',
             'PublicationTypeList': ['Journal Article']},
 'ArticleIds': {'doi': '10.1006/jmre.2001.2429',
                'pii': 'S1090-7807(01)92429-2',
                'pubmed': '11700088'},
 'DateCompleted': datetime.date(2001, 12, 20),
 'DateCreated': datetime.date(2001, 11, 8),
 'DateRevised': datetime.date(2003, 10, 31),
 'MedlineJournalInfo': {'Country': 'United States',
                        'ISSNLinking': '1090-7807',
                        'MedlineTA': 'J Magn Reson',
                        'NlmUniqueID': '9707935'},
 'Owner': 'NLM',
 'PMID': '11700088',
 '_id': '11700088',
 'Status': 'PubMed-not-MEDLINE'}]

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
        stream = FetchMedlineXml(pmids)

        for record in ParseMedlineXml(stream):
            self.assertEqual(pmids[self.count], int(record['_id']))
            self.count += 1

        self.assertEqual(self.count, len(pmids))

    def testParser(self):
        basicConfig()
        
        for record in ParseMedlineXml(self.xml_stream):
            self.assertDictEqual(PARSED_SAMPLE[self.count], record)
            self.count += 1

        self.assertEqual(self.count, len(PARSED_SAMPLE))

if __name__ == '__main__':
    unittest.main()