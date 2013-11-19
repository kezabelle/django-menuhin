# -*- coding: utf-8 -*-
from django.db.models import OneToOneField
from django.template.defaultfilters import slugify
from helpfulfields.querysets import ChangeTrackingQuerySet, PublishingQuerySet


class MenuQuerySet(ChangeTrackingQuerySet, PublishingQuerySet):
    pass


class CustomMenuItemQuerySet(ChangeTrackingQuerySet, PublishingQuerySet):
    pass


class MenuFinder(object):
    def __get__(self, instance, owner):
        self.model = owner
        return self

    def _all_models_oldstyle(self, model):
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
        for model in self._all_models(model=self.model):
            yield model

    def model_slugs(self, lookups):
        for model in self.models():
            if slugify(model._meta.verbose_name)[:50] in lookups:
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
            arguments = {
                'title': slugify(model._meta.verbose_name)[:50],
                'display_title': model._meta.verbose_name[:50],
                'site': site,
            }
            fixed_arguments = dict((k, v) for k, v in arguments.iteritems()
                                   if v)
            yield self.model.objects.get_or_create(**fixed_arguments)


    def get_nodes(self, parent_node=None):
        pk = slugify(self.model._meta.verbose_name)[:50]
        instance = self.model(pk=pk)
        print pk
        custom_menu_items = dict((x.target_id, x)
                                 for x in instance.menu_items.all())
        changing_nodes = len(custom_menu_items) > 0
        for node in instance.get_nodes(parent_node=parent_node):
            # if it's in our custom menu items, yield it how it's supposed to
            # be done.
            if changing_nodes and node.unique_id in custom_menu_items:
                obj = custom_menu_items[node.unique_id]
                newnode = obj.to_menunode()
                if obj.position == obj.POSITIONS.above:
                    yield newnode
                    yield node
                elif obj.position == obj.POSITIONS.below:
                    yield node
                    yield newnode
                elif obj.position == obj.POSITIONS.replacing:
                    yield newnode
                else:
                    yield node
            else:
                yield node

    def get_processed_nodes(self, request, parent_node=None):
        nodes = self.get_nodes(parent_node=parent_node)
        if not self.model.processors:
            yield nodes

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

    def filter(self, request, parent_node=None, min_depth=None, max_depth=None):
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
    #

    # def all(self, request):
    #     is_active = ActiveCalculator(compare_querystrings=True)
    #     return (is_active(this_node=x, request=request) for x in self.nodes)
    #
    # def filter_depth(self, request, from_depth, to_depth):
    #     return (x for x in self.all(request)
    #             if x.depth >= from_depth and x.depth <=to_depth)
    #
    # def filter_active(self, request):
    #     return (x for x in self.all(request)
    #             if 'is_active' in x.extra_context
    #             and x.extra_context['is_active'])
