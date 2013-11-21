# -*- coding: utf-8 -*-
from django.conf import settings
from django.db.models import OneToOneField
from django.template.defaultfilters import slugify
from django.utils import six
from django.utils.importlib import import_module
from helpfulfields.querysets import ChangeTrackingQuerySet, PublishingQuerySet


class MenuQuerySet(ChangeTrackingQuerySet, PublishingQuerySet):
    pass


class CustomMenuItemQuerySet(ChangeTrackingQuerySet, PublishingQuerySet):
    pass


class MenuFinder(object):
    def __get__(self, instance, owner):
        self.model = owner
        return self

    def _all_models_oldstyle(self, model):  # pragma: no cover
        """
        Discovery of menus via unmanaged models
        """
        objs = [rel for rel in model._meta.get_all_related_objects()
                if isinstance(rel.field, OneToOneField)
                and issubclass(rel.field.model, model)
                and rel.field.model._meta.managed is False]
        for obj in objs:
            yield obj
            for subobj in self._all_models(model=obj.field.model):
                yield subobj

    def _do_imports(self):
        """ :( """
        count = 0
        for app in settings.INSTALLED_APPS:
            module_path = '{0}.menus'.format(app)
            try:
                module = import_module(module_path)
                count += 1
            except ImportError as e:
                pass
        # did we find anything?
        return count > 0

    def _all_models(self, model):
        """
        Discovery of menus via proxy models
        """
        objs = [rel for rel in model.__subclasses__()
                if hasattr(rel, '_meta') and rel._meta.proxy is True]
        for obj in objs:
            yield obj
            for subobj in self._all_models(model=obj):
                yield subobj

    def models(self):
        """
        Returns all possible menu model classes (not instances)
        """
        self._do_imports()
        for model in self._all_models(model=self.model):
            yield model

    def model_slugs(self, lookups):
        for model in self.models():
            if slugify(model._meta.verbose_name_plural)[:50] in lookups:
                yield model

    def model_slug(self, lookup):
        return list(self.model_slugs((lookup,)))[0]

    def get_or_create(self, site=None):
        """
        Creates all of the discovered menus ...
        """
        if site is None:
            site = self.model._meta.get_field_by_name('site')[0].default()
        for model in self.models():
            kwargs = {
                'title': slugify(model._meta.verbose_name_plural)[:50].strip(),
                'site': site,
            }
            # don't include the changeable display title in the get call.
            try:
                yield self.model.objects.get(**kwargs)
            except self.model.DoesNotExist:
                kwargs.update(is_published=False,
                              display_title=model._meta.verbose_name_plural[:50].strip())  # noqa
                yield self.model.objects.create(**kwargs)

    def get_nodes(self, request, parent_node=None):
        pk = slugify(self.model._meta.verbose_name_plural)[:50]
        instance = self.model(pk=pk)
        custom_menu_items = dict((x.target_id, x)
                                 for x in instance.menu_items.all())
        changing_nodes = len(custom_menu_items) > 0
        for node in instance.get_nodes(request=request,
                                       parent_node=parent_node):
            # if it's in our custom menu items, yield it how it's supposed to
            # be done.
            if changing_nodes and node.unique_id in custom_menu_items:
                obj = custom_menu_items[node.unique_id]
                newnodes = obj.to_menunode(request)
                # put our new nodes first.
                if obj.position == obj.POSITIONS.above:
                    for newnode in newnodes:
                        yield newnode
                    yield node
                # put our new nodes last
                elif obj.position == obj.POSITIONS.below:
                    yield node
                    for newnode in newnodes:
                        yield newnode
                # replace the existing nodes
                elif obj.position == obj.POSITIONS.replacing:
                    for newnode in newnodes:
                        yield newnode
                # dunno; wtf did you put in the position field?
                else:  # pragma: no cover
                    yield node
            else:
                yield node

    def get_processed_nodes(self, request, parent_node=None):
        nodes = self.get_nodes(request=request, parent_node=parent_node)
        if not self.model.processors:
            for node in nodes:
                yield node

        # ugh :(
        tree = {}
        nodes_to_use = list(nodes)
        for element in nodes_to_use:
            tree[element.unique_id] = element

        for node in nodes_to_use:
            for processor in self.model.processors:
                node = processor(this_node=node, other_nodes=tree,
                                 request=request)
            yield node
        del tree, nodes

    def all(self, request, parent_node=None):
        return self.get_processed_nodes(request, parent_node=None)

    def filter(self, request, parent_node=None, min_depth=None,
               max_depth=None):
        nodes = self.get_processed_nodes(request, parent_node=None)
        # nothing was given ... this is just doing .all()
        if min_depth is None and max_depth is None:
            return nodes

        # if only one parameter was given, figure out the correct values.
        if min_depth is None and max_depth:
            min_depth = 0
        elif max_depth is None and min_depth:
            max_depth = float("inf")
        return (x for x in nodes
                if x.depth >= min_depth and x.depth <= max_depth)
