# -*- coding: utf-8 -*-
import logging
from urlparse import urlparse
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.db.models import SlugField, ForeignKey, CharField
from django.utils.functional import cached_property
from django.contrib.contenttypes.models import ContentType
from django.http import QueryDict
from django.utils.importlib import import_module
from model_utils import Choices
from model_utils.managers import PassThroughManager
from helpfulfields.models import ChangeTracking, Publishing
from menuhin.settings import MENUHIN_MENU_HANDLERS
from menuhin.text import (menu_v, menu_vp, title_label, title_help,
                          display_title_label, display_title_help)
from menuhin.querysets import MenuQuerySet, CustomMenuItemQuerySet, MenuFinder


logger = logging.getLogger(__name__)


class Menu(ChangeTracking, Publishing):
    site = ForeignKey(Site, default=Site.objects.get_current)
    title = SlugField(max_length=50, primary_key=True,
                      verbose_name=title_label, help_text=title_help)
    display_title = CharField(max_length=50, verbose_name=display_title_label,
                              help_text=display_title_help)

    objects = PassThroughManager.for_queryset_class(MenuQuerySet)()
    menus = MenuFinder()

    def __unicode__(self):
        """Reserved for admin/form usage."""
        return self.title

    def get_nodes(self, parent_node=None):
        raise NotImplementedError('Subclasses should provide this implementation')

    class Meta:
        verbose_name = menu_v
        verbose_name_plural = menu_vp
        unique_together = ('site', 'title')


class CustomMenuItem(ChangeTracking, Publishing):
    menu = ForeignKey(Menu, related_name="menu_items")
    POSITIONS = Choices('above', 'replacing', 'below')
    position = CharField(choices=POSITIONS, default=POSITIONS.above, max_length=5)
    title = CharField(max_length=100, verbose_name=display_title_label)
    url = CharField(max_length=2048)
    # store the parent_id of the menunode to work with.
    target_id = CharField(max_length=100)
    attach_menu = ForeignKey(Menu, related_name="attached_to", null=True)
    objects = PassThroughManager.for_queryset_class(CustomMenuItemQuerySet)()

    @cached_property
    def unique_id(self):
        return 'custom_menu_item_%s' % self.pk

    def get_attach_menu(self):
        if self.attach_menu is not None:
            return self.attach_menu.menus.model_slug(self.attach_menu.title)
        return None

    def to_menunode(self):
        yield MenuNode(
            title=self.title,
            url=self.url,
            unique_id=self.unique_id,
            parent_id=self.target_id,
        )
        attached = self.get_attach_menu()
        if attached is not None:
            for node in attached.menus.get_nodes(parent_node=self.target_id):
                yield node




class MenuNode(object):
    __slots__ = ('title', 'url', 'unique_id', 'parent_id', 'depth', 'ancestors',
                 'descendants', 'extra_context', '_object', 'object')

    def __init__(self, title, url, unique_id, parent_id=None, **kwargs):
        self.title = title
        self.url = url
        self.unique_id = unique_id
        self.parent_id = parent_id
        if self.unique_id == self.parent_id:
            raise ImproperlyConfigured("Nodes cannot be their own parent!")
        self.depth = 0
        self.ancestors = []
        self.descendants = []
        self.extra_context = kwargs or {}
        self._object = None

    def get_absolute_url(self):
        """Familiar API ..."""
        return self.url

    def _get_object(self):
        if self._object is None:
            if 'content_type' not in self.extra_context:
                logger.warning('Attempted to access `MenuNode.object` without'
                               'providing `content_type`')
                return self._object
            if 'object_id' not in self.extra_context:
                logger.warning('Attempted to access `MenuNode.object` without'
                               'providing `object_id`')
                return self._object

            model = ContentType.objects.get_for_id(
                self.extra_context['content_type'])
            try:
                self._object = model.model_class()._default_manager.get(
                    pk=self.extra_context['object_id'])
            except ObjectDoesNotExist as e:
                return self._object

        return self._object

    def _set_object(self, obj):
        """
        Forcibly set the object.
        """
        self._object = obj

    object = property(_get_object, _set_object)

    def __unicode__(self):
        return self.title

    def __repr__(self):
        return ('<menuhin.models.MenuNode: {obj.depth} ({obj.unique_id}, '
                '{obj.parent_id}, {obj.title})>').format(obj=self)

    def __nonzero__(self):
        """
        Allows for doing "If Node A:" for truthiness

        :return: :data:`True` or :data:`False`
        """
        return len(self.title) > 0 and len(self.url) > 0 and len(self.unique_id) > 0

    def __eq__(self, other):
        return other.unique_id == self.unique_id

    def __ne__(self, other):
        return other.unique_id != self.unique_id

    # def __getattr__(self, attr):
    #     """
    #     Anything not in `__slots__` should be pulled out of the extra context
    #     dictionary.
    #
    #     :param attr: attribute name to look up.
    #     :return: the value stored in the `extra_context` dictionary.
    #     """
    #     return self.extra_context.get(attr, None)
    #
    # __getitem__ = __getattr__
    #
    # def __setattr__(self, key, value):
    #     """
    #     If the `key` is one which we know about (ie: is in `__slots__`) then
    #     apply it directly, otherwise push it into the `extra_context`
    #
    #     :param key: the attribute to try and set.
    #     :param value: the value to apply to either the object or the dictionary.
    #     :return: :data:`None`
    #     """
    #     if hasattr(self, key):
    #         object.__setattr__(self, key, value)
    #     else:
    #         self.extra_context.update(key=value)
    #
    # __setitem__ = __setattr__

    def __contains__(self, item):
        """
        Allows for doing "Is Node A in Node B?" without being clear about
        where in the family it is.

        :param item: The item to find in the ancestors or descendants list.
        :return: :data:`True` or :data:`False`
        """
        return item in self.ancestors or item in self.descendants


class HeirarchyCalculator(object):
    __slots__ = ('start',)

    def __init__(self, start=0):
        self.start = start

    def __call__(self, this_node, other_nodes, request, **kwargs):
        ancestors = []
        parent = this_node.unique_id
        while parent is not None:
            if parent not in other_nodes:
                parent = None
            else:
                next_parent = other_nodes[parent]
                ancestors.append(next_parent)
                parent = next_parent.parent_id
        this_node.ancestors = ancestors[::-1]
        # get rid of self.
        this_node.ancestors.pop()

        this_node.depth = len(this_node.ancestors) + self.start

        for node in this_node.ancestors:
            node.descendants.append(this_node)

        return this_node


class ActiveCalculator(object):
    __slots__ = ('compare_querystrings',)

    def __init__(self, compare_querystrings=True):
        self.compare_querystrings = True

    def __call__(self, this_node, other_nodes, request, **kwargs):
        try:
            req_url = request.get_full_path()
        except AttributeError as e:
            # request was None, so stop processing ...
            return this_node

        node_url = this_node.url
        if self.compare_querystrings:
            split_req_url = urlparse(req_url)
            split_node_url = urlparse(node_url)
            # the querys should be the same, in any order, hopefully
            node_query = QueryDict(split_node_url.query)
            req_query = QueryDict(split_req_url.query)

            is_active = (split_req_url.path == split_node_url.path
                         and node_query == req_query)
        else:
            is_active = req_url == node_url
        if is_active is True:
            this_node.extra_context['is_active'] = is_active
            # highlight any ancestors
            for node in this_node.ancestors:
                node.extra_context['is_ancestor'] = is_active
        return this_node
