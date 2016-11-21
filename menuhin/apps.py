# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from .finders import find_menus

class MenuhinConfig(AppConfig):
    name = 'menuhin'
    verbose_name = _("menus")

    def ready(self):
        retval = super(MenuhinConfig, self).ready()
        find_menus()
        return retval
