from datetime import datetime, timedelta
try:
    from unittest import TestCase
except ImportError:
    from django.utils.unittest import TestCase
from django.test import TestCase as TestCaseWithDB
from django.contrib.sites.models import Site
from menuhin.models import MenuItem
from menuhin.sitemaps import MenuItemSitemap
from .data import get_bulk_data

class SitemapTestCase(TestCaseWithDB):
    def setUp(self):
        MenuItem.load_bulk(get_bulk_data())

    def test_priority(self):
        sitemap = MenuItemSitemap()
        items = sitemap.items()
        self.assertEqual(
            [sitemap.priority(m) for m in items],
            [0.9, 0.9, 0.8, 0.8, 0.8, 0.7, 0.8, 0.9, 0.9, 0.8])

    def test_changefreq(self):
        sitemap = MenuItemSitemap()
        MenuItem.objects.filter(title='3').update(
            modified=datetime.utcnow() - timedelta(days=5))
        MenuItem.objects.filter(title='41').update(
            modified=datetime.utcnow() - timedelta(days=8))

        items = sitemap.items()
        results = [sitemap.changefreq(m) for m in items]
        first_daily = results[:7]
        weekly = results[7:8]
        remaining_daily = results[8:9]
        monthly = results[9:10]
        self.assertEqual(first_daily, ['daily'] * 7)
        self.assertEqual(weekly, ['weekly'])
        self.assertEqual(remaining_daily, ['daily'])
        self.assertEqual(monthly, ['monthly'])

    def test_lastmod(self):
        sitemap = MenuItemSitemap()
        items = sitemap.items()
        results = [sitemap.lastmod(m) for m in items]
        self.assertEqual(len(results), 10)
        for x in results:
            self.assertIsInstance(x, datetime)
            self.assertGreater(
                x, datetime.utcnow() - timedelta(minutes=3600))
            self.assertLess(x, datetime.utcnow())
