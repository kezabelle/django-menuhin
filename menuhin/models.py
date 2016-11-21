# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import json
from collections import namedtuple
from itertools import chain
from operator import attrgetter

import swapper
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models
from django.db import transaction
from django.template import Context
from django.template import Template
from django.template import TemplateDoesNotExist
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.six import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from treebeard.mp_tree import MP_Node


def is_valid_uri(value):
    if not value.startswith(('http://', 'https://', '//', '/', '../', './')):
        raise ValidationError('Invalid URL')
    return True


@python_2_unicode_compatible
class TemplatedTitle(object):
    __slots__ = ('title',)
    def __init__(self, title):
        self.title = title

    def __str__(self):
        return self.title

    def is_balanced(self, prefix, suffix):
        has_lefts = self.title.count(prefix)
        if has_lefts:
            has_rights = self.title.count(suffix)
            return has_rights == has_lefts
        return False

    def has_balanced_template_params(self):
        return self.is_balanced('{{', '}}')

    def has_balanced_format_params(self):
        return self.is_balanced('{', '}')

    def title_needs_parsing(self):
        return (self.has_balanced_template_params() or
                self.has_balanced_format_params())

    def render(self, context):
        if '{' not in self.title:
            return self.title
        if self.has_balanced_template_params():
            return Template(self.title).render(Context(context))
        elif self.has_balanced_format_params():
            return self.title.format(**context)
        return self.title


@python_2_unicode_compatible
class BaseMenuItem(MP_Node):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    menu_slug = models.SlugField(max_length=100, verbose_name=_('unique key'),
                                 help_text=_('an internally consistent key used to find menus.'),
                                 db_index=True)
    title = models.CharField(max_length=50, verbose_name=_('title'),
                      help_text=_('a meaningful display title for this menu item'))
    uri = models.TextField(validators=[is_valid_uri], verbose_name=("URL"))
    is_published = models.BooleanField(default=False, db_index=True)
    # these exist to allow a given menuitem to reference an original object,
    # but are underscore prefixed to disallow access in the template.
    _original_content_type = models.ForeignKey(ContentType, related_name='+',
                                        default=None, null=True)
    _original_content_id = models.CharField(max_length=255, blank=False,
                                     default=None, null=True)
    _original_object = GenericForeignKey(ct_field="_original_content_type",
fk_field="_original_content_id")

    def __str__(self):
        return self.title  # pragma: no cover

    def __repr__(self):
        return ('<{name}: title: {title}, published: {status!s}, uri: {uri}>'.format(
            name=self.__class__.__name__, title=self.title,
            status=self.is_published, uri=self.uri))

    def get_absolute_url(self):
        return self.uri

    def href(self):
        return self.uri

    def original_object(self):
        try:
            return self._original_object
        except ObjectDoesNotExist:
            return None
    original_object.do_not_call_in_templates = True

    def parsed_title(self, context):
        return TemplatedTitle(title=self.title).render(context=context)

    def extra_context_template(self):
        template = 'menuhin/menuitem_context/%s.json' % (self.menu_slug,)
        try:
            return render_to_string(template)
        except TemplateDoesNotExist:
            return None
    extra_context_template.do_not_call_in_templates = True

    @cached_property
    def extra_context(self):
        template_data = self.extra_context_template()
        if template_data is None:
            return {}
        try:
            return json.loads(template_data)
        except (TypeError, ValueError) as e:
            return {}

    @classmethod
    def get_published_annotated_list(cls, parent=None, min_depth=None, max_depth=None):
        qs = cls.get_tree(parent).filter(is_published=True)

        parent_depth = 0
        if parent is not None:
            parent_depth = parent.get_depth()

        if min_depth:
            if parent is not None:
                min_depth += parent_depth
            qs = qs.filter(depth__gte=min_depth)
        if max_depth:
            if parent is not None:
                max_depth += parent_depth
            qs = qs.filter(depth__lte=max_depth)
        qs = qs.defer('_original_content_type', '_original_content_id')
        return cls.get_annotated_list_qs(qs)

    class Meta:
        index_together = (
            ('_original_content_type', '_original_content_id'),
        )
        abstract = True


class MenuItem(BaseMenuItem):
    class Meta:
        swappable = swapper.swappable_setting('menuhin', 'MenuItem')


class MenuItemGroup(object):
    @property
    def verbose_name(self):
        raise NotImplementedError("Subclasses should implement this.")

    def get_urls(self, *args, **kwargs):
        """
        This may yield individual items, or just return an iterable.
        The choice is YOUUURS.
        """
        raise NotImplementedError("Subclasses should implement this to yield "
"`URI` instances.")


URI = namedtuple('URI', 'path title')
class ModelURI(namedtuple('ModelURI', 'obj')):
    @property
    def path(self):
        instance = self.obj
        abs_url = instance.get_absolute_url
        if callable(abs_url):
            abs_url = abs_url()
        return abs_url

    @property
    def title(self):
        instance = self.obj
        if hasattr(instance, 'get_menu_title'):
            title = instance.get_menu_title()
        elif hasattr(instance, 'get_title'):
            title = instance.get_title()
        elif hasattr(instance, 'title'):
            title = instance.title
        elif hasattr(instance, 'get_headline'):
            title = instance.get_headline()
        elif hasattr(instance, 'headline'):
            title = instance.headline
        else:
            title = instance  # rely on calling str or unicode
        title = strip_tags(force_text(title)).strip()
        if title == "":
            title = '<No title>'
        return title

class ModelMenuItemGroup(MenuItemGroup):
    model = None

    def __init__(self):
        super(ModelMenuItemGroup, self).__init__()
        model = self.get_model()
        if model is None:
            raise ValueError("No model class provided")
        if not hasattr(model, 'get_absolute_url'):
            raise ValueError("{cls!r} lacks a `get_absolute_url` method")

    def get_model(self):
        return self.model

    @property
    def verbose_name(self):
        return self.get_model()._meta.verbose_name

    def get_queryset(self):
        return self.get_model().objects.all().iterator()

    def get_urls(self):
        queryset = self.get_queryset()
        seen_urls = set()
        final_urls = set()
        for obj in queryset:
            abs_obj = ModelURI(obj=obj)
            if abs_obj.path not in seen_urls:
                final_urls.add(abs_obj)
                seen_urls.add(abs_obj.path)
        return final_urls


class MenuRegistry(object):
    __slots__ = ('registry',)
    def __init__(self):
        self.registry = set()

    def register(self, item):
        self.registry.add(item)

    def unregister(self, item):
        self.registry.remove(item)

    def list(self):
        byname = attrgetter('verbose_name')
        bylen = attrgetter('path')
        menus = sorted(self.registry, key=byname)
        for menu in menus:
            menu = menu()
            urls = sorted(menu.get_urls(), key=bylen)
            yield byname(menu), urls

    def existing(self):
        model = swapper.load_model('menuhin', 'MenuItem')
        existing = model.objects.all()  #.values_list('uri', flat=True))
        return existing

    def items_to_update(self):
        existing = set(self.existing().values_list('uri', flat=True))
        items = tuple(self.list())
        for menu, urls in items:
            urls_to_update = []
            for url in urls:
                if url.path not in existing:
                    urls_to_update.append(url)
            if urls_to_update:
                yield menu, urls_to_update

    @transaction.atomic
    def update(self):
        items_to_update = tuple(self.items_to_update())
        items_to_update = tuple(chain.from_iterable(x[1] for x in items_to_update))
        if items_to_update:
            model = swapper.load_model('menuhin', 'MenuItem')
            added = []
            for item_to_update in items_to_update:
                path_slug = slugify(item_to_update.path)
                if not path_slug:
                    path_slug = slugify(item_to_update.title)
                if not path_slug:
                    path_slug = 'default'
                kwargs = {
                    'uri': item_to_update.path,
                    'is_published': False,
                    'title': item_to_update.title,
                    'menu_slug': path_slug,
                }
                original_obj = getattr(item_to_update, 'obj', None)
                if original_obj is not None:
                    kwargs.update({
                        '_original_content_type': ContentType.objects.get_for_model(
                            original_obj),
                        '_original_content_id': original_obj.pk
                    })
                instance = model.add_root(**kwargs)
                added.append(instance)
            return added
        else:
            return None


registry = MenuRegistry()
