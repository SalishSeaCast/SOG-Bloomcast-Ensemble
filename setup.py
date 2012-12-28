# -*- coding: utf-8 -*-
from distutils.core import setup
import sys

PY26 = sys.version_info[0] == 2 and sys.version_info[1] == 6

python_classifiers = [
    'Programming Language :: Python :: {0}'.format(py_version)
    for py_version in ['2', '2.6', '2.7']]
other_classifiers = [
    'Development Status :: 5 - Production/Stable',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python :: Implementation :: CPython',
    'Operating System :: Unix',
    'Operating System :: MacOS :: MacOS X',
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Education',
]

install_requires = [
    'BeautifulSoup',
    'contextlib2',
    'mako',
    'matplotlib',
    'numpy',
    'PyYAML',
    'requests',
    # Use `cd SOG; pip install -e .` to install SOG command processor
    # and its dependencies
]
if PY26:
    install_requires.append('argparse')

setup(
    name='SoG-bloomcast',
    version='2.0',
    description='Strait of Georgia spring diatom bloom predictor',
    author='Doug Latornell',
    author_email='djl@douglatornell.ca',
    url='http://eos.ubc.ca/~sallen/SoG-bloomcast/results.html',
    license="New BSD License",
    classifiers=python_classifiers + other_classifiers,
    install_requires=install_requires,
    packages=['bloomcast'],
)
