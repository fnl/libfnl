from tempfile import TemporaryFile
from unittest import main, TestCase
from libfnl.nlp.genia.corpus import Reader

__author__ = 'Florian Leitner'

class PosReaderTests(TestCase):

    SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/css" href="gpml.css" ?>
<!DOCTYPE set SYSTEM "gpml.merged.dtd">
<set>

<import resource="GENIAontology.daml" prefix="G"></import>

<article>
<articleinfo>
<bibliomisc>MEDLINE:95369245</bibliomisc>
</articleinfo>
<title>
<sentence><w c="NN">IL-2</w> <w c="NN">gene</w> <w c="NN">expression</w> <w c="CC">and</w> <w c="NN">NF-kappa</w> <w c="NN">B</w> <w c="NN">activation</w> <w c="IN">through</w> <w c="NN">CD28</w> <w c="VBZ">requires</w> <w c="JJ">reactive</w> <w c="NN">oxygen</w> <w c="NN">production</w> <w c="IN">by</w> <w c="NN">5-lipoxygenase</w><w c=".">.</w></sentence>
</title>
<abstract>
<sentence><w c="NN">Activation</w> <w c="IN">of</w> <w c="DT">the</w> <w c="NN">CD28</w> <w c="NN">surface</w> <w c="NN">receptor</w> <w c="VBZ">provides</w> <w c="DT">a</w> <w c="JJ">major</w> <w c="JJ">costimulatory</w> <w c="NN">signal</w> <w c="IN">for</w> <w c="NN">T</w> <w c="NN">cell</w> <w c="NN">activation</w> <w c="VBG">resulting</w> <w c="IN">in</w> <w c="VBN">enhanced</w> <w c="NN">production</w> <w c="IN">of</w> <w c="NN">interleukin-2</w> <w c="(">(</w><w c="NN">IL-2</w><w c=")">)</w> <w c="CC">and</w> <w c="NN">cell</w> <w c="NN">proliferation</w><w c=".">.</w></sentence>
<sentence><w c="IN">In</w> <w c="JJ">primary</w> <w c="NN">T</w> <w c="NNS">lymphocytes</w> <w c="PRP">we</w> <w c="VBP">show</w> <w c="IN">that</w> <w c="NN">CD28</w> <w c="NN">ligation</w> <w c="VBZ">leads</w> <w c="TO">to</w> <w c="DT">the</w> <w c="JJ">rapid</w> <w c="JJ">intracellular</w> <w c="NN">formation</w> <w c="IN">of</w> <w c="JJ">reactive</w> <w c="NN">oxygen</w> <w c="NNS">intermediates</w> <w c="(">(</w><w c="NNS">ROIs</w><w c=")">)</w> <w c="WDT">which</w> <w c="VBP">are</w> <w c="VBN">required</w> <w c="IN">for</w> <w c="*">CD28</w><w c="JJ">-mediated</w> <w c="NN">activation</w> <w c="IN">of</w> <w c="DT">the</w> <w c="NN">NF-kappa</w> <w c="*">B</w><w c="*">/</w><w c="*">CD28</w><w c="JJ">-responsive</w> <w c="NN">complex</w> <w c="CC">and</w> <w c="NN">IL-2</w> <w c="NN">expression</w><w c=".">.</w></sentence>
</abstract>
</article>

<article>
<articleinfo>
<bibliomisc>MEDLINE:95333264</bibliomisc></articleinfo><title><sentence><w c="DT">The</w> <w c="NN">peri-kappa</w> <w c="NN">B</w> <w c="NN">site</w> <w c="VBZ">mediates</w> <w c="JJ">human</w> <w c="NN">immunodeficiency</w> <w c="NN">virus</w> <w c="NN">type</w> <w c="CD">2</w> <w c="NN">enhancer</w> <w c="NN">activation</w> <w c="IN">in</w> <w c="NNS">monocytes</w> <w c="CC">did</w><w c="RB">n't</w> <w c="IN">in</w> <w c="NN">T</w> <w c="NNS">cells</w><w c=".">.</w></sentence>
</title>
<abstract>
<sentence><w c="JJ">Human</w> <w c="NN">immunodeficiency</w> <w c="NN">virus</w> <w c="NN">type</w> <w c="CD">2</w> <w c="(">(</w><w c="NN">HIV-2</w><w c=")">)</w><w c=",">,</w> <w c="IN">like</w> <w c="NN">HIV-1</w><w c=",">,</w> <w c="VBZ">causes</w> <w c="NN">AIDS</w> <w c="CC">and</w> <w c="VBZ">is</w> <w c="VBN">associated</w> <w c="IN">with</w> <w c="NN">AIDS</w> <w c="NNS">cases</w> <w c="RB">primarily</w> <w c="IN">in</w> <w c="NNP">West</w> <w c="NNP">Africa</w><w c=".">.</w></sentence>
<sentence><w c="NN">HIV-1</w> <w c="CC">and</w> <w c="NN">HIV-2</w> <w c="VBP">display</w> <w c="JJ">significant</w> <w c="NNS">differences</w> <w c="IN">in</w> <w c="JJ">nucleic</w> <w c="NN">acid</w> <w c="NN">sequence</w> <w c="CC">and</w> <w c="IN">in</w> <w c="DT">the</w> <w c="JJ">natural</w> <w c="NN">history</w> <w c="IN">of</w> <w c="JJ">clinical</w> <w c="NN">disease</w><w c=".">.</w></sentence>
<sentence><w c="JJ">Consistent</w> <w c="IN">with</w> <w c="DT">these</w> <w c="NNS">differences</w><w c=",">,</w> <w c="PRP">we</w> <w c="VBP">have</w> <w c="RB">previously</w> <w c="VBN">demonstrated</w> <w c="IN">that</w> <w c="DT">the</w> <w c="NN">enhancer/promoter</w> <w c="NN">region</w> <w c="IN">of</w> <w c="NN">HIV-2</w> <w c="VBZ">functions</w> <w c="RB">quite</w> <w c="RB">differently</w> <w c="IN">from</w> <w c="DT">that</w> <w c="IN">of</w> <w c="NN">HIV-1</w><w c=".">.</w></sentence>
</abstract>
</article>

</set>
"""

    def setUp(self):
        self.file = TemporaryFile()
        self.file.write(PosReaderTests.SAMPLE.encode())
        self.file.seek(0)
        self.reader = Reader()

    def testReadingSample(self):
        count = 0
        sentences = [2, 4]
        pos_tags = [44, 86] # second: one less for joined "didn't"!

        for text in self.reader.toText(self.file):
            tags = text.tagtree
            self.assertEqual(1, len(tags[self.reader.section_ns][self.reader.abstract_tag]))
            self.assertEqual(1, len(tags[self.reader.section_ns][self.reader.title_tag]))
            self.assertEqual(sentences[count], len(tags[self.reader.section_ns][self.reader.sentence_tag]))
            self.assertEqual(pos_tags[count], sum(map(len, tags[self.reader.pos_tag_ns].values())))
            count += 1

        self.assertEqual(2, count)

if __name__ == '__main__':
    main()
