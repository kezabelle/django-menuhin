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
                           RequestRelations, find_missing,
                           get_relations_for_request, change_published_status)


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
