# -*- coding: utf-8 -*-
from itertools import izip
from random import randrange
from django.db.models.loading import get_model
from django.core.exceptions import ImproperlyConfigured
from django.contrib.contenttypes.models import ContentType
from django.utils.unittest import TestCase
from django.utils.functional import lazy
from django.test import TestCase as DjangoTestCase
from django.test.client import RequestFactory
from django.contrib.sites.models import Site
from django.template import Template, RequestContext
from django.template.defaultfilters import slugify
from model_mommy import mommy
from menuhin import get_version, version, __version__, __version_info__
from menuhin.models import (Menu, MenuNode, ActiveCalculator,
                            HeirarchyCalculator)


class TestMenu(Menu):
    def get_data_for_nodes(self, thing):
        return {
            'title': unicode(thing),
            'url': '/test/%s' % slugify(unicode(thing)),
        }

    def get_nodes(self, request, parent_node=None):
        id_fmt = 'user_%s'
        previous_user = id_fmt % 0
        UserModel = get_model('auth', 'User')
        LazyContentType = lazy(
            lambda: ContentType.objects.get_for_model(UserModel).pk, int)
        for user in UserModel.objects.all():
            yield MenuNode(
                unique_id=id_fmt % user.pk,
                parent_id=previous_user,
                content_type=LazyContentType,
                object_id=user.pk,
                # allow subclasses to change things without breaking most of
                # my tests.
                **self.get_data_for_nodes(thing=user)
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

    def get_data_for_nodes(self, thing):
        return {
            'title': 'test-menu-child ... %s' % unicode(thing),
            'url': '/test-menu-child/%s' % slugify(unicode(thing)),
        }

    class Meta:
        managed = False
        proxy = True


class TestMenuGrandChild(TestMenuChild):
    processors = (
        HeirarchyCalculator(start=15),
        # ActiveCalculator(compare_querystrings=True),
    )

    def get_data_for_nodes(self, thing):
        return {
            'title': 'test-menu-grandchild ... %s' % unicode(thing),
            'url': '/grandchild/%s' % slugify(unicode(thing)),
        }

    class Meta:
        managed = False
        proxy = True


class TestMenuSecondChild(TestMenu):
    processors = (
        HeirarchyCalculator(start=1),
        ActiveCalculator(compare_querystrings=True),
    )

    def get_data_for_nodes(self, thing):
        return {
            'title': 'second-child ... %s' % unicode(thing),
            'url': '/second-child/%s' % slugify(unicode(thing)),
        }

    class Meta:
        managed = False
        proxy = True


class TestMenuThirdChild(TestMenu):
    processors = (
        HeirarchyCalculator(start=1),
        ActiveCalculator(compare_querystrings=True),
    )

    def get_nodes(self, request, parent_node=None):
        yield MenuNode(
            title="I am alone :(",
            url='/alone/',
            unique_id='alone_forever',
        )

    class Meta:
        managed = False
        proxy = True


class MenuNodeSanityTests(DjangoTestCase):
    def test_same_parent_same_unique(self):
        def generate_node():
            return MenuNode(title='a', url='b', unique_id='c', parent_id='c')
        self.assertRaises(ImproperlyConfigured, generate_node)

    def test_unicode_repr(self):
        node = MenuNode(title='a', url='b', unique_id='c')
        self.assertEqual(unicode(node), 'a')

    def test_repr(self):
        node = MenuNode(title='a', url='b', unique_id='c')
        self.assertEqual(repr(node),
                         '<menuhin.models.MenuNode: 0 (c, None, a)>')

    def test_object_only_providing_content_type(self):
        self.assertIsNone(MenuNode(title='a', url='b', unique_id='c',
                                   content_type=1).object)

    def test_object_only_providing_object_id(self):
        self.assertIsNone(MenuNode(title='a', url='b', unique_id='c',
                                   object_id=1).object)

    def test_object_is_none_if_stupid_ctpk(self):
        self.assertIsNone(MenuNode(title='a', url='b', unique_id='c',
                                   content_type=99999, object_id=99999).object)

    def test_setting_object(self):
        user = mommy.make('auth.User')
        node = MenuNode(title='a', url='b', unique_id='c', content_type=99999,
                        object_id=99999)
        node.object = user
        self.assertIsNotNone(node.object)
        self.assertEqual(node.object, user)

    def test_contains(self):
        node1 = MenuNode(title='a', url='b', unique_id='1c')
        node2 = MenuNode(title='a', url='b', unique_id='2c')
        node3 = MenuNode(title='a', url='b', unique_id='3c')
        node4 = MenuNode(title='a', url='b', unique_id='4c')
        node5 = MenuNode(title='a', url='b', unique_id='5c')
        node6 = MenuNode(title='a', url='b', unique_id='6c')
        node1.ancestors = [node2, node3]
        # make sure node 3 (an ancestor) is IN node 1
        self.assertIn(node3, node1)
        # node 4 is not in the ancestors list
        self.assertNotIn(node4, node1)
        # nor is node 2 in node 3
        self.assertNotIn(node2, node3)

        # make sure node 5 (a descendant) is IN node 4
        node4.descendants = [node5, node6]
        self.assertIn(node5, node4)
        # node 1 is not in the descendants for node 4
        self.assertNotIn(node1, node4)
        # and node 5 is not in node 6
        self.assertNotIn(node5, node6)


class ActiveCalculatorTests(TestCase):
    def test_attribute_error_on_bad_request(self):
        calc = ActiveCalculator()
        this_node = {'testing': 1}
        self.assertEqual(this_node, calc(this_node=this_node, other_nodes=(),
                                         request=()))

    def test_not_comparing_querystrings(self):
        node = MenuNode(title='a', url='/a/b/?c=d', unique_id='c')
        calc = ActiveCalculator(compare_querystrings=False)
        request = RequestFactory().get('/a/b/')
        # before running
        was_found_active = node.extra_context.get('is_active', False)
        self.assertFalse(was_found_active)
        node = calc(this_node=node, other_nodes=(), request=request)
        # after running
        was_found_active = node.extra_context.get('is_active', False)
        self.assertFalse(was_found_active)

    def test_matching_without_querystrings(self):
        node = MenuNode(title='a', url='/a/b/', unique_id='c')
        calc = ActiveCalculator(compare_querystrings=False)
        request = RequestFactory().get('/a/b/')
        node = calc(this_node=node, other_nodes=(), request=request)
        # after running again without a querystring
        was_found_active = node.extra_context.get('is_active', False)
        self.assertTrue(was_found_active)


class MenuhinBaseTests(DjangoTestCase):

    def test_versioning(self):
        """ make sure the versions stay consistent """
        for v in (version, __version__, __version_info__):
            self.assertEqual(get_version(), v)

    def test_creation(self):
        site = Site.objects.all()[0]
        title = "test"
        display_title = "my menu!"
        obj = Menu.objects.create(site=site, title=title,
                                  display_title=display_title)

        self.assertEqual(obj.site_id, site.pk)
        self.assertEqual(obj.title, title)
        self.assertEqual(unicode(obj), title)
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
                                       TestMenuSecondChild,
                                       TestMenuThirdChild])

    def test_discovery_child(self):
        menus = TestMenu.menus.models()
        self.assertEqual(list(menus), [TestMenuChild,
                                       TestMenuGrandChild,
                                       TestMenuSecondChild,
                                       TestMenuThirdChild])

    def test_discovery_grandchild(self):
        menus = TestMenuGrandChild.menus.models()
        self.assertEqual(list(menus), [])

    def test_not_implemented(self):
        self.assertRaises(NotImplementedError, Menu().get_nodes,
                          RequestFactory().get('/'))

    def test_inserted_models(self):
        with self.assertNumQueries(0):
            do_menus = Menu.menus.models()
        with self.assertNumQueries(1):
            self.assertEqual([], list(Menu.objects.all()))

        with self.assertNumQueries(20):
            for menu, created in Menu.menus.get_or_create():
                self.assertTrue(created)

        with self.assertNumQueries(5):
            for menu, created in Menu.menus.get_or_create():
                self.assertFalse(created)

        with self.assertNumQueries(4):
            for menu, created in TestMenu.menus.get_or_create():
                self.assertEqual(menu.__class__, TestMenu)
                self.assertTrue(isinstance(menu, TestMenu))
                self.assertTrue(isinstance(menu, Menu))
                self.assertFalse(created)

    def test_repr_sanity_etc(self):
        menus = Menu.menus.models()
        menu = next(menus)()
        request = RequestFactory().get('/')
        for x in menu.get_nodes(request=request):
            repr = ('<menuhin.models.MenuNode: {obj.depth} ({obj.unique_id}, '
                    '{obj.parent_id}, {obj.title})>'.format(obj=x))
            self.assertEqual(repr, repr(x))
            self.assertEqual(x.title, unicode(x))

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

    def test_equality(self):
        request = RequestFactory().get('/')
        nodes = TestMenu.menus.get_nodes(request)
        users, nodes = _building_and_menu()[0:2]
        self.assertEqual(nodes[0], nodes[0])
        self.assertNotEqual(nodes[0], nodes[1])
        self.assertNotEqual(nodes[0], nodes[2])
        self.assertNotEqual(nodes[0], nodes[3])
        # and patching one to make it equal ...
        nodes[3].unique_id = nodes[0].unique_id
        self.assertEqual(nodes[0], nodes[3])


def _building_and_menu(skip=1, maxnum=None):
    """
    Crap helper method.
    """
    if maxnum is None:
        maxnum = randrange(50, 100)
    users = list(mommy.make('auth.User') for x in xrange(1, maxnum))
    menus = Menu.menus.models()
    for x in xrange(0, skip):
        MenuKlass = next(menus)
    # with self.assertNumQueries(1):
    request = RequestFactory().get('/')
    menu = MenuKlass.menus.get_nodes(request)
    return users, list(menu), MenuKlass


class MenuhinUsageTests(DjangoTestCase):
    def test_building(self):
        parent_user = 0
        for user, node in zip(*_building_and_menu()[0:2]):
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
        bundled = izip(*_building_and_menu()[0:2])

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
        request = RequestFactory().get('/')
        with self.assertNumQueries(3):
            self.assertEqual(list(MenuKlass().get_nodes(request=request)),
                             list(MenuKlass.menus.get_nodes(request=request)))

    def test_all_as_api_frontend(self):
        users, menu, klass = _building_and_menu(skip=2)
        self.assertEqual(TestMenuChild, klass)
        request = RequestFactory().get(
            '/test-menu-child/%s' % slugify(unicode(users[5]))
        )
        get_processed = list(klass.menus.get_processed_nodes(request=request))
        all_ = list(klass.menus.all(request=request))
        self.assertEqual(get_processed, all_)

    def test_filter_as_api_frontend(self):
        users, menu, klass = _building_and_menu(skip=2)
        self.assertEqual(TestMenuChild, klass)
        request = RequestFactory().get(
            '/test-menu-child/%s' % slugify(unicode(users[5]))
        )
        filtered = list(klass.menus.filter(request=request))
        all_ = list(klass.menus.all(request=request))
        get_processed = list(klass.menus.get_processed_nodes(request=request))
        self.assertEqual(get_processed, all_)
        self.assertEqual(all_, filtered)
        self.assertEqual(filtered, get_processed)

    def test_getting_models_by_slug(self):
        with self.assertNumQueries(20):
            for menu, created in Menu.menus.get_or_create():
                self.assertTrue(created)
        slugs = ('test-menu-grand-child', 'test-menu-second-child')
        self.assertEqual(list(Menu.menus.model_slugs(lookups=slugs)), [
            TestMenuGrandChild, TestMenuSecondChild
        ])

    def test_getting_models_by_slug2(self):
        with self.assertNumQueries(20):
            for menu, created in Menu.menus.get_or_create():
                self.assertTrue(created)
        result = Menu.menus.model_slug(lookup='test-menu-second-child')
        self.assertEqual(result, TestMenuSecondChild)


class MenuhinProcessorsUsageTests(DjangoTestCase):

    def test_processors_is_active(self):
        users, menu, klass = _building_and_menu(skip=2)
        self.assertEqual(TestMenuChild, klass)
        request = RequestFactory().get(
            '/test-menu-child/%s' % slugify(unicode(users[5]))
        )
        fetched_nodes = list(klass.menus.get_processed_nodes(request=request))
        # sanity ...
        self.assertEqual(len(users), len(fetched_nodes))

        # without the heirarchy calculator, only one thing can be active
        results = [x.url for x in fetched_nodes
                   if x.extra_context.get('is_active', False)]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], request.get_full_path())

    def test_processors_heirarchy(self):
        users, menu, klass = _building_and_menu(skip=3)
        self.assertEqual(TestMenuGrandChild, klass)
        request = RequestFactory().get('/')
        fetched_nodes = list(klass.menus.get_processed_nodes(request=request))
        # sanity ...
        self.assertEqual(len(users), len(fetched_nodes))
        # depth from beginning should be the same ...
        for offset, node in enumerate(fetched_nodes,
                                      start=klass.processors[0].start):
            self.assertEqual(offset, node.depth)

        first = fetched_nodes[0]
        # no ancestors.
        self.assertEqual(0, len(first.ancestors))
        self.assertEqual([], first.ancestors)

        # all descendants
        first_descendants = [x for x in klass.menus.get_nodes(request=request)
                             if x != first]
        self.assertEqual(first.descendants, first_descendants)

        last = fetched_nodes[-1]
        # no descendants.
        self.assertEqual(0, len(last.descendants))
        self.assertEqual([], last.descendants)

        # all ancestors
        last_ancestors = [x for x in klass.menus.get_nodes(request=request)
                          if x != last]
        self.assertEqual(last.ancestors, last_ancestors)

    def test_processors_mark_ancestors_active(self):
        users, menu, klass = _building_and_menu(skip=4)
        self.assertEqual(TestMenuSecondChild, klass)
        user_offset = 7
        url = '/second-child/%s' % slugify(unicode(users[user_offset]))
        request = RequestFactory().get(url)
        fetched_nodes = list(klass.menus.get_processed_nodes(request=request))
        # sanity ...
        self.assertEqual(len(users), len(fetched_nodes))
        active_urls = [x.url for x in fetched_nodes
                       if x.extra_context.get('is_active', False)]
        self.assertEqual(1, len(active_urls))
        self.assertEqual(active_urls[0], url)

        ancestor_urls = [x.url for x in fetched_nodes
                         if x.extra_context.get('is_ancestor', False)]
        expected_urls = ['/second-child/%s' % slugify(unicode(x))
                         for x in users[:user_offset]]
        self.assertEqual(user_offset, len(ancestor_urls))
        self.assertEqual(ancestor_urls, expected_urls)

        ancestor_objs = [x for x in fetched_nodes
                         if x.extra_context.get('is_ancestor', False)]
        expected_objs = [MenuNode(title=unicode(x),
                                  url='/second-child/%s' % slugify(unicode(x)),
                                  unique_id='user_%s' % x.pk)
                         for x in users[:user_offset]]
        self.assertEqual(user_offset, len(ancestor_objs))
        self.assertEqual(ancestor_objs, expected_objs)

    def test_depth_min_depth(self):
        users, menu, klass = _building_and_menu(skip=4)
        self.assertEqual(TestMenuSecondChild, klass)
        user_offset = 7
        url = '/test/%s' % slugify(unicode(users[user_offset]))
        request = RequestFactory().get(url)
        fetched_nodes = list(klass.menus.filter(request=request, min_depth=3))
        # sanity ...
        self.assertEqual(len(users) - 2, len(fetched_nodes))
        # depth from beginning should be the same ...
        for offset, node in enumerate(fetched_nodes, start=3):
            self.assertEqual(offset, node.depth)

    def test_depth_max_depth(self):
        users, menu, klass = _building_and_menu(skip=4)
        self.assertEqual(TestMenuSecondChild, klass)
        user_offset = 7
        url = '/test/%s' % slugify(unicode(users[user_offset]))
        request = RequestFactory().get(url)
        fetched_nodes = list(klass.menus.filter(request=request, max_depth=2))
        # sanity ...
        self.assertEqual(2, len(fetched_nodes))
        # depth from beginning should be the same ...
        for offset, node in enumerate(fetched_nodes, start=1):
            self.assertEqual(offset, node.depth)

    def test_depth_bad_min_max_depth(self):
        users, menu, klass = _building_and_menu(skip=4)
        self.assertEqual(TestMenuSecondChild, klass)
        user_offset = 7
        url = '/test/%s' % slugify(unicode(users[user_offset]))
        request = RequestFactory().get(url)
        fetched_nodes = list(klass.menus.filter(request=request, min_depth=3,
                                                max_depth=2))
        # sanity ...
        self.assertEqual(0, len(fetched_nodes))

    def test_depth_good_min_max_depth(self):
        users, menu, klass = _building_and_menu(skip=4)
        self.assertEqual(TestMenuSecondChild, klass)
        user_offset = 7
        url = '/test/%s' % slugify(unicode(users[user_offset]))
        request = RequestFactory().get(url)
        fetched_nodes = list(klass.menus.filter(request=request, min_depth=2,
                                                max_depth=10))
        # sanity ...
        self.assertEqual(9, len(fetched_nodes))
        # depth from beginning should be the same ...
        for offset, node in enumerate(fetched_nodes, start=2):
            self.assertEqual(offset, node.depth)

class MenuhinCustomItemsTests(DjangoTestCase):
    def setUp(self):
        self.maxDiff = None
        self.users = list(mommy.make('auth.User')
                          for x in xrange(1, 10))
        self.menus = list(Menu.menus.get_or_create())

    def test_custom_making(self):
        custom = mommy.make('menuhin.CustomMenuItem', menu=self.menus[0][0],
                            title='yay custom!', target_id='user_4',
                            position='replacing', url='/yay/')
        request = RequestFactory().get('/')
        self.assertEqual(list(custom.to_menunode(request=request)), [MenuNode(
            title=custom.title,
            url=custom.url,
            unique_id='custom_menu_item_%s' % custom.pk,
            parent_id=custom.target_id,
        )])

    def test_custom_replacing(self):
        custom = mommy.make('menuhin.CustomMenuItem', menu=self.menus[0][0],
                            title='yay custom!', target_id='user_4',
                            position='replacing', url='/yay/')
        request = RequestFactory().get('/')
        menu = list(TestMenu.menus.get_nodes(request))
        expecting = [menu[3]]
        self.assertEqual(expecting, list(custom.to_menunode(request=request)))
        self.assertEqual(9, len(menu))

    def test_custom_before(self):
        custom = mommy.make('menuhin.CustomMenuItem', menu=self.menus[0][0],
                            title='yay custom!', target_id='user_4',
                            position='above', url='/yay/')
        request = RequestFactory().get('/')
        menu = list(TestMenu.menus.get_nodes(request=request))
        expecting = [menu[3]]
        self.assertEqual(expecting, list(custom.to_menunode(request=request)))
        self.assertEqual(10, len(menu))

    def test_custom_after(self):
        custom = mommy.make('menuhin.CustomMenuItem', menu=self.menus[0][0],
                            title='yay custom!', target_id='user_4',
                            position='below', url='/yay/')
        request = RequestFactory().get('/')
        menu = list(TestMenu.menus.get_nodes(request=request))
        expecting = [menu[4]]
        self.assertEqual(expecting, list(custom.to_menunode(request=request)))
        self.assertEqual(10, len(menu))

    def test_custom_attach_menu(self):
        custom = mommy.make('menuhin.CustomMenuItem', menu=self.menus[0][0],
                            title='yay custom!', target_id='user_4',
                            position='replacing', url='/yay/',
                            attach_menu=self.menus[4][0])
        request = RequestFactory().get('/')
        self.assertEqual(custom.get_attach_menu(request), TestMenuThirdChild)
        menu = list(TestMenu.menus.get_nodes(request=request))
        extra_nodes = list(custom.to_menunode(request=request))
        self.assertEqual(menu[3], extra_nodes[0])
        self.assertEqual(menu[4], extra_nodes[1])
        self.assertEqual(len(menu), 10)
        thirdnodes = list(TestMenuThirdChild.menus.get_nodes(request=request))
        self.assertEqual(len(thirdnodes), 1)
        self.assertEqual([extra_nodes[1]], thirdnodes)


class MenuhinTemplateTagTests(DjangoTestCase):
    def setUp(self):
        self.users = list(mommy.make('auth.User')
                          for x in xrange(1, 10))
        self.menus = list(Menu.menus.get_or_create())

    def test_loading(self):
        tmpl = Template("""
        {% load menus %}
        """)
        url = '/'
        request = RequestFactory().get(url)
        self.assertEqual('', tmpl.render(RequestContext(request)).strip())

    def test_basic_rendering(self):
        tmpl = Template("""
        {% load menus %}
        {% show_menu "test-menu" %}
        """)
        url = '/'
        request = RequestFactory().get(url)
        result = tmpl.render(RequestContext(request))
        lines = (x.strip() for x in result.strip().split("\n") if x.strip())
        safe_lines = list(lines)
        self.assertEqual(safe_lines[0],
                         '<ol class="menu  menu--fromdepth--0 '
                         'menu--todepth--100">')
        self.assertEqual(safe_lines[-1],
                         '</ol>')
        remainder = safe_lines[1:-1]
        # self.assertEqual('', result.strip())

    def test_plaintext_rendering(self):
        tmpl = Template("""
        {% load menus %}
        {% show_menu "test-menu" 0 100 "menuhin/show_menu/plaintext.html" %}
        """)
        url = '/'
        request = RequestFactory().get(url)
        result = tmpl.render(RequestContext(request))
        lines = (x.strip() for x in result.strip().split("\n") if x.strip())
        safe_lines = list(lines)

        self.assertEqual(len(self.users), len(safe_lines))
        for line, user in zip(safe_lines, self.users):
            self.assertEqual(line, '%s [/test/%s]' % (unicode(user),
                                                      slugify(unicode(user))))
