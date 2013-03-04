# -*- coding: utf-8 -*-
from django.conf import settings

MENUHIN_MENU_HANDLERS = getattr(settings, 'MENUHIN_MENU_HANDLERS', None)
SHARED_CACHE_KEY = 'menuhin_menu'
NODE_CACHE_KEY_PREFIX = 'menuhin_nodes_%s'
TREE_CACHE_KEY_PREFIX = 'menuhin_tree_%s'
