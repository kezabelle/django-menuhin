try:
    from django.utils.unittest import TestCase
except ImportError:
    from unittest import TestCase
from django.core.exceptions import ValidationError
from menuhin.models import MenuItem, is_valid_uri, MenuItemGroup, URI


class IsValidUriTestCase(TestCase):
    def test_is_valid_scheme(self):
        self.assertTrue(is_valid_uri('http://'))
        self.assertTrue(is_valid_uri('https://'))
        self.assertTrue(is_valid_uri('//'))

    def test_invalid_scheme(self):
        with self.assertRaises(ValidationError):
            is_valid_uri('ftp://')

    def test_is_valid_other(self):
        self.assertTrue(is_valid_uri('/a/agd/'))


class BalancingTitlesTestCase(TestCase):
    def test_balanced_template(self):
        obj = MenuItem(title='{{ a }}')
        self.assertTrue(obj.title_has_balanced_template_params())

    def test_balanced_format(self):
        obj = MenuItem(title='{a}')
        self.assertTrue(obj.title_has_balanced_format_params())

    def test_title_needs_parsing(self):
        obj = MenuItem(title='{a}')
        self.assertTrue(obj.title_needs_parsing())
        obj2 = MenuItem(title='{{a}}')
        self.assertTrue(obj2.title_needs_parsing())

    def test_title_doesnt_need_parsing(self):
        obj = MenuItem(title='yay, :}}}')
        self.assertFalse(obj.title_needs_parsing())

    def test_parsed_format(self):
        obj = MenuItem(title='yay, {a!s}!')
        self.assertEqual('yay, 1!', obj.parsed_title({'a': 1}))

    def test_parsed_template(self):
        obj = MenuItem(title='yay, {{ a }}!')
        self.assertEqual('yay, 2!', obj.parsed_title({'a': 2}))

    def test_parsed_nothing_to_do(self):
        obj = MenuItem(title='yay, 3!')
        self.assertEqual('yay, 3!', obj.parsed_title({'a': 1}))

    def test_parsed_unbalanced(self):
        obj = MenuItem(title='{ yay, :}}}')
        self.assertEqual('{ yay, :}}}', obj.parsed_title({'a': 4}))


class MenuItemBasicTestCase(TestCase):
    def test_cleaning(self):
        obj = MenuItem(title='x', uri='/a/b/c/')
        self.assertEqual(obj.menu_slug, '')
        obj.clean()
        self.assertEqual(obj.menu_slug, 'a-b-c')

    def test_get_absolute_url(self):
        obj = MenuItem(title='x', uri='/a/b/c/')
        self.assertEqual(obj.get_absolute_url(), '/a/b/c/')


class MyMenuIsNeat(MenuItemGroup):
    def get_urls(self, *a, **kw):
        yield URI(title='a', path='/a/')
        yield URI(title='a', path='/a/')
        yield URI(title='a', path='/a/')


class MenuItemGroupTestCase(TestCase):
    def test_needs_implementing(self):
        with self.assertRaises(NotImplementedError):
            MenuItemGroup().get_urls()

    def test_implementation_name(self):
        x = MyMenuIsNeat()
        self.assertEqual(x.title, 'my menu is neat')

    def test_calling_urls(self):
        menu = MyMenuIsNeat()
        menu_urls = tuple(menu.get_urls())
        self.assertEqual(len(menu_urls), 3)
