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
        return self.model().get_nodes(parent_node=parent_node)

    def get_processed_nodes(self, request, parent_node=None):
        nodes = self.get_nodes(parent_node=parent_node)
        if not self.model.processors:
            yield nodes

        # ugh :(
        tree = {}
        nodes = list(nodes)
        for element in nodes:
            tree[element.unique_id] = element

        for node in nodes:
            for processor in self.model.processors:
                yield processor(this_node=node, other_nodes=tree,
                                request=request)
    #
    # def build_tree(self):
    #     """
    #     internal nodes representation!
    #     basically:
    #     {
    #       'unique_id': node,
    #       'unique_id': node,
    #     }
    #     """
    #     assert self._meta.managed is False, "Stop trying to call this on " \
    #                                         "managed models"
    #     self.tree = {}
    #     for element in self.nodes:
    #         self.tree[element.unique_id] = element
    #     return self
    #
    # def build_nodes(self):
    #     self.nodes = list(self.get_nodes())
    #     return self
    #
    # def apply_safe_processors(self):
    #     # process nodes
    #     # This might be expensive, so use sparingly.
    #     if self.processors:
    #         for node in self.nodes:
    #             for processor in self.processors:
    #                 node = processor(this_node=node,
    #                                  other_nodes=self.tree)
    #     return self
    #
    # def calculate_tree(self):
    #     self.tree = {}
    #     for element in self.nodes:
    #         self.tree[element.unique_id] = element
    #     return self
    #
    # def build(self, request=None):
    #     self.build_nodes().build_tree().apply_safe_processors()
    #     return self
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
