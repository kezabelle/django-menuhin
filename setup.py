#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
from setuptools import setup

try:
    from setuptest import test
    test_config = {
        'cmdclass': {'test': test}
    }
except ImportError:
    test_config = {
        'tests_require': (
            'django-setuptest',
            ),
        'test_suite': 'setuptest.setuptest.SetupTestSuite'
    }
    for argument in ('--failfast', '--autoreload', '--label'):
        if argument in sys.argv:
            sys.argv.remove(argument)


HERE = os.path.abspath(os.path.dirname(__file__))

def make_readme(root_path):
    FILES = ('README.rst', 'LICENSE', 'CHANGELOG', 'CONTRIBUTORS')
    for filename in FILES:
        filepath = os.path.realpath(os.path.join(HERE, filename))
        if os.path.isfile(filepath):
            with open(filepath, mode='r') as f:
                yield f.read()

LONG_DESCRIPTION = "\r\n\r\n----\r\n\r\n".join(make_readme(HERE))

setup(
    name='django-menuhin',
    version='0.1.0',
    author='Keryn Knight',
    author_email='python-package@kerynknight.com',
    description="generating menus for Django apps",
    long_description=LONG_DESCRIPTION,
    packages=[
        'menuhin',
    ],
    include_package_data=True,
    install_requires=[
        'Django>=1.3',
        'django-model-utils>=1.5',
        'django-classy-tags>=0.4',
    ],
    tests_require=[
        'django-setuptest>=0.1.4',
        'model-mommy>=1.2',
        'django-pdb>=0.3.2',
    ],
    zip_safe=False,
    keywords='django menu',
    license="BSD License",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Framework :: Django',
        'Natural Language :: English',
        'Environment :: Web Environment',
        'Topic :: Internet :: WWW/HTTP',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
    **test_config
)
