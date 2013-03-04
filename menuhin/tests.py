# -*- coding: utf-8 -*-
from django.db import IntegrityError, router
from django.db.models import Q
from django.db.models.deletion import Collector
from django.test import TestCase
from menuhin.models import Menu, Node, Hierarchy




class MenuModelsTestCase(TestCase):

    def test_no_menu_duplicates(self):
        Menu.objects.create(title='default1')
        Menu.objects.create(title='not_default')
        self.assertRaises(IntegrityError, lambda: Menu.objects.create(title='default1'))

    def test_menu_names(self):
        # TODO: wtf, why do these all work?
        Menu.objects.create(title='this-is-ok')
        Menu.objects.create(title='this_also_ok')
        Menu.objects.create(title='this is not ok')
        Menu.objects.create(title='and-nor-is-this?')

    def _adjacency_values_for_node(self, obj):
        return Hierarchy.objects.filter(
            Q(ancestor=obj) | Q(descendant=obj)
        ).values_list('ancestor', 'descendant', 'lvl')

    def _yield_some_nodes(self, menu, num):
        results = []
        for x in range(1, num+1):
            results.append(Node.objects.create(menu=menu, title='Node %d' % x))
        return results


    def test_getting_root_nodes(self):
        """ Get the root nodes for a specific menu.

        In this instance, we should get the following results:
            * Node 1
            * Node 4
            * Node 5

        Given a menu which should look something like:
            * Node 1
                * Node 2
                    * Node 3
            * Node 4
            * Node 5
                * Node 6
        """
        with self.assertNumQueries(8):
            menu = Menu.objects.create(title='default')
            nodes = self._yield_some_nodes(menu, 6)

        with self.assertNumQueries(23):
            # roots first
            Node.objects.insert_node(nodes[0])
            Node.objects.insert_node(nodes[3])
            Node.objects.insert_node(nodes[4])
            # sets up Node 2
            Node.objects.insert_node(nodes[1], parent=nodes[0])
            # sets up Node 3
            Node.objects.insert_node(nodes[2], parent=nodes[1])
            # sets up Node 6
            Node.objects.insert_node(nodes[5], parent=nodes[4])

        # find roots in this menu
        with self.assertNumQueries(1):
            found_roots = [(x.get_title(), x.pk) for x in Node.objects.roots(menu=menu)]
            expected_roots = [(u'Node 1', 1), (u'Node 4', 4), (u'Node 5', 5)]
            self.assertEqual(expected_roots, found_roots)


    def test_items_to_delete(self):
        """
        Given a menu which should look something like:
            * Node 1
                * Node 2
                    * Node 3
                    * Node 5
                        * Node 6
            * Node 4
        Find all things relating to Node 2 and delete them.
        """
        with self.assertNumQueries(8):
            menu = Menu.objects.create(title='default')
            nodes = self._yield_some_nodes(menu, 6)
        with self.assertNumQueries(36):
            # roots first
            Node.objects.insert_node(nodes[0])
            Node.objects.insert_node(nodes[3])
            # sets up Node 2
            Node.objects.insert_node(nodes[1], parent=nodes[0])
            # sets up Node 3
            Node.objects.insert_node(nodes[2], parent=nodes[1])
            # sets up Node 5
            Node.objects.insert_node(nodes[4], parent=nodes[2])
            # sets up Node 6
            Node.objects.insert_node(nodes[5], parent=nodes[4])

        with self.assertNumQueries(1):
            items_to_delete = Node.objects._relations_to_delete(nodes[1])
            ids = list(items_to_delete.values_list('pk', flat=True))
            ids.sort()

        # tests equivalent of nodes[1].delete()
        with self.assertNumQueries(2):
            using = router.db_for_write(nodes[1].__class__, instance=nodes[1])
            collector = Collector(using=using)
            collector.collect([nodes[1]])
            other_ids = [x.pk for x in collector.data[Hierarchy]]
            other_ids.sort()
            self.assertEqual(ids, other_ids)

        # number of queries required for deleting nodes[1], in actuality.
        with self.assertNumQueries(5):
            nodes[1].delete()

        # check root nodes are fine.
        with self.assertNumQueries(1):
            found_roots = [(x.get_title(), x.pk) for x in Node.objects.roots(menu=menu)]
            expected_roots = [(u'Node 1', 1), (u'Node 4', 4)]
            self.assertEqual(expected_roots, found_roots)

    def test_moving_item(self):
        """
        Given a menu which should look something like:
            * Node 1
                * Node 2
                    * Node 3
                    * Node 5
                        * Node 6
            * Node 4
        Move Node 4 under Node 2
            * Node 1
                * Node 2
                    * Node 3
                    * Node 5
                        * Node 6
                    * Node 4

        """
        with self.assertNumQueries(8):
            menu = Menu.objects.create(title='default')
            nodes = self._yield_some_nodes(menu, 6)
        with self.assertNumQueries(36):
            # roots first
            Node.objects.insert_node(nodes[0])
            Node.objects.insert_node(nodes[3])
            # sets up Node 2
            Node.objects.insert_node(nodes[1], parent=nodes[0])
            # sets up Node 3
            Node.objects.insert_node(nodes[2], parent=nodes[1])
            # sets up Node 5
            Node.objects.insert_node(nodes[4], parent=nodes[2])
            # sets up Node 6
            Node.objects.insert_node(nodes[5], parent=nodes[4])
        with self.assertNumQueries(11):
            Node.objects.move_node(nodes[3], nodes[1])
        with self.assertNumQueries(1):
            found_roots = [(x.get_title(), x.pk) for x in Node.objects.roots(menu=menu)]
            expected_roots = [(u'Node 1', 1)]
            self.assertEqual(expected_roots, found_roots)

        nodes = Node.objects.filter(menu=menu)
        import pdb; pdb.set_trace()
        print nodes

    def taest_insertion_manager(self):
        """

        Menu should look something like:
            * Node 1
                * Node 2
                    * Node 3
            * Node 4
        """
#        from django.db import connection
#        connection.use_debug_cursor = True
        menu = Menu.objects.create(title='default')
        # a root node.
        with self.assertNumQueries(4):
            nodes = self._yield_some_nodes(menu, 4)

        with self.assertNumQueries(3):
            Node.objects.insert_node(nodes[0])
            found_adjacencies = list(self._adjacency_values_for_node(nodes[0]))
            expected_adjacencies = [(1, 1, 0), (None, 1, 1)]
            self.assertEqual(expected_adjacencies, found_adjacencies)

        # this should be a child of nodes[0]
        with self.assertNumQueries(6):
            nodes[1] = Node.objects.create(menu=menu, title='Node B')
            Node.objects.insert_node(nodes[1], parent=nodes[0])
            found_adjacencies = list(self._adjacency_values_for_node(nodes[1]))
            expected_adjacencies = [(2, 2, 0), (1, 2, 1), (None, 2, 2)]
            self.assertEqual(expected_adjacencies, found_adjacencies)

        # this should be a child of nodes[1]
        with self.assertNumQueries(8):
            nodes[2] = Node.objects.create(menu=menu, title='Node C')
            Node.objects.insert_node(nodes[2], parent=nodes[1])
            found_adjacencies = list(self._adjacency_values_for_node(nodes[2]))
            expected_adjacencies = [(3, 3, 0), (1, 3, 2), (None, 3, 3), (2, 3, 1)]
            self.assertEqual(expected_adjacencies, found_adjacencies)

        # another root node.
        with self.assertNumQueries(3):
            nodes[3] = Node.objects.create(menu=menu, title='Node D')
            Node.objects.insert_node(nodes[3])
            found_adjacencies = list(self._adjacency_values_for_node(nodes[3]))
            expected_adjacencies = [(4, 4, 0), (None, 4, 1)]
            self.assertEqual(expected_adjacencies, found_adjacencies)




#
#
#    def taest_menu_creation_manually(self):
#        # see script here
#        # http://bobobobo.wordpress.com/2010/12/22/closure-table-part-deux-nodes-and-adjacencies-a-tree-in-mysql/
#        menu = Menu.objects.create(title='default')
#
#
#
#        nodes[0] = Node.objects.create(menu=menu, title='Node A')
#        nodes[1] = Node.objects.create(menu=menu, title='Node B')
#        nodes[2] = Node.objects.create(menu=menu, title='Node C')
#        nodes[3] = Node.objects.create(menu=menu, title='Node D')
#        node4 = Node.objects.create(menu=menu, title='Node E')
#        node5 = Node.objects.create(menu=menu, title='Node F')
#        node6 = Node.objects.create(menu=menu, title='Node G')
#
#
#        Hierarchy.objects.create(ancestor=nodes[0], descendant=nodes[0], lvl=0)
#        Hierarchy.objects.create(ancestor=None, descendant=nodes[0], lvl=1)
#
#        Hierarchy.objects.create(ancestor=nodes[1], descendant=nodes[1], lvl=0)
#        Hierarchy.objects.create(ancestor=nodes[0], descendant=nodes[1], lvl=1)
#
#        Hierarchy.objects.create(ancestor=None, descendant=nodes[1], lvl=2)
#
#        Hierarchy.objects.create(ancestor=nodes[2], descendant=nodes[2], lvl=0)
#        Hierarchy.objects.create(ancestor=None, descendant=nodes[2], lvl=1)
#
#        Hierarchy.objects.create(ancestor=nodes[3], descendant=nodes[3], lvl=0)
#        Hierarchy.objects.create(ancestor=nodes[1], descendant=nodes[3], lvl=1)
#        Hierarchy.objects.create(ancestor=nodes[0], descendant=nodes[3], lvl=2)
#        Hierarchy.objects.create(ancestor=None, descendant=nodes[3], lvl=3)
#
#
#        Hierarchy.objects.create(ancestor=node4, descendant=node4, lvl=0)
#        Hierarchy.objects.create(ancestor=nodes[2], descendant=node4, lvl=1)
#        Hierarchy.objects.create(ancestor=None, descendant=node4, lvl=2)
#
#        Hierarchy.objects.create(ancestor=node5, descendant=node5, lvl=0)
#        Hierarchy.objects.create(ancestor=nodes[0], descendant=node5, lvl=1)
#        Hierarchy.objects.create(ancestor=None, descendant=node5, lvl=2)
#
#        Hierarchy.objects.create(ancestor=node6, descendant=node6, lvl=0)
#        Hierarchy.objects.create(ancestor=nodes[0], descendant=node6, lvl=1)
#        Hierarchy.objects.create(ancestor=None, descendant=node6, lvl=2)
#
#        res1 = list(Hierarchy.objects.filter(ancestor=nodes[0]).values_list('descendant', flat=True))
#
#        self.assertEqual([1, 2, 4, 6, 7], res1)
#
#        res2 = list(Hierarchy.objects.filter(descendant=node6).exclude(ancestor=node6).values_list('ancestor', flat=True))
#        self.assertEqual([1, None], res2)
#
#        # count descendants
#        subquery = Hierarchy.objects.filter(ancestor=nodes[0]).values_list('descendant')
#        found = Hierarchy.objects.filter(ancestor__in=subquery).exclude(descendant=nodes[0])
#        self.assertEqual(9, found.count())
#
#        # count descendants via HierarchyManager
#        self.assertEqual(9, Hierarchy.objects.descendant_count(nodes[0]))
#        self.assertEqual(2, Hierarchy.objects.descendant_count(nodes[2]))
#        self.assertEqual(0, Hierarchy.objects.descendant_count(nodes[3]))
#
#        # show descendants via HierarchyManager
#        self.assertEqual(
#            [2, 4, 6, 7, 2, 4, 4, 6, 7],
#            list(Hierarchy.objects.descendants(nodes[0]).values_list('descendant', flat=True))
#        )
