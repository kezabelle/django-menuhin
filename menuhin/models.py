# -*- coding: utf-8 -*-
import logging
from collections import namedtuple
from django.core.exceptions import ValidationError
from django.template.loader import Template
from django.template.context import Context
from django.utils.encoding import python_2_unicode_compatible
try:
    from django.utils.six.moves import urllib_parse
    urlsplit = urllib_parse.urlsplit
    urlunsplit = urllib_parse.urlunsplit
except (ImportError, AttributeError) as e:  # pragma: no cover Python 2, < Django 1.5
    from urlparse import urlsplit, urlunsplit

try:
    from django.utils.text import camel_case_to_spaces as get_verbose_name
except ImportError:  # pragma: no cover (Django < 1.7)
    from django.db.models.options import get_verbose_name

from treebeard.mp_tree import MP_Node
from django.db.models import (SlugField, ForeignKey, CharField, TextField,
                              BooleanField)
from django.contrib.sites.models import Site
# from model_utils.managers import PassThroughManager
from model_utils.models import TimeStampedModel
# from .querysets import MenuQuerySet
from .utils import (get_relations_for_request, set_menu_slug, get_title,
                    get_list_title)
# from helpfulfields.models import ChangeTracking, Publishing
from menuhin.text import (menu_v, menu_vp, title_label, title_help,
                          display_title_label, display_title_help,
                          menuitem_v, menuitem_vp)


logger = logging.getLogger(__name__)


def is_valid_uri(value):
    if not value.startswith(('http://', 'https://', '//', '/', '../', './')):
        raise ValidationError('Invalid URL')
    return True


@python_2_unicode_compatible
class MenuItem(TimeStampedModel, MP_Node):

    menu_slug = SlugField(max_length=100, verbose_name=title_label,
                          help_text=title_help, db_index=True)
    site = ForeignKey('sites.Site')
    title = CharField(max_length=50, verbose_name=display_title_label,
                      help_text=display_title_help)
    uri = TextField(validators=[is_valid_uri])
    is_published = BooleanField(default=False, db_index=True)
    is_active = False
    is_ancestor = False
    is_descendant = False
    is_sibling = False
    user_passes_test = True
    vary_on_user = False

    def __str__(self):
        return self.title  # pragma: no cover

    def __repr__(self):
        return ('<{name}: title: {title}, published: {status!s}, uri: {uri}, '
                'site_id: {site}>'.format(name=self.__class__.__name__,
                                          title=self.title,
                                          status=self.is_published,
                                          uri=self.uri, site=self.site_id))

    def clean(self):
        if not self.menu_slug:
            self.menu_slug = set_menu_slug(self.uri, model=MenuItem)

    def get_absolute_url(self):
        return self.uri

    def href(self):
        return self.uri

    def get_canonical_url(self):
        domain = self.site.domain.strip('/')
        path = self.get_absolute_url().lstrip('/')
        return '//{domain}/{path}'.format(domain=domain, path=path)

    def is_balanced(self, prefix, suffix):
        has_lefts = self.title.count(prefix)
        if has_lefts:
            has_rights = self.title.count(suffix)
            return has_rights == has_lefts
        return False

    def title_has_balanced_template_params(self):
        return self.is_balanced('{{', '}}')

    def title_has_balanced_format_params(self):
        return self.is_balanced('{', '}')

    def title_needs_parsing(self):
        return (self.title_has_balanced_template_params() or
                self.title_has_balanced_format_params())

    def parsed_title(self, context):
        if '{' not in self.title:
            return self.title
        if self.title_has_balanced_template_params():
            return Template(self.title).render(Context(context))
        elif self.title_has_balanced_format_params():
            return self.title.format(**context)
        return self.title

    @classmethod
    def get_published_annotated_list(cls, parent=None, **tree_kwargs):
        """
        copy paste job of the original `get_annotated_list` so that we can
        filter only published items, specifically for this.
        """
        result, info = [], {}
        start_depth, prev_depth = (None, None)

        if 'site' not in tree_kwargs:
            tree_kwargs.update(site=Site.objects.get_current())

        if 'is_published' not in tree_kwargs:
            tree_kwargs.update(is_published=True)

        # shuffle the depth around as necessary ...
        if 'to_depth' in tree_kwargs:
            maximum_depth = tree_kwargs.pop('to_depth')
            # go this far *from the parent*
            if parent is not None:
                maximum_depth += parent.get_depth()
            tree_kwargs.update(depth__lte=maximum_depth)

        qs = cls.get_tree(parent).select_related('site').filter(**tree_kwargs)
        for node in qs:
            depth = node.get_depth()
            if start_depth is None:
                start_depth = depth
            open = (depth and (prev_depth is None or depth > prev_depth))
            if prev_depth is not None and depth < prev_depth:
                info['close'] = list(range(0, prev_depth - depth))
            info = {'open': open, 'close': [], 'level': depth - start_depth}
            result.append((node, info,))
            prev_depth = depth
        if start_depth and start_depth > 0:
            info['close'] = list(range(0, prev_depth - start_depth + 1))
        return result

    class Meta:
        verbose_name = menuitem_v
        verbose_name_plural = menu_vp
        # ordering = ('-created', 'title')


class MenuItemGroup(object):

    @property
    def title(self):
        return get_verbose_name(self.__class__.__name__)

    def get_urls(self, *args, **kwargs):
        """
        This may yield individual items, or just return an iterable.
        The choice is YOUUURS.
        """
        raise NotImplementedError("Subclasses should implement this to yield "
                                  "`URI` instances.")


class InvalidModelError(ValueError): pass  # noqa


class ModelMenuItemGroup(MenuItemGroup):
    model = None

    def __init__(self):
        super(ModelMenuItemGroup, self).__init__()
        model = self.get_model()
        if model is None:
            raise InvalidModelError("No model class provided")
        if not hasattr(model, 'get_absolute_url'):
            raise InvalidModelError("{cls!r} lacks a `get_absolute_url` "
                                    "method")

    def get_model(self):
        return self.model

    def get_queryset(self):
        return self.get_model().objects.all().iterator()

    def get_urls(self):
        """
        Unlike the standard MenuItemGroup usage, which would yield
        individual items, this one collects into a complete iterable so
        that it may be de-duplicated for any list urls.
        """
        queryset = self.get_queryset()
        final_urls = set()
        for obj in queryset:

            abs_url = getattr(obj, 'get_absolute_url')
            if callable(abs_url):
                abs_url = abs_url()

            abs_obj = URI(path=abs_url, title=get_title(obj))
            if abs_obj not in final_urls:
                final_urls.add(abs_obj)

            # there's no definitive way I'd like the title part of the next
            # bit to work, so we just shove the URL in as the title.
            list_url = getattr(obj, 'get_list_url', None)
            if list_url is None:
                continue

            if callable(list_url):
                list_url = list_url()

            list_title = get_list_title(obj, url=list_url)
            list_obj = URI(path=list_url, title=list_title)
            if list_title is not None and list_obj not in final_urls:
                final_urls.add(list_obj)
        return final_urls


# collects just a path and a page title, used for inserting.
URI = namedtuple('URI', ('path', 'title'))
