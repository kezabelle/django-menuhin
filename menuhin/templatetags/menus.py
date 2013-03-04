# -*- coding: utf-8 -*-
from classytags.core import Tag, Options
from classytags.arguments import Argument
from classytags.helpers import InclusionTag, AsTag
from django import template
from menuhin.utils import get_menu, get_all_menus

register = template.Library()

class ShowMenu(InclusionTag):
    template = 'menuhin/none.html'
    options = Options(
        Argument('title', required=False, resolve=True, default=None),
    )

    def get_context(self, context, title):
        menu = get_menu(title)
        return {
            'nodes': menu.nodes,
            'menu': menu,
        }

    def get_template(self, context, title):
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
