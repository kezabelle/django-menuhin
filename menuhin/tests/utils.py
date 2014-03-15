try:
    from unittest import TestCase
except ImportError:
    from django.utils.unittest import TestCase
from django.test import TestCase as TestCaseWithDB
from django.test.utils import override_settings
from django.test.client import RequestFactory
from django.contrib.sites.models import Site
from django.db.models.query import EmptyQuerySet
from menuhin.models import MenuItem, URI
from menuhin.utils import (ensure_default_for_site, DefaultForSite,
                           get_menuitem_or_none, set_menu_slug,
                           RequestRelations, find_missing, add_urls,
                           get_relations_for_request, change_published_status,
                           marked_annotated_list, MenuItemURI, update_all_urls)
from .data import get_bulk_data


class EnsureDefaultTestCase(TestCaseWithDB):
    def setUp(self):
        Site.objects.clear_cache()

    @override_settings(SITE_ID=1)
    def test_creation(self):
        # 1 query for site, 1 to look the MenuItem up, 2 to insert it
        # if needs be.
        with self.assertNumQueries(4):
            default = ensure_default_for_site(MenuItem)
        self.assertIsInstance(default, DefaultForSite)
        self.assertTrue(default.created)
        self.assertEqual(default.obj.menu_slug, 'default')

    @override_settings(SITE_ID=1)
    def test_getting_but_not_creating(self):
        ensure_default_for_site(MenuItem)
        # 1 to look the MenuItem up; site was cached by the previous call.
        with self.assertNumQueries(1):
            default = ensure_default_for_site(MenuItem)
        self.assertIsInstance(default, DefaultForSite)
        self.assertFalse(default.created)
        self.assertEqual(default.obj.menu_slug, 'default')


class MenuItemOrNoneTestCase(TestCaseWithDB):
    def test_getting(self):
        existing = ensure_default_for_site(MenuItem)
        existing.obj.is_published = True
        existing.obj.save()
        with self.assertNumQueries(1):
            result = get_menuitem_or_none(MenuItem, '/')
        self.assertIsNotNone(result)
        self.assertIsInstance(result, MenuItem)
        self.assertEqual(result.uri, '/')

    def test_not_exists(self):
        with self.assertNumQueries(1):
            result = get_menuitem_or_none(MenuItem, '/a/b/c/')
        self.assertIsNone(result)


class SetMenuSlugTestCase(TestCase):
    def test_usage_with_qs(self):
        ms = set_menu_slug('/a/b/c/?d=e&f=g')
        self.assertEqual(ms, 'a-b-c')

    def test_usage_no_qs(self):
        ms = set_menu_slug('/a/b/c/')
        self.assertEqual(ms, 'a-b-c')

    def test_max_length(self):
        ms = set_menu_slug('/a/' * 100, model=MenuItem)
        self.assertEqual('a-' * 50, ms)


class RequestRelationsMethodsTestCase(TestCase):
    def test_has_relations(self):
        rel = RequestRelations(relations=(1, 2), obj=None,
                               requested='fake_method', path='/')
        self.assertTrue(rel.has_relations())

    def test_has_no_relations(self):
        rel = RequestRelations(relations=(), obj=None,
                               requested='fake_method', path='/')
        self.assertFalse(rel.has_relations())

    def test_found_instance(self):
        rel = RequestRelations(relations=(), obj=MenuItem(),
                               requested='fake_method', path='/')
        self.assertTrue(rel.found_instance())

    def test_found_no_instance(self):
        rel = RequestRelations(relations=(), obj=None,
                               requested='fake_method', path='/')
        self.assertFalse(rel.found_instance())

    def test_contains(self):
        rel = RequestRelations(relations=(1, 2), obj=None,
                               requested='fake_method', path='/')
        self.assertIn(2, rel)

    def test_does_not_contain(self):
        rel = RequestRelations(relations=(1, 2), obj=None,
                               requested='fake_method', path='/')
        self.assertNotIn(3, rel)

    def test_bool_true(self):
        rel = RequestRelations(relations=(1, 2), obj=1,
                               requested='fake_method', path='/')
        self.assertTrue(rel)

    def test_bool_false(self):
        rel = RequestRelations(relations=(1, 2), obj=None,
                               requested='fake_method', path='/')
        self.assertFalse(rel)


class FindMissingTestCase(TestCaseWithDB):
    def get_urls(self, *a, **kw):
        yield URI(title='a', path='/a/')
        yield URI(title='a-b', path='/a/b/')
        yield URI(title='a-b-c', path='/a/c/')

    def test_site_id_is_not_none(self):
        othersite = Site(domain='x.com', name='y.com')
        othersite.full_clean()
        othersite.save()
        urls = set(self.get_urls())
        result = find_missing(MenuItem, urls=urls, site_id=othersite)
        self.assertEqual(set(result), urls)

    def test_no_urls(self):
        self.assertIsNone(find_missing(MenuItem, urls=()))

    def test_none_missing(self):
        urls = set(self.get_urls())
        for x in urls:
            MenuItem.add_root(uri=x.path, title=x.title,
                              site_id=Site.objects.get_current().pk)
        self.assertIsNone(find_missing(MenuItem, urls=urls))


class AddUrlsTestCase(TestCaseWithDB):
    def get_urls(self, *a, **kw):
        yield URI(title='z', path='/xx/')
        yield URI(title='zz', path='/xx/x/')
        yield URI(title='zzz', path='/xx/x/xx/')

    def test_site_id_is_not_none(self):
        othersite = Site(domain='x.com', name='y.com')
        othersite.full_clean()
        othersite.save()
        urls = set(self.get_urls())
        result = tuple(add_urls(MenuItem, urls=urls, site_id=othersite.pk))
        self.assertEqual(len(result), 3)
        returned_uris = [x.uri for x in result]
        self.assertEqual(set(returned_uris), urls)
        for x in result:
            self.assertIsInstance(x, MenuItemURI)
            self.assertIsInstance(x.instance, MenuItem)
            self.assertEqual(x.instance.uri, x.uri.path)

    def test_site_id_is_none(self):
        urls = set(self.get_urls())
        result = tuple(add_urls(MenuItem, urls=urls))
        self.assertEqual(len(result), 3)
        returned_uris = [x.uri for x in result]
        self.assertEqual(set(returned_uris), urls)
        for x in result:
            self.assertIsInstance(x, MenuItemURI)
            self.assertIsInstance(x.instance, MenuItem)
            self.assertEqual(x.instance.uri, x.uri.path)

    def test_nothing_given_to_yield_back(self):
        result = tuple(add_urls(MenuItem, urls=()))
        self.assertEqual(len(result), 0)


class UpdateAllUrlsTestCase(TestCaseWithDB):
    def get_urls(self, *a, **kw):
        yield URI(title='z', path='/xx/')
        yield URI(title='zz', path='/xx/x/')
        yield URI(title='zzz', path='/xx/x/xx/')

    def test_needed_inserting(self):
        urls = set(self.get_urls())
        result = update_all_urls(model=MenuItem, possible_urls=urls)
        self.assertIsNotNone(result)
        results = tuple(result)
        self.assertEqual(len(results), 3)

    def test_didnt_need_inserting(self):
        # do the inserts ...
        self.test_needed_inserting()
        urls = set(self.get_urls())
        result = update_all_urls(model=MenuItem, possible_urls=urls)
        self.assertIsNone(result)


class GetRelationsForRequestTestCase(TestCaseWithDB):
    def test_middleware_is_not_none(self):
        rf = RequestFactory()
        req = rf.get('/a/b/c/')
        req.menuitem = MenuItem(path='/a/b/c/', title='yay',
                                is_published=True,
                                site_id=Site.objects.get_current().pk)
        results = get_relations_for_request(model=MenuItem, request=req,
                                            relation='get_ancestors')
        self.assertEqual(req.menuitem, results.obj)

    def test_middleware_is_not_none_but_is_falsy(self):
        rf = RequestFactory()
        req = rf.get('/a/b/c/')
        req.menuitem = False
        results = get_relations_for_request(model=MenuItem, request=req,
                                            relation='get_ancestors')
        self.assertIsNone(results.obj)

    def test_middleware_is_none(self):
        rf = RequestFactory()
        req = rf.get('/a/b/c/')
        req.menuitem = None
        results = get_relations_for_request(model=MenuItem, request=req,
                                            relation='get_ancestors')
        self.assertIsNone(results.obj)

    def test_no_middleware_found(self):
        rf = RequestFactory()
        req = rf.get('/a/b/c/')
        results = get_relations_for_request(model=MenuItem, request=req,
                                            relation='get_ancestors')
        self.assertIsNone(results.obj)


class ChangePublishedStatusTestCase(TestCaseWithDB):
    def test_usage(self):
        MenuItem.add_root(title='x', is_published=True,
                          site=Site.objects.get_current())
        MenuItem.add_root(title='y', is_published=False,
                          site=Site.objects.get_current())
        with self.assertNumQueries(4):
            change_published_status(queryset=MenuItem.objects.all(),
                                    modeladmin=None, request=None)
        self.assertFalse(MenuItem.objects.get(title='x').is_published)
        self.assertTrue(MenuItem.objects.get(title='y').is_published)


class MarkedAnnotatedListTestCase(TestCaseWithDB):
    def setUp(self):
        MenuItem.load_bulk(get_bulk_data())

    def test_no_current_node(self):
        tree = MenuItem.get_published_annotated_list(parent=None)
        rf = RequestFactory()
        req = rf.get('/zzzzzzzz/')
        results = marked_annotated_list(request=req, tree=tree)
        find_actives = [mi for mi, crap in results if mi.is_active]
        self.assertEqual(len(find_actives), 0)

    def test_current_node(self):
        tree = MenuItem.get_published_annotated_list(parent=None)
        rf = RequestFactory()
        req = rf.get('/a/')
        results = marked_annotated_list(request=req, tree=tree)
        find_actives = [mi for mi, crap in results if mi.is_active]
        self.assertEqual(len(find_actives), 1)
        self.assertEqual(find_actives[0].title, '2')
        self.assertEqual(find_actives[0].uri, '/a/')
        self.assertTrue(find_actives[0].is_active)

    def test_current_node_forces_other_markings(self):
        tree = MenuItem.get_published_annotated_list(parent=None)
        rf = RequestFactory()

        req = rf.get('/a/b/c/')
        results = marked_annotated_list(request=req, tree=tree)

        active = [mi for mi, crap in results if mi.is_active]
        desc = [mi for mi, crap in results if mi.is_descendant]
        ance = [mi for mi, crap in results if mi.is_ancestor]
        siblings = [mi for mi, crap in results if mi.is_sibling]
        self.assertEqual(len(active), 1)
        self.assertEqual(len(desc), 0)
        self.assertEqual(len(ance), 1)
        self.assertEqual(len(siblings), 3)

        active_urls = [x.uri for x in active]
        desc_urls = [x.uri for x in desc]
        ancestor_urls = [x.uri for x in ance]
        sibling_urls = [x.uri for x in siblings]
        self.assertEqual(active_urls, ['/a/b/c/'])
        self.assertEqual(desc_urls, [])
        self.assertEqual(ancestor_urls, ['/a/'])
        self.assertEqual(sibling_urls, ['/d/', '/e', '/x/'])

    def test_current_node_forces_other_markings2(self):
        tree = MenuItem.get_published_annotated_list(parent=None)
        rf = RequestFactory()

        req = rf.get('/a/')
        results = marked_annotated_list(request=req, tree=tree)

        active = [mi for mi, crap in results if mi.is_active]
        desc = [mi for mi, crap in results if mi.is_descendant]
        ance = [mi for mi, crap in results if mi.is_ancestor]
        siblings = [mi for mi, crap in results if mi.is_sibling]
        self.assertEqual(len(active), 1)
        self.assertEqual(len(desc), 5)
        self.assertEqual(len(ance), 0)
        self.assertEqual(len(siblings), 3)

        active_urls = [x.uri for x in active]
        desc_urls = [x.uri for x in desc]
        ancestor_urls = [x.uri for x in ance]
        sibling_urls = [x.uri for x in siblings]
        self.assertEqual(active_urls, ['/a/'])
        self.assertEqual(desc_urls, ['/a/b/c/', '/d/', '/e', '/HI', '/x/'])
        self.assertEqual(ancestor_urls, [])
        self.assertEqual(sibling_urls, ['/', '/sup', '/yo'])
