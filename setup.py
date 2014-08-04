#!/usr/bin/env python3
from distutils.core import setup
# from Cython.Distutils import build_ext
# from distutils.extension import Extension

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
        'sqlalchemy >= 0.8',
        'psycopg2 >= 2.4',
        'nltk >= 3.0',
        'scikit-learn >= 0.12',
        'unidecode',
        'fn >= 0.2.13',
    ],
    # cmdclass = {'build_ext': build_ext},
    # ext_modules = [Extension("libfnl.nlp._text", ["libfnl/nlp/_text.pyx"])],
    packages=[
        'fnl',
        'fnl.gnamed',
        'fnl.gnamed.parsers',
        'fnl.medline',
        'fnl.nlp',
        'fnl.nlp.genia',
        'fnl.stat',
        'fnl.text',
        'fnl.utils',
    ],
    data_files=[
        ('var/fnl/models', ['medline_abstract_pst.bin']),
    ],
    package_dir={'': 'src'},
    scripts=[
        'scripts/fnlclass.py',
        'scripts/fnlclassi.py',
        'scripts/fnlcorpus.py',
        'scripts/fnldictag.py',
        'scripts/fnlgpcounter.py',
        'scripts/fnlkappa.py',
        'scripts/fnlsegment.py',
        'scripts/fnlsegment.py',
        'scripts/fnlsegtrain.py',
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
