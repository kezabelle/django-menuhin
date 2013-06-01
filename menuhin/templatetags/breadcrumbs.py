# -*- coding: utf-8 -*-
from collections import deque
from copy import copy
from datetime import datetime
import hashlib
from itertools import ifilter, chain
import logging
from operator import attrgetter
from classytags.core import Options
from classytags.arguments import Argument, KeywordArgument
from classytags.helpers import InclusionTag
from django import template
import itertools
from django.core.cache import cache
from django.core.validators import validate_slug
from menuhin.utils import get_all_menus, get_menu

register = template.Library()

logger = logging.getLogger(__name__)

class ShowBreadcrumbsForUrl(InclusionTag):
    template = 'menuhin/none.html'
    options = Options(
        Argument('thing_to_lookup', required=True, resolve=True, default=None),
        KeywordArgument('menu', required=False, resolve=True, default='')
    )

    def get_context(self, context, thing_to_lookup, menu):
        try:
            url = thing_to_lookup.get_absolute_url()
        except AttributeError:
            # Might've been an object with a get_absolute_url method. Wasn't.
            # Now we're assuming it's a string or something we can actually use.
            url = thing_to_lookup

        cache_key = 'show_breadcrumbs_%s' % hashlib.sha1(url).hexdigest()
        # try and get the cached dictionary back.
        cached_crumbs = cache.get(cache_key, None)
        if cached_crumbs is not None:
            return cached_crumbs

        # we can look for the request now that we know we can't return a result
        # from the cache; as we're passing the request back to the menu backend
        # we need it ...
        if 'request' not in context:
            logger.warning('request not in Context')
            return {}
        request = context['request']

        if menu:
            # make sure we haven't been dumb as hammers by validating this title
            # is something we could actually be storing.
            validate_slug(menu)
            logger.debug('finding breadcrumbs for %s only' % menu)
            items = get_menu(menu, request=request).nodes
        else:
            logger.debug('finding breadcrumbs using all menus')
            items = get_all_menus(request=request)
            items = chain.from_iterable([x.nodes for x in items.values()])

        def filter_only_active(input):
            return input.activity[0] is True

        first_active_node = itertools.ifilter(filter_only_active, items).next()
        # takes a copy of the node, so that there's not a potentially infinite
        # number of ancestors and descendants, I think?
        finalised_data = {
            'node': copy(first_active_node),
            'menu': menu,
        }
        cache.set(cache_key, finalised_data)
        return finalised_data

    def get_template(self, context, thing_to_lookup, menu):
        templates = deque([
            'menuhin/show_breadcrumbs/default.html',
            self.template,
        ])
        if menu:
            templates.appendleft('menuhin/show_breadcrumbs/%s/default.html' % menu)
        return list(templates)
register.tag(name='show_breadcrumbs', compile_function=ShowBreadcrumbsForUrl)
