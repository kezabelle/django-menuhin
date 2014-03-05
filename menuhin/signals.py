# -*- coding: utf-8 -*-
from django.dispatch import Signal

default_for_site_needed = Signal(providing_args=('site'))
default_for_site_created = Signal(providing_args=('site', 'instance'))
shorturl_redirect = Signal(providing_args=("instance", "user"))
rebuild_requested = Signal(providing_args=())
missing_inserted = Signal(providing_args=('found', 'missing'))
