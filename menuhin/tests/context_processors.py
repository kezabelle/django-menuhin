from django.test import TestCase as TestCaseUsingDB
from django.test.client import RequestFactory
from menuhin.models import MenuItem
from menuhin.context_processors import request_ancestors, request_descendants
from .data import get_bulk_data


class LazyAncestorsTestCase(TestCaseUsingDB):
    def setUp(self):
        MenuItem.load_bulk(get_bulk_data())
        self.rf = RequestFactory()

    def test_usage(self):
        req = self.rf.get('/a/b/c/')
        resp = request_ancestors(req)
        self.assertIn('MENUHIN_ANCESTORS', resp)
        uris = [x.uri for x in resp['MENUHIN_ANCESTORS']]
        self.assertEqual(uris, ['/a/'])

    def test_check_for_middleware(self):
        req = self.rf.get('/a/')
        req.ancestors = 'FAKE'
        resp = request_ancestors(req)
        self.assertIn('MENUHIN_ANCESTORS', resp)
        self.assertEqual(resp['MENUHIN_ANCESTORS'], 'FAKE')


class LazyDescendantsTestCase(TestCaseUsingDB):
    def setUp(self):
        MenuItem.load_bulk(get_bulk_data())
        self.rf = RequestFactory()

    def test_usage(self):
        req = self.rf.get('/a/')
        resp = request_descendants(req)
        self.assertIn('MENUHIN_DESCENDANTS', resp)
        uris = [x.uri for x in resp['MENUHIN_DESCENDANTS']]
        self.assertEqual(uris, ['/a/b/c/', '/d/', '/e', '/HI', '/x/'])

    def test_check_for_middleware(self):
        req = self.rf.get('/a/')
        req.descendants = 'FAKE'
        resp = request_descendants(req)
        self.assertIn('MENUHIN_DESCENDANTS', resp)
        self.assertEqual(resp['MENUHIN_DESCENDANTS'], 'FAKE')
