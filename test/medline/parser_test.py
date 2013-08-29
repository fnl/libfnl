from sqlite3 import dbapi2
from os.path import dirname
from unittest import main, TestCase
from sqlalchemy.engine.url import URL

from libfnl.medline.orm import *
from libfnl.medline.parser import *


__author__ = 'Florian Leitner'


class ParserTest(TestCase):
    MEDLINE_STRUCTURE_FILE = dirname(__file__) + '/data/medline.xml'
    PMID = 123
    ITEMS = [
        Section(PMID, 1, 'Title', '[a translated title].'),
        Identifier(PMID, 'doi', 'valid doi'),
        Identifier(PMID, 'pii', 'invalid pii'),
        Section(PMID, 2, 'Background', 'background text', 'background label'),
        Section(PMID, 3, 'Objective', 'objective text', 'objective label'),
        Section(PMID, 4, 'Methods', 'methods text', 'methods label'),
        Section(PMID, 5, 'Methods', 'duplicate methods', 'methods label'),
        Section(PMID, 6, 'Results', 'results text', 'results label'),
        Section(PMID, 7, 'Conclusions', 'conclusions text', 'conclusions label'),
        Section(PMID, 8, 'Unlabelled', 'unlabelled text with encoding–errors'),
        Section(PMID, 9, 'Abstract', 'abstract text', 'abstract label'),
        Section(PMID, 10, 'Abstract', 'default text'),
        Section(PMID, 11, 'Copyright', 'copyright info'),
        Author(PMID, 1, 'Author', forename='First'),
        Author(PMID, 2, 'Middle', suffix='Suf'),
        Author(PMID, 3, 'Author', forename='P Last', initials='PL'),
        Database(PMID, 'db1', 'acc1'),
        Database(PMID, 'db1', 'acc2'),
        Database(PMID, 'db1', 'acc3'),
        Database(PMID, 'db2', 'acc'),
        Section(PMID, 12, 'Vernacular', 'non-english article title'),
        Descriptor(PMID, 1, 'minor geographic descriptor'),
        Qualifier(PMID, 1, 1, 'minor qualifier'),
        Descriptor(PMID, 2, 'major descriptor', True),
        Qualifier(PMID, 2, 1, 'major qualifier', True),
        Qualifier(PMID, 2, 2, 'another qualifier'),
        Descriptor(PMID, 3, 'major descriptor', True),
        Qualifier(PMID, 3, 1, 'minor qualifier'),
        Descriptor(PMID, 4, 'minor descriptor'),
        Qualifier(PMID, 4, 1, 'major qualifier', True),
        Identifier(PMID, 'pmc', 'PMC12345'),
        Section(PMID, 13, 'Abstract', 'explanation for publisher abstract'),
        Section(PMID, 14, 'Conclusions', 'NASA conclusions', 'NASA label'),
        Section(PMID, 15, 'Copyright', 'NASA copyright'),
        Medline(PMID, 'MEDLINE', 'NLM Jour Abbrev',
                date(1974, 2, 19), date(1974, 11, 19), date(2006, 2, 14)),
        ]

    def setUp(self):
        self.file = open(ParserTest.MEDLINE_STRUCTURE_FILE)

    def testParseToDB(self):
        logging.getLogger().setLevel(logging.ERROR)
        InitDb(URL('sqlite'), module=dbapi2)
        self.sess = Session()
        count = 0
        # noinspection PyTypeChecker
        for item in Parse(self.file, None):
            count += 1
            self.sess.add(item)
        self.assertEqual(len(ParserTest.ITEMS), count)
        self.sess.commit()

    def testParseAll(self):
        logging.getLogger().setLevel(logging.ERROR)
        items = ParserTest.ITEMS
        # noinspection PyTypeChecker
        for i, item in enumerate(Parse(self.file, None)):
            self.assertEqual(str(items[i]), str(item))
            self.assertEqual(items[i], item)

    def testSkipRecords(self):
        for i in Parse(self.file, {123}):
            self.fail(str(i))

if __name__ == '__main__':
    main()
