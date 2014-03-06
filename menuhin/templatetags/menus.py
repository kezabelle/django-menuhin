# -*- coding: utf-8 -*-
import logging
from django.contrib.sites.models import Site
from classytags.core import Options
from classytags.arguments import Argument
from classytags.helpers import InclusionTag, AsTag
from menuhin.models import MenuItem
from django import template


register = template.Library()
logger = logging.getLogger(__name__)


class ShowMenu(InclusionTag, AsTag):
    template = 'menuhin/show_menu.html'
    options = Options(
        Argument('menu_slug', required=False, resolve=True,
                 default='default'),
        Argument('to_depth', required=False, resolve=True, default=100),
        Argument('template', required=False, resolve=True, default=None),
        'as', Argument('var', required=False, default=None, resolve=False)
    )

    def get_context(self, context, menu_slug, to_depth, template, **kwargs):
        request = None
        if 'request' in context:
            request = context['request']

        site = Site.objects.get_current()

        try:
            menu_root = MenuItem.objects.get(menu_slug=menu_slug, site=site,
                                             is_published=True)
        except MenuItem.DoesNotExist:
            return {}

        annotated_menu = MenuItem.get_published_annotated_list(
            parent=menu_root)

        return {
            'menu_nodes': tuple(x for x in annotated_menu
                                if x[1]['level'] <= to_depth),
            'to_depth': to_depth,
            'menu_root': menu_root,
            'template': template or self.template,
            'request_in_context': request is not None,
        }

    def render_tag(self, context, **kwargs):
        #: this is basically from the core :class:`~classytags.core.Tag`
        #: implementation but changed to allow us to have different output
        #: so that using it as an AS tag returns a *list* of nodes.
        varname = kwargs.get(self.varname_name, None)
        if varname:
            context[varname] = self.get_context(context, **kwargs)
            return ''
        return super(ShowMenu, self).render_tag(context, **kwargs)
register.tag(ShowMenu)
