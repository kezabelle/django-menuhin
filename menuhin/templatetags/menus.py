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


class ShowMenu(InclusionTag, AsTag):
    template = 'menuhin/none.html'
    options = Options(
        Argument('title', required=True, resolve=True, default=None),
        Argument('from_depth', required=False, resolve=True, default=0),
        Argument('to_depth', required=False, resolve=True, default=100),
        Argument('template', required=False, resolve=True, default=None),
        'as', Argument('var', required=False, default=None, resolve=False)

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
        template = kwargs.get('template', None)
        if template is not None:
            return [template]
        return [
            'menuhin/show_menu/%s/default.html' % title,
            'menuhin/show_menu/default.html',
            self.template,
        ]

    def render_tag(self, context, **kwargs):
        #: this is basically from the core :class:`~classytags.core.Tag`
        #: implementation but changed to allow us to have different output
        #: so that using it as an AS tag returns a *list* of nodes.
        varname = kwargs.get(self.varname_name, None)
        if varname:
            context[varname] = self.get_context(context, **kwargs)
            return ''
        return super(ShowMenu, self).render_tag(context, **kwargs)
register.tag(name='show_menu', compile_function=ShowMenu)
