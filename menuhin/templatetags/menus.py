# -*- coding: utf-8 -*-
import logging
from collections import namedtuple
from django.contrib.sites.models import Site
from classytags.core import Options
from classytags.arguments import Argument, IntegerArgument
from classytags.helpers import InclusionTag, AsTag
from django.db.models.query_utils import DeferredAttribute
from django.utils.functional import lazy
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

ItemWithMeta = namedtuple('ItemWithMeta', 'obj query')
FieldAttrNames = namedtuple('FieldAttrNames', 'name attname')


@register.simple_tag(takes_context=True)
def parse_title(context, obj):
    if not hasattr(obj, 'parsed_title'):
        return ''

    # concrete_fields doesn't exist under < Django 1.6
    try:
        concrete_fields = (x for x in obj._meta.concrete_fields)
    except AttributeError:
        concrete_fields = (field for field in obj._meta.fields
                           if field.column is not None)
    concrete_fieldnames_attnames = tuple(
        FieldAttrNames(name=x.name, attname=x.attname)
        for x in concrete_fields
    )
    # check both name and attname because deferring _original_content_type
    # requires us check both ...
    undeferred = (
        possible_attr for possible_attr in concrete_fieldnames_attnames
        if not isinstance(obj.__class__.__dict__.get(possible_attr.name), DeferredAttribute)  # noqa
        and not isinstance(obj.__class__.__dict__.get(possible_attr.attname), DeferredAttribute)  # noqa
    )
    final_fieldnames = (final_attr for final_attr in undeferred
                        if final_attr.name != 'title')
    kwargs = dict((attr.name, getattr(obj, attr.name))
                  for attr in final_fieldnames)
    if 'request' in context:
        kwargs.update(request=context['request'])
    return obj.parsed_title(context=kwargs)


class GetMenuItem(object):
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
            obj = (MenuItem.objects.select_related('site')
                   .defer('_original_content_type', '_original_content_id')
                   .get(**lookup))
            return ItemWithMeta(obj=obj, query=lookup)
        except MenuItem.DoesNotExist:
            msg = "Unable to find menu item using {0!r}".format(lookup)
            logger.warning(msg, exc_info=1, extra={
                'request': context.get('request')
            })
        return ItemWithMeta(obj=None, query=lookup)


class ShowMenu(GetMenuItem, InclusionTag, AsTag):
    template = 'menuhin/show_menu.html'
    name = "show_menu"
    options = Options(
        Argument('menu_slug', required=False, resolve=True,
                 default='default'),
        IntegerArgument('from_depth', required=False, resolve=True, default=0),
        IntegerArgument('to_depth', required=False, resolve=True, default=100),
        Argument('template', required=False, resolve=True, default=None),
        'as', Argument('var', required=False, default=None, resolve=False)
    )

    def get_context(self, context, menu_slug, from_depth, to_depth, template, **kwargs):
        site = Site.objects.get_current()
        # allow passing through None or "" ...
        if not from_depth:
            from_depth = 0
        # allow passing through None or "" ...
        if not to_depth:
            to_depth = 100
        base = {
            'to_depth': to_depth,
            'from_depth': from_depth,
            'site': site,
            'template': template or self.template,
        }
        if 'request' in context:
            base.update(request=context['request'])

        # try to go by PK, or if there's no invalid characters (eg: /:_ ...)
        # by menu_slug, otherwise falling back to assuming the input is
        # request.path or whatevers.
        fetched_menuitem = self.get_menuitem(context, menu_slug, site)
        menu_root = fetched_menuitem.obj
        base.update(query=fetched_menuitem.query)

        if menu_root is None:
            return base

        menu_root.is_active = True
        depth_filtered_menu = MenuItem.get_published_annotated_list(
            parent=menu_root, from_depth=from_depth, to_depth=to_depth)

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


class ShowBreadcrumbs(GetMenuItem, InclusionTag, AsTag):
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

        # try to go by PK, or if there's no invalid characters (eg: /:_ ...)
        # by menu_slug, otherwise falling back to assuming the input is
        # request.path or whatevers.
        fetched_menuitem = self.get_menuitem(context, path_or_menuslug, site)
        menuitem = fetched_menuitem.obj
        base.update(query=fetched_menuitem.query)

        if menuitem is None:
            return base

        menuitem.is_active = True

        def marked_ancestors():
            ancestors = (menuitem.get_ancestors()
                         .select_related('site')
                         .defer('_original_content_type', '_original_content_id')
                         .filter(is_published=True, site=site))
            for ancestor in ancestors:
                ancestor.is_ancestor = True
                yield ancestor

        def marked_children():
            """
            This returns a list because it's lazy, because it's not always
            accessed. Repeated iterations will each do database queries.
            """
            out = []
            children = (menuitem.get_children()
                        .select_related('site')
                        .filter(is_published=True, site=site))
            for child in children:
                child.is_descendant = True
                out.append(child)
            return out

        base.update(ancestor_nodes=tuple(marked_ancestors()),
                    menu_node=menuitem,
                    child_nodes=lazy(marked_children, list))
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
