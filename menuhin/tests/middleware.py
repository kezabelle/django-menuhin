try:
    from django.utils.unittest import TestCase
except ImportError:
    from unittest import TestCase
from django.test import TestCase as TestCaseWithDB
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.contrib.sites.models import Site
from menuhin.models import MenuItem
from menuhin.middleware import RequestTreeMiddleware
from .data import get_bulk_data


class RequestTreeMiddlewareTestCase(TestCaseWithDB):
    def setUp(self):
        self.rf = RequestFactory()
        self.mw = RequestTreeMiddleware()
        MenuItem.load_bulk(get_bulk_data())

    @override_settings(MEDIA_URL='/a/b/c/', STATIC_URL='/b/')
    def test_is_ignored(self):
        req = self.rf.get('/a/b/c/d.jpg')
        self.assertIsNone(self.mw.process_request(req))

    def test_menuitem_is_published(self):
        MenuItem.add_root(uri='/a/b/', title='found',
                          site=Site.objects.get_current(),
                          is_published=True)
        req = self.rf.get('/a/b/')
        self.mw.process_request(req)
        with self.assertNumQueries(1):
            self.assertEqual(req.menuitem.uri, '/a/b/')
            self.assertEqual(req.menuitem.title, 'found')

    def test_menuitem_is_none_because_not_published(self):
        MenuItem.add_root(uri='/a/b/', title='found',
                          site=Site.objects.get_current(),
                          is_published=False)
        req = self.rf.get('/a/b/')
        self.mw.process_request(req)
        with self.assertNumQueries(1):
            with self.assertRaises(AttributeError):
                self.assertIsNone(req.menuitem.uri)

    def test_descendants(self):
        req = self.rf.get('/a/')
        self.mw.process_request(req)
        with self.assertNumQueries(7):
            descendants = [x for x in req.descendants]
        urls = [x.uri for x in descendants]
        self.assertEqual(urls, ['/a/b/c/', '/d/', '/e', '/HI', '/x/'])

    def test_ancestors(self):
        req = self.rf.get('/a/b/c/')
        self.mw.process_request(req)
        with self.assertNumQueries(3):
            ancestors = [x for x in req.ancestors]
        urls = [x.uri for x in ancestors]
        self.assertEqual(urls, ['/a/'])

    def test_siblings(self):
        req = self.rf.get('/a/')
        self.mw.process_request(req)
        with self.assertNumQueries(6):
            siblings = [x for x in req.siblings]
        urls = [x.uri for x in siblings]
        self.assertEqual(urls, ['/', '/a/', '/sup', '/yo'])

    def test_children(self):
        req = self.rf.get('/a/')
        self.mw.process_request(req)
        with self.assertNumQueries(6):
            children = [x for x in req.children]
        urls = [x.uri for x in children]
        self.assertEqual(urls, ['/a/b/c/', '/d/', '/e', '/x/'])
