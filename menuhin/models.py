# -*- coding: utf-8 -*-
from datetime import datetime
import logging
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db.models import SlugField, ForeignKey, CharField
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

#MenuNode = namedtuple('MenuNode', ['title', 'url', 'unique_id', 'parent_id'])


class AncestryCalculator(object):
    def __call__(self, this_node, other_nodes):
#        import pdb; pdb.set_trace()
        ancestors = []
        parent = this_node.unique_id
        while parent is not None:
            next_parent = other_nodes[parent]
            ancestors.append(next_parent)
            parent = next_parent.parent_id

        this_node.ancestors = ancestors
        return this_node


class DescendantCalculator(object):
    def __call__(self, this_node, other_nodes):
        this_node.descendants = this_node.ancestors[::-1]
        return this_node

class DepthCalculator(object):
    def __init__(self, start=0):
        self.start = start

    def __call__(self, this_node, other_nodes):
        this_node.depth = len(this_node.ancestors) + self.start
        return this_node

class MenuCollection(object):
    processors = [
        AncestryCalculator(),
        DescendantCalculator(),
        DepthCalculator(),
    ]
    name = None
    verbose_name = None

    def get_name(self):
        return self.name

    def get_verbose_name(self):
        return self.verbose_name

    def get_menu_key(self):
        return self.name

    def nodes_from_cache(self):
        key = NODE_CACHE_KEY_PREFIX % self.get_name()
        return cache.get(key, None)

    def nodes_to_cache(self, nodelist):
        key = NODE_CACHE_KEY_PREFIX % self.get_name()
        return cache.set(key, nodelist)

    def tree_from_cache(self):
        key = TREE_CACHE_KEY_PREFIX % self.get_name()
        return cache.get(key, None)

    def tree_to_cache(self, nodelist):
        key = TREE_CACHE_KEY_PREFIX % self.get_name()
        return cache.set(key, nodelist)

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

    def build(self):
        # Try and get data from cache
        result_from_cache = self.nodes_from_cache()
        self.nodes = result_from_cache
        if result_from_cache is None:
            logger.info('Cache missed for nodes, getting from %r' % self.__class__)
            start = datetime.now()
            # may be a generator or something, and to do the node processing we
            # need it to be a fixed data structure.
            self.nodes = list(self.get_nodes())
            end = datetime.now()
            duration1 = (end - start)
            logging_parts = (duration1.microseconds, duration1.seconds)
            logger.debug('getting nodes took %d microseconds (%d seconds)' % logging_parts)

        # internal nodes representation!
        # basically:
        # {
        #   'unique_id': node,
        #   'unique_id': node,
        # }
        result_from_cache = self.tree_from_cache()
        self.tree = result_from_cache or {}
        if result_from_cache is None:
            logger.info('Cache missed for tree, getting from %r' % self.__class__)
            start = datetime.now()
            for element in self.nodes:
                self.tree[element.unique_id] = element
            end = datetime.now()
            duration2 = (end - start)
            logging_parts = (duration2.microseconds, duration2.seconds)
            logger.debug('Building tree took %s microseconds (%d seconds)' % logging_parts)

        # process nodes
        # This might be expensive, so use sparingly.
        if self.processors:
            logger.debug('%d processors to apply to each node' % len(self.processors))
            start = datetime.now()
            for node in self.nodes:
                for processor in self.processors:
                    node = processor(node, self.tree)
            end = datetime.now()
            duration3 = (end - start)
            logging_parts = (duration3.microseconds, duration3.seconds)
            logger.debug('Processing nodes took %s microseconds (%d seconds)' % logging_parts)

#        self.nodes = self.tree.values()
        # put data back into the cache now we have it all.
        self.nodes_to_cache(self.nodes)
        self.tree_to_cache(self.tree)

class RealTimeMenuCollection(MenuCollection):
    """
    If for some reason, you need to avoid the cache, you can use this. Yay!
    (Don't use this!)
    """
    def nodes_from_cache(self):
        """ Never looks in the cache """
        return None

    def nodes_to_cache(self, nodelist):
        """ Never caches anything """
        return None

    def tree_from_cache(self):
        """ Never looks in the cache """
        return None

    def tree_to_cache(self, nodelist):
        """ Never caches anything """
        return None

class MenuHandler(object):
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

#
#
#class Node(Model):
#    menu = ForeignKey(Menu)
#    title = CharField(max_length=255)
#    adjacencies = ManyToManyField('self', symmetrical=False, through='menuhin.Hierarchy')
#    url = AnyUrlField()
#    created = DateTimeField(auto_now_add=True)
#    modified = DateTimeField(auto_now=True)
#
##Node.objects.select_related('adjacencies').filter(descendants=F('ancestors__id')).count()
#    objects = NodeManager()
#
#    def __unicode__(self):
#        """Reserved for admin/form usage."""
#        return self.title
#
#    def get_title(self):
#        """API compatibility with django-CMS menus"""
#        return self.title
#    get_title.short_description = 'Title'
#    get_title.admin_order_field = 'title'
#
#    def get_menu_title(self):
#        """API compatibility with django-CMS menus"""
#        return self.get_title()
#
#    def get_absolute_url(self):
#        """Because it's what's expected"""
#        return self.url
#    get_absolute_url.short_description = 'Web address'
#    get_absolute_url.admin_order_field = 'url'
#
#    def pk_b36(self):
#        return int_to_base36(self.pk)
##
##    def save(self, *args, **kwargs):
##        super(Node, self).save(*args, **kwargs)
##        for node in Hierarchy.objects.filter(descendant=1)
##            Hierarchy.objects.create(node, 1, node.next_lvl)
##        Hierarchy.objects.create(node, node, 0)
#
#
#
#    class Meta:
#        verbose_name = menuitem_v
#        verbose_name_plural = menuitem_vp
#        db_table = 'nodes'
##        ordering = ['left_sibling']
#
#
#class Hierarchy(Model):
#    ancestor = ForeignKey(Node, null=True, related_name='ancestors')
#    descendant = ForeignKey(Node, related_name='descendants')
#    lvl = PositiveIntegerField(db_index=True)
#    created = DateTimeField(auto_now_add=True)
#    modified = DateTimeField(auto_now=True)
#
#    #objects = HierarchyManager()
#
#    def __unicode__(self):
#        return 'parent: "%s", child: "%s"' % (self.ancestor, self.descendant)
#
#    def next_lvl(self):
#        return sum([self.lvl, 1])
#
#    def previous_lvl(self):
#        return max(sum([self.lvl, -1]))
#
#    class Meta:
#        db_table = 'adjacencies'
#        unique_together = ['ancestor', 'descendant']
#        verbose_name = menurelation_v
#        verbose_name_plural = menurelation_vp
