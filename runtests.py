#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.conf import settings
import django


def get_settings():
    import test_settings
    setting_attrs = {}
    for attr in dir(test_settings):
        if attr.isupper():
            setting_attrs[attr] = getattr(test_settings, attr)
    return setting_attrs


def runtests():
    if not settings.configured:
        settings.configure(**get_settings())

    # Compatibility with Django 1.7's stricter initialization
    if hasattr(django, 'setup'):
        django.setup()

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    try:
        from django.test.runner import DiscoverRunner as Runner
        test_args = ['menuhin.tests']
    except ImportError:
        from django.test.simple import DjangoTestSuiteRunner as Runner
        test_args = ['menuhin']
    failures = Runner(
        verbosity=2, interactive=True, failfast=False).run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests()
