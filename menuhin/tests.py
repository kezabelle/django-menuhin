# -*- coding: utf-8 -*-
from itertools import izip
from random import randrange
from django.db.models.loading import get_model
from django.contrib.contenttypes.models import ContentType
from django.utils.unittest import TestCase
from django.utils.functional import lazy
from django.test import TestCase as DjangoTestCase
from django.test.client import RequestFactory
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from model_mommy import mommy
from menuhin.models import (Menu, MenuNode, AncestryCalculator,
                            DescendantCalculator, DepthCalculator,
                            ActiveCalculator, HeirarchyCalculator)


class TestMenu(Menu):
    def get_nodes(self, parent_node=None):
        id_fmt = 'user_%s'
        previous_user = id_fmt % 0
        UserModel = get_model('auth', 'User')
        LazyContentType = lazy(
            lambda: ContentType.objects.get_for_model(UserModel).pk, int)
        for user in UserModel.objects.all():
            yield MenuNode(
                title=unicode(user),
                url='/test/%s' % slugify(unicode(user)),
                unique_id=id_fmt % user.pk,
                parent_id=previous_user,
                content_type=LazyContentType,
                object_id=user.pk,
            )
            previous_user = id_fmt % user.pk

    class Meta:
        managed = False
        proxy = True


class TestMenuChild(TestMenu):
    processors = (
        # AncestryCalculator(),
        # DescendantCalculator(),
        # DepthCalculator(),
        # HeirarchyCalculator(start=1),
        ActiveCalculator(compare_querystrings=True),
    )

    class Meta:
        managed = False
        proxy = True


class TestMenuGrandChild(TestMenuChild):
    processors = (
        HeirarchyCalculator(start=15),
        # ActiveCalculator(compare_querystrings=True),
    )

    class Meta:
        managed = False
        proxy = True


class TestMenuSecondChild(TestMenu):
    processors = (
        HeirarchyCalculator(start=1),
        ActiveCalculator(compare_querystrings=True),
    )

    class Meta:
        managed = False
        proxy = True


class MenuhinBaseTests(DjangoTestCase):
    def setUp(self):
        self.maxnum = randrange(10, 200)

    def test_creation(self):
        site = Site.objects.all()[0]
        title = "test"
        display_title = "my menu!"
        obj = Menu.objects.create(site=site, title=title,
                                  display_title=display_title)

        self.assertEqual(obj.site_id, site.pk)
        self.assertEqual(obj.title, title)
        self.assertEqual(obj.display_title, display_title)

    def test_descriptor(self):
        self.assertEqual(Menu, Menu.menus.model)
        self.assertEqual(TestMenu, TestMenu.menus.model)
        self.assertEqual(TestMenuGrandChild, TestMenuGrandChild.menus.model)

    def test_discovery(self):
        menus = Menu.menus.models()
        self.assertEqual(list(menus), [TestMenu,
                                       TestMenuChild,
                                       TestMenuGrandChild,
                                       TestMenuSecondChild])

    def test_discovery_child(self):
        menus = TestMenu.menus.models()
        self.assertEqual(list(menus), [TestMenuChild,
                                       TestMenuGrandChild,
                                       TestMenuSecondChild])

    def test_discovery_grandchild(self):
        menus = TestMenuGrandChild.menus.models()
        self.assertEqual(list(menus), [])

    def test_not_implemented(self):
        self.assertRaises(NotImplementedError, Menu().get_nodes)

    def test_inserted_models(self):
        with self.assertNumQueries(0):
            do_menus = Menu.menus.models()
        with self.assertNumQueries(1):
            self.assertEqual([], list(Menu.objects.all()))

        with self.assertNumQueries(16):
            for menu, created in Menu.menus.get_or_create():
                self.assertTrue(created)

        with self.assertNumQueries(4):
            for menu, created in Menu.menus.get_or_create():
                self.assertFalse(created)

        with self.assertNumQueries(3):
            for menu, created in TestMenu.menus.get_or_create():
                self.assertEqual(menu.__class__, TestMenu)
                self.assertTrue(isinstance(menu, TestMenu))
                self.assertTrue(isinstance(menu, Menu))
                self.assertFalse(created)

    def test_repr_sanity_etc(self):
        menus = Menu.menus.models()
        menu = next(menus)()
        for x in menu.get_nodes():
            repr = ('<menuhin.models.MenuNode: {obj.depth} ({obj.unique_id}, '
                    '{obj.parent_id}, {obj.title})>'.format(obj=x))
            self.assertEqual(repr, repr(x))
            self.assertEqual(x.title, unicode(x))

    def _building_and_menu(self, skip=1):
        users = list(mommy.make('auth.User') for x in xrange(1, self.maxnum))
        menus = Menu.menus.models()
        for x in xrange(0, skip):
            MenuKlass = next(menus)
        # with self.assertNumQueries(1):
        menu = MenuKlass.menus.get_nodes()
        return users, list(menu), MenuKlass

    def test_building(self):
        parent_user = 0
        for user, node in zip(*self._building_and_menu()[0:2]):
            self.assertEqual(unicode(user), node.title)
            self.assertEqual('user_%s' % user.pk, node.unique_id)
            self.assertEqual('/test/%s' % slugify(unicode(user)),
                             node.get_absolute_url())
            self.assertEqual('user_%s' % parent_user,
                             node.parent_id)
            self.assertEqual(0, node.depth)
            parent_user = user.pk

    def test_building_with_context_to_get_object(self):
        parent_user = 0
        bundled = izip(*self._building_and_menu()[0:2])

        # 1 to get the content type lazily, which is just because of the
        # way we've done the test; 1 to get the model class; 1 to get the
        # model instance itself.
        user, node = next(bundled)
        with self.assertNumQueries(3):
            self.assertEqual(user, node.object)

        for user, node in bundled:
            # 1 to get the content type lazily, which is just because of the
            # way we've done the test; 1 to get the model instance itself.
            with self.assertNumQueries(2):
                self.assertEqual(user, node.object)

    def test_calling_via_subclass_menufinder(self):
        menus = Menu.menus.models()
        MenuKlass = next(menus)
        with self.assertNumQueries(2):
            self.assertEqual(list(MenuKlass().get_nodes()),
                             list(MenuKlass.menus.get_nodes()))

    def test_equality(self):
        users, nodes = self._building_and_menu()[0:2]
        self.assertEqual(nodes[0], nodes[0])
        self.assertNotEqual(nodes[0], nodes[1])
        self.assertNotEqual(nodes[0], nodes[2])
        self.assertNotEqual(nodes[0], nodes[3])
        # and patching one to make it equal ...
        nodes[3].unique_id = nodes[0].unique_id
        self.assertEqual(nodes[0], nodes[3])

    def test_falsy(self):
        """
        if title/url/unique_id don't all have a length>0, they're not true.
        """
        node = MenuNode(title='', url='', unique_id='')
        self.assertFalse(True if node else False)

        node = MenuNode(title='a', url='', unique_id='')
        self.assertFalse(True if node else False)
        node = MenuNode(title='a', url='/', unique_id='')
        self.assertFalse(True if node else False)
        node = MenuNode(title='', url='/', unique_id='1')
        self.assertFalse(True if node else False)

        node = MenuNode(title='a', url='/', unique_id='1')
        self.assertTrue(True if node else False)

    def test_processors_is_active(self):
        users, menu, klass = self._building_and_menu(skip=2)
        self.assertEqual(TestMenuChild, klass)
        request = RequestFactory().get('/test/%s' % slugify(unicode(users[5])))
        wtf2 = list(klass.menus.get_processed_nodes(request=request))
        # sanity ...
        self.assertEqual(len(users), len(wtf2))

        # without the heirarchy calculator, only one thing can be active
        results = [x.url for x in wtf2
                   if x.extra_context.get('is_active', False)]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], request.get_full_path())

    def test_processors_heirarchy(self):
        users, menu, klass = self._building_and_menu(skip=3)
        self.assertEqual(TestMenuGrandChild, klass)
        request = RequestFactory().get('/')
        wtf2 = list(klass.menus.get_processed_nodes(request=request))
        # sanity ...
        self.assertEqual(len(users), len(wtf2))
        # depth from beginning should be the same ...
        for offset, node in enumerate(wtf2, start=klass.processors[0].start):
            self.assertEqual(offset, node.depth)

        first = wtf2[0]
        # no ancestors.
        self.assertEqual(0, len(first.ancestors))
        self.assertEqual([], first.ancestors)

        # all descendants
        first_descendants = [x for x in klass.menus.get_nodes()
                             if x != first]
        self.assertEqual(first.descendants, first_descendants)

        last = wtf2[-1]
        # no descendants.
        self.assertEqual(0, len(last.descendants))
        self.assertEqual([], last.descendants)

        # all ancestors
        last_ancestors = [x for x in klass.menus.get_nodes()
                          if x != last]
        self.assertEqual(last.ancestors, last_ancestors)

    def test_processors_mark_ancestors_active(self):
        users, menu, klass = self._building_and_menu(skip=4)
        self.assertEqual(TestMenuSecondChild, klass)
        user_offset = 7
        url = '/test/%s' % slugify(unicode(users[user_offset]))
        request = RequestFactory().get(url)
        wtf2 = list(klass.menus.get_processed_nodes(request=request))
        # sanity ...
        self.assertEqual(len(users), len(wtf2))

        active_urls = [x.url for x in wtf2
                       if x.extra_context.get('is_active', False)]
        self.assertEqual(1, len(active_urls))
        self.assertEqual(active_urls[0], url)

        ancestor_urls = [x.url for x in wtf2
                         if x.extra_context.get('is_ancestor', False)]
        expected_urls = ['/test/%s' % slugify(unicode(x))
                         for x in users[:user_offset]]
        self.assertEqual(user_offset, len(ancestor_urls))
        self.assertEqual(ancestor_urls, expected_urls)

        ancestor_objs = [x for x in wtf2
                         if x.extra_context.get('is_ancestor', False)]
        expected_objs = [MenuNode(title=unicode(x),
                                  url='/test/%s' % slugify(unicode(x)),
                                  unique_id='user_%s' % x.pk)
                         for x in users[:user_offset]]
        self.assertEqual(user_offset, len(ancestor_objs))
        self.assertEqual(ancestor_objs, expected_objs)
