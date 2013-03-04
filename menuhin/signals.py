# -*- coding: utf-8 -*-
from django.dispatch import Signal

shorturl_redirect = Signal(providing_args=["instance", "user"])
