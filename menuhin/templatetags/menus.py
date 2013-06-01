# -*- coding: utf-8 -*-
from copy import copy
from classytags.core import Tag, Options
from classytags.arguments import Argument
from classytags.helpers import InclusionTag, AsTag
from django import template
import itertools
from django.core.validators import validate_slug
from menuhin.utils import get_menu, get_all_menus

register = template.Library()



class ShowMenu(InclusionTag):
    template = 'menuhin/none.html'
    options = Options(
        Argument('title', required=True, resolve=True, default=None),
        Argument('from_depth', required=False, resolve=True, default=0),
        Argument('to_depth', required=False, resolve=True, default=100),
    )

    def get_context(self, context, title, from_depth, to_depth, **kwargs):
        # make sure we haven't been dumb as hammers by validating this title
        # is something we could actually be storing.
        validate_slug(title)

        request = None
        if 'request' in context:
            request = context['request']
            # request.path = '/weblog/2013/jan/a-temporary-addition-to-the-office/'
        menu = get_menu(key=title, request=request)

        def filter_depths(input):
            return input.depth >= from_depth and input.depth <= to_depth

        nodes = itertools.ifilter(filter_depths, menu.nodes)

        return {
            'nodes': list(nodes),
            'menu': menu,
            'from_depth': from_depth,
            'to_depth': to_depth,
        }

    def get_template(self, context, title, **kwargs):
        return [
            'menuhin/show_menu/%s/default.html' % title,
            'menuhin/show_menu/default.html',
            self.template,
        ]
register.tag(name='show_menu', compile_function=ShowMenu)


class ShowAllMenus(InclusionTag):
    template = 'menuhin/none.html'
#    options = Options(
#        Argument('title', required=False, resolve=True, default=None),
#    )

    def get_context(self, context):
        items = get_all_menus()
        import pdb; pdb.set_trace()
        return {}

    def get_template(self, context):
        return [
            'menuhin/show_all_menus/default.html',
            self.template,
        ]
register.tag(name='show_all_menus', compile_function=ShowAllMenus)

class GetMenu(AsTag):
    options = Options(
        Argument('title', required=False, resolve=True, default=None),
    )
    def get_value(self, context, title):
        menu = get_menu(title)
        return {
            'nodes': menu.nodes,
            'menu': menu,
        }
register.tag(name='get_menu', compile_function=GetMenu)
