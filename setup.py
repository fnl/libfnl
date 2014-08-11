#!/usr/bin/env python3
from distutils.core import setup

setup(
    name='libfnl',
    version='0.0.1',
    license='GNU Affero GPL v3',
    author='Florian Leitner',
    author_email='florian.leitner@gmail.com',
    url='https://github.com/fnl/libfnl',
    description='command-line tools for text mining',
    long_description=open('README.rst').read(),
    install_requires=[
        'fn >= 0.2.13',
        'html5lib >= 0.999',
        'nltk >= 3.0.0b1',
        #'psycopg2 >= 2.4',
        'pytest >= 2.6.0',
        'scikit-learn >= 0.12',
        'sqlalchemy >= 0.8',
        'Unidecode >= 0.04.16',
    ],
    packages=[
        'fnl',
        'fnl.nlp',
        'fnl.nlp.genia',
        'fnl.stat',
        'fnl.text',
        'fnl.utils',
    ],
    data_files=[
        ('var/fnl/dictionaries', ['mammalian_genes.csv', 'qualifier_order.txt']),
        ('var/fnl/models', ['medline_abstract_pst.bin']),
        ('var/nersuite/models', ['bc2gm.iob2.no_dic.m.xz', 'nlpba04.iob2.no_dic.m.xz']),
    ],
    scripts=[
        'scripts/fnlclassi.py',
        'scripts/fnlcorpus.py',
        'scripts/fnlcsvsimjoin.py',
        'scripts/fnldgrep.py',
        'scripts/fnldictag.py',
        'scripts/fnlgpcounter.py',
        'scripts/fnlkappa.py',
        'scripts/fnlrelex.py',
        'scripts/fnlsegment.py',
        'scripts/fnlsegtrain.py',
        'scripts/fnltok.py',
        'scripts/genia_ner.sh',
        'scripts/unique_tokens_on_line.py',
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Software Development :: Libraries',
        'Topic :: Text Processing',
        'Topic :: Text Processing :: Linguistic',
    ],
)
