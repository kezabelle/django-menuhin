try:
    from unittest import TestCase
except ImportError:
    from django.utils.unittest import TestCase
from django.test import TestCase as TestCaseWithDB
from django.test.utils import override_settings
from django.contrib.sites.models import Site
from menuhin.models import MenuItem
from menuhin.utils import (ensure_default_for_site, DefaultForSite,
                           get_menuitem_or_none, set_menu_slug)


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
