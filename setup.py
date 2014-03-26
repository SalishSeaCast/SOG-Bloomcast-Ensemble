# Copyright 2011-2014 Doug Latornell and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""SoG-bloomcast -- Operational Prediction of the Strait of Georgia
Spring Phytoplankton Bloom
"""
import setuptools

import __pkg_metadata__


python_classifiers = [
    'Programming Language :: Python :: {0}'.format(py_version)
    for py_version in ['3', '3.3']]
other_classifiers = [
    'Development Status :: ' + __pkg_metadata__.DEV_STATUS,
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python :: Implementation :: CPython',
    'Operating System :: Unix',
    'Operating System :: MacOS :: MacOS X',
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Education',
]
try:
    long_description = open('README.rst', 'rt').read()
except IOError:
    long_description = ''
install_requires = [
    'arrow',
    'BeautifulSoup4',
    'cliff',
    'mako',
    'matplotlib',
    'numpy',
    'PyYAML',
    'requests',
    'Sphinx',
    'sphinx-bootstrap-theme',
    # Use `cd SOG; pip install -e .` to install SOG command processor
    # and its dependencies
]

setuptools.setup(
    name=__pkg_metadata__.PROJECT,
    version=__pkg_metadata__.VERSION,
    description=__pkg_metadata__.DESCRIPTION,
    long_description=long_description,
    author='Doug Latornell',
    author_email='djl@douglatornell.ca',
    url='http://eos.ubc.ca/~sallen/SoG-bloomcast/results.html',
    download_url=(
        'https://bitbucket.org/douglatornell/sog-bloomcast/get/default.tar.gz'),
    license='Apache License, Version 2.0',
    classifiers=python_classifiers + other_classifiers,
    platforms=['MacOS X', 'Linux'],
    install_requires=install_requires,
    packages=setuptools.find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        # The bloomcast command:
        'console_scripts': [
            'bloomcast = bloomcast.main:main',
        ],
        # Sub-command plug-ins:
        'bloomcast.app': [
            'ensemble = bloomcast.ensemble:Ensemble',
        ],
    },
)
