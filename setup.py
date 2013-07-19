# -*- coding: utf-8 -*-
import setuptools

python_classifiers = [
    'Programming Language :: Python :: {0}'.format(py_version)
    for py_version in ['3', '3.3']]
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
    'BeautifulSoup4',
    'mako',
    'matplotlib',
    'numpy',
    'PyYAML',
    'requests',
    # Use `cd SOG; pip install -e .` to install SOG command processor
    # and its dependencies
]

setuptools.setup(
    name='SoG-bloomcast',
    version='3.0b1',
    description='Strait of Georgia spring diatom bloom predictor',
    author='Doug Latornell',
    author_email='djl@douglatornell.ca',
    url='http://eos.ubc.ca/~sallen/SoG-bloomcast/results.html',
    license="New BSD License",
    classifiers=python_classifiers + other_classifiers,
    install_requires=install_requires,
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': ['bloomcast = bloomcast.bloomcast:main']},
)
