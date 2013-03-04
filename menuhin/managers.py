# -*- coding: utf-8 -*-
from django.db import transaction
from django.db.models import Manager, Q


class NodeManager(Manager):
    def ancestors(self, obj):
        return []

    def descendents(self, obj):
        return []

    def children(self, obj):
        return []

    def parents(self, obj):
        return []

    def move(self, from_, to_):
        return []

    def insert_node(self, obj, parent=None):
        from menuhin.models import Hierarchy
        with transaction.commit_on_success():
            if parent is not None:
                relationships = Hierarchy.objects.filter(descendant=parent)
                z = [Hierarchy.objects.create(ancestor=relation.ancestor,
                    descendant=obj, lvl=relation.next_lvl()) for relation in relationships]
            me = Hierarchy.objects.create(ancestor=obj, descendant=obj, lvl=0)
            if parent is None:
                Hierarchy.objects.create(ancestor=None, descendant=obj, lvl=1)
            return True
        return False

    def roots(self, menu):
        # TODO: refactor to use adjacencies field.
        from menuhin.models import Hierarchy
        return self.get_query_set().filter(pk__in=Hierarchy.objects.filter(ancestor=None, lvl=1)
            .values_list('descendant'))

    def _relations_to_delete(self, obj):
        from menuhin.models import Hierarchy
        return Hierarchy.objects.filter(descendant=obj).exclude(ancestor=obj) | Hierarchy.objects.filter(ancestor=obj)

    def delete_node(self, obj):
        from menuhin.models import Hierarchy
        with transaction.commit_on_success():
            parents = Hierarchy.objects.filter(descendant=obj).exclude(ancestor=obj)
            children = Hierarchy.objects.filter(ancestor=obj)
            parents.delete()
            children.delete()
            return True
        return False
#            all_of_us = Hierarchy.objects.filter(
#                Q(ancestor__in=parents.values_list('ancestor')) |
#                Q(descendant__in=children.values_list('descendant'))
#            )
#        return all_of_us

    def move_node(self, obj, new_parent):
        if self.delete_node(obj) == True:
            return self.insert_node(obj, parent=new_parent)
        return False


class HierarchyManager(Manager):
    def descendants(self, obj):
        """
        Generates a query like:
        SELECT *
        FROM   `closure_table`
        WHERE  `ancestor` IN (SELECT a.`ancestor`
                          FROM   `closure_table`
                          WHERE  `descendant` = 1
                                 AND `ancestor` != 1)
               AND `descendant` IN (SELECT `descendant`
                             FROM   `closure_table`
                             WHERE  `ancestor` = 1)
        """
        parents = (self
                   .filter(descendant=obj)
                   .exclude(ancestor=obj)
                   .values_list('ancestor'))
        children = (self
                    .filter(ancestor=obj)
                    .values_list('descendant'))
        all_of_us = self.filter(ancestor__in=parents, descendant__in=children)
        return all_of_us

    def descendant_count(self, obj):
        """
        Boils down to a query like:
        SELECT count(*)
        FROM   `closure_table`
        WHERE  `ancestor` IN (SELECT `descendant`
                          FROM   `closure_table`
                          WHERE  `ancestor` = 1)
               AND NOT descendant = 1;
        """
        subquery = self.model.objects.filter(ancestor=obj).values_list('descendant')
        found = self.model.objects.filter(ancestor__in=subquery).exclude(descendant=obj)
        return found.count()

    def add(self, obj, target=None):
        try:
            target_id = target.pk
        except AttributeError:
            # no object passed in.
            target_id = target

        obj.save()

