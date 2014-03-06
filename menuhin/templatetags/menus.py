# -*- coding: utf-8 -*-
import logging
from django.contrib.sites.models import Site
from classytags.core import Options
from classytags.arguments import Argument
from classytags.helpers import InclusionTag, AsTag
from menuhin.models import MenuItem
from django import template
from django.core.validators import slug_re


register = template.Library()
logger = logging.getLogger(__name__)


class ShowMenu(InclusionTag, AsTag):
    template = 'menuhin/show_menu.html'
    name = "show_menu"
    options = Options(
        Argument('menu_slug', required=False, resolve=True,
                 default='default'),
        Argument('to_depth', required=False, resolve=True, default=100),
        Argument('template', required=False, resolve=True, default=None),
        'as', Argument('var', required=False, default=None, resolve=False)
    )

    def get_context(self, context, menu_slug, to_depth, template, **kwargs):
        site = Site.objects.get_current()
        base = {
            'to_depth': to_depth,
            'site': site,
            'template': template or self.template,
            'request_in_context': 'request' in context,
        }

        try:
            menu_root = MenuItem.objects.get(menu_slug=menu_slug, site=site,
                                             is_published=True)
        except MenuItem.DoesNotExist:
            return base

        annotated_menu = MenuItem.get_published_annotated_list(
            parent=menu_root)

        base.update(menu_root=menu_root,
                    menu_nodes=tuple(x for x in annotated_menu
                                     if x[1]['level'] <= to_depth))
        return base

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


class ShowBreadcrumbs(InclusionTag, AsTag):
    template = 'menuhin/show_breadcrumbs.html'
    name = "show_breadcrumbs"
    options = Options(
        Argument('path_or_menuslug', required=True, resolve=True),
        Argument('template', required=False, resolve=True, default=None),
        'as', Argument('var', required=False, default=None, resolve=False)
    )

    def get_context(self, context, path_or_menuslug, template, **kwargs):
        site = Site.objects.get_current()
        base = {
            'site': site,
            'template': template or self.template,
            'request_in_context': 'request' in context,
        }

        lookup = {'menu_slug': path_or_menuslug}
        if not slug_re.search(path_or_menuslug):
            lookup = {'uri__iexact': path_or_menuslug}
        lookup.update(site=site, is_published=True)
        base.update(query=lookup)
        try:
            menuitem = MenuItem.objects.get(**lookup)
        except MenuItem.DoesNotExist:
            return base
        base.update(ancestor_nodes=menuitem.get_ancestors(),
                    menu_node=menuitem,
                    child_nodes=menuitem.get_children())

        return base

    def render_tag(self, context, **kwargs):
        #: this is basically from the core :class:`~classytags.core.Tag`
        #: implementation but changed to allow us to have different output
        #: so that using it as an AS tag returns a *list* of nodes.
        varname = kwargs.get(self.varname_name, None)
        if varname:
            context[varname] = self.get_context(context, **kwargs)
            return ''
        return super(ShowBreadcrumbs, self).render_tag(context, **kwargs)
register.tag(ShowBreadcrumbs)
