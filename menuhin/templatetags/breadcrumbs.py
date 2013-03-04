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
        if menu:
            logger.debug('finding breadcrumbs for %s only' % menu)
            items = get_menu(menu).nodes
        else:
            logger.debug('finding breadcrumbs using all menus' % menu)
            items = get_all_menus()
            items = chain.from_iterable([x.nodes for x in items.values()])

        try:
            url = thing_to_lookup.get_absolute_url()
        except AttributeError:
            # Might've been an object with a get_absolute_url method. Wasn't.
            # Now we're assuming it's a string or something we can actually use.
            url = thing_to_lookup

        def maybe_url_match(current_item):
            """ Relies on the parent context. Ugh. """
            if url in current_item.url:
                if len(current_item.url) <= url:
                    return True
            return False

        start = datetime.now()

        found_items = ifilter(maybe_url_match, items)
        found_and_sorted = sorted(found_items, key=attrgetter('url'))
        try:
            longest_match = found_and_sorted[0]
            other_matches = found_and_sorted[1:]
        except IndexError:
            longest_match = None
            other_matches = None

        end = datetime.now()
        duration1 = (end - start)
        logging_parts = (duration1.microseconds, duration1.seconds)
        logger.debug('filtering and sorting breadcrumbs took %d microseconds (%d seconds)' % logging_parts)
        return {
            'node': longest_match,
            'possibly_related': other_matches,
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
