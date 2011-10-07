from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES
# from Cython.Distutils import build_ext
# from distutils.extension import Extension

for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

import libfnl

# TODO: MANIFEST.in with the .rst files (README and doc)

setup(
    name='libfnl',
    version='.'.join(map(str, libfnl.__version__)),
    description='A toolset for real-world NLP.',
    license='GNU AGPL v3',
    author='Florian Leitner',
    author_email='florian.leitner@gmail.com',
    url='https://github.com/fnl/libfnl',
#    cmdclass = {'build_ext': build_ext},
#    ext_modules = [Extension("libfnl.nlp._text", ["libfnl/nlp/_text.pyx"])],
    packages=[
        'libfnl',
        'libfnl.couch',
        'libfnl.nlp',
        'libfnl.nlp.genia',
        'libfnl.stat',
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: POSIX',
        'Programming Language :: C',
        'Programming Language :: C++',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Software Development :: Libraries',
        'Topic :: Text Processing',
        'Topic :: Text Processing :: Linguistic',
    ],
    package_data={'biocreative.evaluation': ['configuration.ini']},
    scripts=['bin/corpus.py', 'bin/kappa.py']
)