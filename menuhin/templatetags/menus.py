# -*- coding: utf-8 -*-
import logging
from collections import namedtuple
from django.contrib.sites.models import Site
from classytags.core import Options
from classytags.arguments import Argument
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

        menu_slug = force_text(menu_slug)
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
            msg = "Unable to find menu item using {0!r}".format(lookup)
            logger.warning(msg, exc_info=1, extra={
                'request': context.get('request')
            })
            return base

        depth_filtered_menu = MenuItem.get_published_annotated_list(
            parent=menu_root, to_depth=to_depth)

        if 'request' in context:
            marked_annotated_menu = marked_annotated_list(
                request=context['request'],
                tree=depth_filtered_menu)
        else:  # pragma: no cover
            logger.info("Cannot calculate position in tree without a request")
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

    def get_template(self, context, **kwargs):
        template = kwargs.get('template', None)
        if template is not None:
            return template
        return super(ShowMenu, self).get_template(context, **kwargs)
register.tag(ShowMenu)


ItemWithMeta = namedtuple('ItemWithMeta', 'obj query')


class ShowBreadcrumbs(InclusionTag, AsTag):
    template = 'menuhin/show_breadcrumbs.html'
    name = "show_breadcrumbs"
    options = Options(
        Argument('path_or_menuslug', required=False, default='',
                 resolve=True),
        Argument('template', required=False, resolve=True, default=None),
        'as', Argument('var', required=False, default=None, resolve=False)
    )

    def get_menuitem(self, context, path_or_menuslug, site_instance):
        # allow for failing early.
        if isinstance(path_or_menuslug, MenuItem):
            return ItemWithMeta(obj=path_or_menuslug, query=None)

        path_or_menuslug = force_text(path_or_menuslug)
        if path_or_menuslug.isdigit():
            lookup = {'pk': int(path_or_menuslug)}
        elif slug_re.search(path_or_menuslug):
            lookup = {'menu_slug': path_or_menuslug}
        elif len(path_or_menuslug) > 0:
            lookup = {'uri__iexact': path_or_menuslug}
        elif 'request' in context:
            lookup = {'uri__iexact': context['request'].path}
        else:
            msg = ("Couldn't figure out a lookup method for argument "
                   "{0!r}".format(path_or_menuslug))
            logger.warning(msg, extra={
                'request': context.get('request')
            })
            return ItemWithMeta(obj=None, query=None)

        lookup.update(site=site_instance, is_published=True)

        try:
            obj = MenuItem.objects.select_related('site').get(**lookup)
            return ItemWithMeta(obj=obj, query=lookup)
        except MenuItem.DoesNotExist:
            msg = "Unable to find menu item using {0!r}".format(lookup)
            logger.warning(msg, exc_info=1, extra={
                'request': context.get('request')
            })
        return ItemWithMeta(obj=None, query=lookup)

    def get_context(self, context, path_or_menuslug, template, **kwargs):
        site = Site.objects.get_current()
        base = {
            'site': site,
            'template': template or self.template,
        }
        if 'request' in context:
            base.update(request=context['request'])

        # try to go by PK, or if there's no invalid characters (eg: /:_ ...)
        # by menu_slug, otherwise falling back to assuming the input is
        # request.path or whatevers.
        fetched_menuitem = self.get_menuitem(context, path_or_menuslug, site)
        menuitem = fetched_menuitem.obj
        if menuitem is None:
            return base

        menuitem.is_active = True
        base.update(query=fetched_menuitem.query)

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

    def get_template(self, context, **kwargs):
        template = kwargs.get('template', None)
        if template is not None:
            return template
        return super(ShowBreadcrumbs, self).get_template(context, **kwargs)
register.tag(ShowBreadcrumbs)
