# -*- coding: utf-8 -*-
from collections import deque
from datetime import datetime
from itertools import ifilter, chain
import logging
from operator import attrgetter
from classytags.core import Options
from classytags.arguments import Argument, KeywordArgument
from classytags.helpers import InclusionTag
from django import template
import itertools
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
        if 'request' not in context:
            logger.warning('request not in Context')
            return {}
        request = context['request']

        if menu:
            logger.debug('finding breadcrumbs for %s only' % menu)
            items = get_menu(menu, request=request).nodes
        else:
            logger.debug('finding breadcrumbs using all menus' % menu)
            items = get_all_menus(request=request)
            items = chain.from_iterable([x.nodes for x in items.values()])

        try:
            url = thing_to_lookup.get_absolute_url()
        except AttributeError:
            # Might've been an object with a get_absolute_url method. Wasn't.
            # Now we're assuming it's a string or something we can actually use.
            url = thing_to_lookup

        start = datetime.now()

        def filter_only_active(input):
            return input.activity[0] is True

        try:
            first_active_node = itertools.ifilter(filter_only_active, items).next()
        except:
            # Can't remember what I needed to catch :\
            first_active_node = None

        end = datetime.now()
        duration1 = (end - start)
        logging_parts = (duration1.microseconds, duration1.seconds)
        logger.debug('filtering breadcrumbs took %d microseconds (%d seconds)' % logging_parts)

        return {
            'node': first_active_node,
            'menu': menu,
        }

    def get_template(self, context, thing_to_lookup, menu):
        templates = deque([
            'menuhin/show_breadcrumbs/default.html',
            self.template,
        ])
        if menu:
            templates.appendleft('menuhin/show_breadcrumbs/%s/default.html' % menu)
        return list(templates)
register.tag(name='show_breadcrumbs', compile_function=ShowBreadcrumbsForUrl)
