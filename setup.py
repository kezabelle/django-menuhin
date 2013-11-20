#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

HERE = os.path.abspath(os.path.dirname(__file__))


setup(
    name='django-menuhin',
    version='0.1.0',
    author='Keryn Knight',
    author_email='python-package@kerynknight.com',
    description="generating menus for Django apps",
    long_description=open(os.path.join(HERE, 'README.rst')).read(),
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
    test_suite='setuptest.setuptest.SetupTestSuite',
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
)
