# -*- coding: utf-8 -*-
import logging
from collections import namedtuple
from django.template.loader import Template
from django.template.context import Context
from django.utils.encoding import python_2_unicode_compatible
try:
    from django.utils.six.moves import urllib_parse
    urlsplit = urllib_parse.urlsplit
    urlunsplit = urllib_parse.urlunsplit
except (ImportError, AttributeError) as e:  # Python 2, < Django 1.5
    from urlparse import urlsplit, urlunsplit

try:
    from django.utils.text import camel_case_to_spaces as get_verbose_name
except ImportError:  # pragma: no cover (Django < 1.7)
    from django.db.models.options import get_verbose_name

from treebeard.mp_tree import MP_Node
from django.db.models import (SlugField, ForeignKey, CharField, TextField,
                              BooleanField)
# from model_utils.managers import PassThroughManager
from model_utils.models import TimeStampedModel
# from .querysets import MenuQuerySet
from .utils import get_relations_for_request
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
    # objects = TreePageManager()
    # node_order_by = ('path', 'depth')

    # def to_namedtuple(self):
    #     return SafeMenuItem(menu_slug=self.menu_slug, site_id=self.site_id,
    #                         title=self.title, uri=self.uri)

    def __str__(self):
        return self.title

    def clean(self):
        if not self.menu_slug:
            self.menu_slug = set_menu_slug(self.uri, model=MenuItem)

    def get_absolute_url(self):
        return self.uri

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
    def get_published_annotated_list(cls, parent=None):
        """
        Gets an annotated list from a tree branch.

        :param parent:

            The node whose descendants will be annotated. The node itself
            will be included in the list. If not given, the entire tree
            will be annotated.
        """
        result = super(MenuItem, cls).get_annotated_list(parent)
        for base_result in result:
            if base_result[0].is_published:
                yield base_result
            else:
                yield base_result
        # return result

    class Meta:
        verbose_name = menuitem_v
        verbose_name_plural = menu_vp
        # ordering = ('-created', 'title')


class MenuItemGroup(object):

    @property
    def title(self):
        return get_verbose_name(self.__class__.__name__)

    def get_urls(self, *args, **kwargs):
        raise NotImplementedError("Subclasses should implement this to yield "
                                  "`URI` instances.")

# collects just a path and a page title, used for inserting.
URI = namedtuple('URI', ('path', 'title'))


# class SafeMenuItem(namedtuple('SafeMenuItem', ['menu_slug', 'site_id',
#                    'title', 'uri'])):


def get_ancestors_for_request(request):
    return get_relations_for_request(model=MenuItem, request=request,
                                     relation='get_ancestors').relations


def get_descendants_for_request(request):
    return get_relations_for_request(model=MenuItem, request=request,
                                     relation='get_descendants').relations
