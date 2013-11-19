# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='django-menuhin',
    version='0.1.0',
    author='Keryn Knight',
    author_email='python-package@kerynknight.com',
    packages=[
        'menuhin',
    ],
    include_package_data=True,
    install_requires=[
        'Django>=1.3',
        'django-model-utils>=1.5',
    ],
    tests_require=[
        'django-setuptest>=0.1.4',
    ],
    test_suite='setuptest.setuptest.SetupTestSuite',
    zip_safe=False,
    keywords='django menu',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Framework :: Django',
        'Natural Language :: English',
        'Environment :: Web Environment',
        'Topic :: Internet :: WWW/HTTP',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)
