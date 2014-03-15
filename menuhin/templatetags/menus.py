# -*- coding: utf-8 -*-
import logging
from django.contrib.sites.models import Site
from classytags.core import Options
from classytags.arguments import Argument, StringArgument
from classytags.helpers import InclusionTag, AsTag
from menuhin.models import MenuItem
from menuhin.utils import marked_annotated_list
from django import template
from django.core.validators import slug_re
try:
    from django.utils.encoding import force_text
except ImportError:  # pragma: no cover
    from django.utils.encoding import force_unicode as force_text


register = template.Library()
logger = logging.getLogger(__name__)


@register.simple_tag(takes_context=True)
def parse_title(context, obj):
    if not hasattr(obj, 'parsed_title'):
        return ''

    kwargs = dict((attr, getattr(obj, attr))
                  for attr in obj._meta.get_all_field_names()
                  if attr != 'title')
    if 'request' in context:
        kwargs.update(request=context['request'])
    return obj.parsed_title(context=kwargs)


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
        }
        if 'request' in context:
            base.update(request=context['request'])

        # if doing a PK lookup, given the PK is unique across any site, assume
        # the user knows wtf they're doing, so don't ask for only this site,
        # as that may never match.
        if menu_slug.isdigit():
            lookup = {'pk': int(menu_slug), 'is_published': True}
        # this is the most common operation ...
        else:
            lookup = {'menu_slug': menu_slug, 'site': site,
                      'is_published': True}
        base.update(query=lookup)
        try:
            menu_root = MenuItem.objects.select_related('site').get(**lookup)
        except MenuItem.DoesNotExist:
            return base

        annotated_menu = MenuItem.get_published_annotated_list(
            parent=menu_root)
        depth_filtered_menu = tuple(x for x in annotated_menu
                                    if x[1]['level'] <= to_depth)

        if 'request' in context:
            marked_annotated_menu = marked_annotated_list(
                request=context['request'],
                tree=depth_filtered_menu)
        else:
            marked_annotated_menu = depth_filtered_menu

        base.update(menu_root=menu_root,
                    menu_nodes=marked_annotated_menu)
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
        Argument('path_or_menuslug', required=False, default='',
                 resolve=True),
        Argument('template', required=False, resolve=True, default=None),
        'as', Argument('var', required=False, default=None, resolve=False)
    )

    def get_context(self, context, path_or_menuslug, template, **kwargs):
        site = Site.objects.get_current()
        base = {
            'site': site,
            'template': template or self.template,
        }
        if 'request' in context:
            base.update(request=context['request'])

        path_or_menuslug = force_text(path_or_menuslug)
        # try to go by PK, or if there's no invalid characters (eg: /:_ ...)
        # by menu_slug, otherwise falling back to assuming the input is
        # request.path or whatevers.
        if path_or_menuslug.isdigit():
            lookup = {'pk': int(path_or_menuslug)}
        elif slug_re.search(path_or_menuslug):
            lookup = {'menu_slug': path_or_menuslug}
        elif len(path_or_menuslug) > 0:
            lookup = {'uri__iexact': path_or_menuslug}
        elif 'request' in context:
            lookup = {'uri__iexact': context['request'].path}
        else:
            return base

        lookup.update(site=site, is_published=True)
        base.update(query=lookup)
        try:
            menuitem = MenuItem.objects.select_related('site').get(**lookup)
        except MenuItem.DoesNotExist:
            return base
        menuitem.is_active = True

        def marked_ancestors():
            ancestors = (menuitem.get_ancestors()
                         .select_related('site')
                         .filter(is_published=True, site=site))
            for ancestor in ancestors:
                ancestor.is_ancestor = True
                yield ancestor

        def marked_children():
            children = (menuitem.get_children()
                        .select_related('site')
                        .filter(is_published=True, site=site))
            for child in children:
                child.is_descendant = True
                yield child

        base.update(ancestor_nodes=tuple(marked_ancestors()),
                    menu_node=menuitem,
                    child_nodes=tuple(marked_children()))
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
