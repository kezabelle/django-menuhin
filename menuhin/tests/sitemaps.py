from datetime import datetime, timedelta
try:
    from unittest import TestCase
except ImportError:
    from django.utils.unittest import TestCase
from django.test import TestCase as TestCaseWithDB
from django.contrib.sites.models import Site
from menuhin.models import MenuItem
from menuhin.sitemaps import MenuItemSitemap


class SitemapTestCase(TestCaseWithDB):
    def setUp(self):
        site = Site.objects.get_current().pk
        BASE_DATA = [
            {'data': {'title': '1', 'site': site, 'is_published': True}},
            {'data': {'title': '2', 'site': site, 'is_published': True}, 'children': [
                {'data': {'title': '21', 'site': site, 'is_published': True}},
                {'data': {'title': '22', 'site': site, 'is_published': True}},
                {'data': {'title': '23', 'site': site, 'is_published': True}, 'children': [
                    {'data': {'title': '231', 'site': site, 'is_published': True}},
                ]},
                {'data': {'title': '24', 'site': site, 'is_published': True}},
            ]},
            {'data': {'title': '3', 'site': site, 'is_published': True}},
            {'data': {'title': '4', 'site': site, 'is_published': True}, 'children': [
                {'data': {'title': '41', 'site': site, 'is_published': True}},
            ]},
        ]
        MenuItem.load_bulk(BASE_DATA)

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
