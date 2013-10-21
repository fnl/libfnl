from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES
# from Cython.Distutils import build_ext
# from distutils.extension import Extension

for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

# TODO: MANIFEST.in with the .rst files in doc

setup(
    name='libfnl',
    version='1',
    license='GNU AGPL v3',
    author='Florian Leitner',
    author_email='florian.leitner@gmail.com',
    url='https://github.com/fnl/libfnl',
    description='tools for text mining in molecular biology',
    long_description=open('README.rst').read(),
    install_requires=[
        'sqlalchemy >= 0.8',
        'psycopg2 >= 2.4',
    ],
#    cmdclass = {'build_ext': build_ext},
#    ext_modules = [Extension("libfnl.nlp._text", ["libfnl/nlp/_text.pyx"])],
    packages=[
        'libfnl',
        'libfnl.gnamed',
        'libfnl.gnamed.parsers',
        'libfnl.medline',
        'libfnl.nlp.genia',
        'libfnl.stat',
        'libfnl.text',
        'libfnl.utils',
    ],
    package_dir={
        '': 'src',
    },
    scripts=['bin/fnlcorpus.py', 'bin/fnlgnamed.py', 'bin/fnlgpcounter.py', 'bin/fnlkappa.py', 'bin/fnlmedline.py'],
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
