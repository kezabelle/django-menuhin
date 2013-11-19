# -*- coding: utf-8 -*-
import logging
from classytags.core import Options
from classytags.arguments import Argument
from classytags.helpers import InclusionTag, AsTag
from menuhin.models import Menu
from django import template
import itertools
from django.core.validators import validate_slug


register = template.Library()
logger = logging.getLogger(__name__)


class ShowMenu(InclusionTag):
    template = 'menuhin/none.html'
    options = Options(
        Argument('title', required=True, resolve=True, default=None),
        Argument('from_depth', required=False, resolve=True, default=0),
        Argument('to_depth', required=False, resolve=True, default=100),
    )

    def get_context(self, context, title, from_depth, to_depth, **kwargs):
        request = None
        if 'request' in context:
            request = context['request']
        FoundMenu = Menu.menus.model_slug(title)
        nodes = FoundMenu.menus.filter(request=request, min_depth=from_depth,
                                       max_depth=to_depth)
        final_nodes = list(nodes)
        return {
            'nodes': final_nodes,
            'menu': FoundMenu,
            'from_depth': from_depth,
            'to_depth': to_depth,
            'is_submenu': False,
        }

    def get_template(self, context, title, **kwargs):
        return [
            'menuhin/show_menu/%s/default.html' % title,
            'menuhin/show_menu/default.html',
            self.template,
        ]
register.tag(name='show_menu', compile_function=ShowMenu)


class GetMenu(AsTag):
    options = ShowMenu.options

    def get_value(self, *args, **kwargs):
        return ShowMenu().get_context(*args, **kwargs)
register.tag(name='get_menu', compile_function=GetMenu)


class ShowSubMenu(InclusionTag):
    template = ShowMenu.template
    options = Options(
        Argument('url', required=True, resolve=True, default=100),
        Argument('to_depth', required=False, resolve=True, default=100),
        Argument('menu', required=False, resolve=True, default=None),
    )

    def get_context(self, context, url, to_depth, menu, **kwargs):
        # we can look for the request now that we know we can't return a result
        # from the cache; as we're passing the request back to the menu backend
        # we need it ...
        if 'request' not in context:
            logger.warning('request not in Context')
            return {}
        request = context['request']

        if menu:
            logger.debug('finding matching node for for %s only' % menu)
            items = get_menu(menu, request=request).filter_active(request=request)
        else:
            logger.debug('finding matching node using all menus')
            items = get_all_menus(request=request)
            items = itertools.chain.from_iterable([x.filter_active(request=request)
                                                   for x in items.values()])

        try:
            url = url.get_absolute_url()
        except AttributeError:
            # Might've been an object with a get_absolute_url method. Wasn't.
            # Now we're assuming it's a string or something we can actually use.
            pass

        # hmmm, this could probably use the active calculator?
        try:
            first_active_node = items.next()
            max_depth = first_active_node.depth + to_depth
            descendants = (x for x in first_active_node.descendants
                           if x.depth <= max_depth)
        except StopIteration as e:
            first_active_node = None
            descendants = ()

        return {
            'node': first_active_node,
            'nodes': descendants,
            'menu': menu,
            'to_depth': to_depth,
            'is_submenu': True,
        }

    def get_template(self, context, menu, **kwargs):
        return [
            'menuhin/show_menu/%s/default.html' % menu,
            'menuhin/show_menu/default.html',
            self.template,
        ]
register.tag(name='show_sub_menu', compile_function=ShowSubMenu)
