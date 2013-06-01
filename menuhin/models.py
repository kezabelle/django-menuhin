# -*- coding: utf-8 -*-
from datetime import datetime
import logging
from urlparse import urlparse
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db.models import SlugField, ForeignKey, CharField
from django.http import QueryDict
from django.utils.importlib import import_module
from model_utils.managers import PassThroughManager
from helpfulfields.models import ChangeTracking, Publishing
from menuhin.settings import MENUHIN_MENU_HANDLERS, NODE_CACHE_KEY_PREFIX, TREE_CACHE_KEY_PREFIX
from menuhin.text import (menu_v, menu_vp, title_label, title_help,
                          display_title_label, display_title_help)
from menuhin.querysets import MenuQuerySet

# see the following URLs:
# http://bobobobo.wordpress.com/2010/12/22/closure-table-part-deux-nodes-and-adjacencies-a-tree-in-mysql/
# http://dirtsimple.org/2010/11/simplest-way-to-do-tree-based-queries.html
# https://gist.github.com/1380975


logger = logging.getLogger(__name__)


class Menu(ChangeTracking, Publishing):
    site = ForeignKey(Site, default=Site.objects.get_current)
    title = SlugField(max_length=50, primary_key=True,
                      verbose_name=title_label, help_text=title_help)
    display_title = CharField(max_length=50, verbose_name=display_title_label,
                              help_text=display_title_help)

    objects = PassThroughManager.for_queryset_class(MenuQuerySet)()

    def __unicode__(self):
        """Reserved for admin/form usage."""
        return self.title

    class Meta:
        verbose_name = menu_v
        verbose_name_plural = menu_vp


class MenuNode(object):
    __slots__ = ('title', 'url', 'unique_id', 'parent_id',
                 'depth', 'ancestors', 'descendants', 'activity', 'extra_context')

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
        # activity is:
        # 0 - active
        # 1 - ancestor
        # 2 - descendant
        self.activity = [False, False, False]
        self.extra_context = kwargs or {}

    def get_absolute_url(self):
        """Familiar API ..."""
        return self.url

    def __unicode__(self):
        return self.title

    def __repr__(self):
        return '<menuhin.models.MenuNode (%s, %s)>' % (self.unique_id, self.parent_id)

class AncestryCalculator(object):
    __slots__ = ()

    def __call__(self, this_node, other_nodes, **kwargs):
        ancestors = []
        parent = this_node.unique_id
        while parent is not None:
            next_parent = other_nodes[parent]
            ancestors.append(next_parent)
            parent = next_parent.parent_id

        this_node.ancestors = ancestors[::-1]
        return this_node


class DescendantCalculator(object):
    __slots__ = ()

    def __call__(self, this_node, other_nodes, **kwargs):
        this_node.descendants = this_node.ancestors[::-1]
        return this_node


class DepthCalculator(object):
    __slots__ = ('start',)

    def __init__(self, start=0):
        self.start = start

    def __call__(self, this_node, other_nodes, **kwargs):
        this_node.depth = len(this_node.ancestors) + self.start
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
        if is_active and not this_node.activity[0]:
            this_node.activity[0] = is_active
            # highlight any ancestors
            for node in this_node.ancestors:
                node.activity[1] = True
        return this_node


class MenuCollection(object):
    processors = [
        AncestryCalculator(),
        DescendantCalculator(),
        DepthCalculator(),
        ActiveCalculator(compare_querystrings=True),
    ]
    name = None
    verbose_name = None

    def get_name(self):
        return self.name

    def get_verbose_name(self):
        return self.verbose_name

    def get_menu_key(self):
        return self.name

    def get_nodes(self, *args, **kwargs):
        raise NotImplementedError('Subclasses should provide this implementation')

    #
    # def nodes_from_cache(self):
    #     key = NODE_CACHE_KEY_PREFIX % self.get_name()
    #     return cache.get(key, None)
    #
    # def nodes_to_cache(self, nodelist):
    #     key = NODE_CACHE_KEY_PREFIX % self.get_name()
    #     return cache.set(key, nodelist)
    #
    # def tree_from_cache(self):
    #     key = TREE_CACHE_KEY_PREFIX % self.get_name()
    #     return cache.get(key, None)
    #
    # def tree_to_cache(self, nodelist):
    #     key = TREE_CACHE_KEY_PREFIX % self.get_name()
    #     return cache.set(key, nodelist)

    def get_or_create(self, *args, **kwargs):
        """
        Look up a menu by the `name` associated with this MenuCollection;
        if it doesn't exist, create it.
        Note that the get() only uses the `name` and not the `verbose_name`
        so that the displayed name on a live site may be customised.
        Sort of like a guarnteed fixture.

        :return: Menu object
        """
        name = self.get_name()
        try:
            logger.debug('Getting menu from database')
            menu = Menu.objects.get(title=name)
        except Menu.DoesNotExist:
            logger.info('Menu not found in database, creating "%s" now' % name)
            menu = Menu.objects.create(title=name,
                display_title=self.get_verbose_name())
        return menu

    def __init__(self):
        self.nodes = None
        self.tree = None
        self.menu = self.get_or_create()

    def build_tree(self):
        # internal nodes representation!
        # basically:
        # {
        #   'unique_id': node,
        #   'unique_id': node,
        # }
        self.tree = {}
        for element in self.nodes:
            self.tree[element.unique_id] = element
        return self

    def build_nodes(self):
        self.nodes = list(self.get_nodes())
        return self

    def apply_processors(self):
        # process nodes
        # This might be expensive, so use sparingly.
        if self.processors:
            for node in self.nodes:
                for processor in self.processors:
                    node = processor(this_node=node,
                                     other_nodes=self.tree,
                                     request=self.request)
        return self

    def build(self, request=None):
        self.request = request
        self.build_nodes().build_tree().apply_processors()
        return self




class MenuHandler(object):
    __slots__ = ('menus', )

    def __init__(self):
        self.menus = {}

    def _load_menus(self):
        """
        Internal only. Copies the way middleware classes are loaded, using a
        global setting `MENUHIN_MENU_HANDLERS` which defaults to `None`

        :return: True or False
        :rtype: bool
        """
        # fail early.
        if MENUHIN_MENU_HANDLERS is None:
            if settings.DEBUG:
                raise ImproperlyConfigured("MENUHIN_MENU_HANDLERS not found in "
                "your settings module")
            return False

        # The following is stolen verbatim from Django's basehandler.
        # It basically serves to put the classes into a dictionary, letting useful
        # exception messages occur when stuff goes wrong.
        for menu_handler_path in MENUHIN_MENU_HANDLERS:
            try:
                dot = menu_handler_path.rindex('.')
            except ValueError:
                raise ImproperlyConfigured("%s isn't a valid path to a menu handler" % menu_handler_path)
            handler_module, handler_cls = menu_handler_path[:dot], menu_handler_path[dot+1:]
            try:
                mod = import_module(handler_module)
            except ImportError, e:
                raise ImproperlyConfigured('Error importing menu handler %s: "%s"' % (handler_module, e))
            try:
                final_menu_handler = getattr(mod, handler_cls)
            except AttributeError:
                raise ImproperlyConfigured('Menu handler module "%s" does not define a "%s" class' % (handler_module, handler_cls))

            the_menu = final_menu_handler()
            self.menus[the_menu.get_menu_key()] = the_menu
        return True

    def load_menus(self):
        """
        Public accessor function for populating the available menus.

        :return: This MenuHandler (self)
        :rtype: object
        """
#        cached_menu = cache.get('menuhin_menus', None)
#        # populate from cache
#        if cached_menu is not None:
#            self.menus = cached_menu
        self._load_menus()
#        # failed cache, create!
#        if cached_menu is None:
#            cache.set('menuhin_menus', self.menus)
        return self

    def reload_menus(self):
        """
        Public API method for clearing the cache and trying again.

        :return: This MenuHandler (self)
        :rtype: object
        """
#        cache.delete('menuhin_menus')
        self.menus = {}
        logging.info('reloading all menus in %r' % self)
        self._load_menus()
        return self

menu_handlers = MenuHandler()
