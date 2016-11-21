# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from functools import partial
from itertools import chain

from django.apps import apps
from django.conf import settings
try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module
from django.utils.module_loading import import_string


def project_finder():
    root = settings.BASE_DIR
    try:
        yield import_module('%(root)s.menuhin_menus' % {'root': root})
    except ImportError as e:
        pass


def apps_finder():
    app_configs = apps.get_app_configs()
    for app_config in app_configs:
        root = app_config.name
        try:
            yield import_module('%(root)s.menuhin_menus' % {'root': root})
        except ImportError as e:
            continue


def get_finders():
    defaults = ('menuhin.finders.apps_finder', 'menuhin.finders.project_finder')
    finders = getattr(settings, 'MENUHIN_FINDERS', defaults)
    for finder in finders:
        if finder == 'menuhin.finders.apps_finder':
            yield apps_finder
        elif finder == 'menuhin.finders.project_finder':
            yield project_finder
        else:
            yield partial(import_string, dotted_path=finder)


def find_menus():
    finders = tuple(get_finders())
    found = (finder() for finder in finders)
    found_unwrapped = tuple(chain.from_iterable(found))
    return found_unwrapped
