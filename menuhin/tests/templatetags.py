from django.test import TestCase as TestCaseUsingDB
from django.test.client import RequestFactory
from django.template import Template, Context
from django.contrib.sites.models import Site
from menuhin.models import MenuItem
from .data import get_bulk_data


class ShowBreadcrumbsTestCase(TestCaseUsingDB):
    def setUp(self):
        MenuItem.load_bulk(get_bulk_data())

    def test_basic_usage(self):
        req = RequestFactory().get('/HI')
        template = Template('''
        {% load menus %}
        {% show_breadcrumbs %}
        ''')
        context = Context({
            'request': req,
        })
        rendered = template.render(context).strip()
        self.assertIn('<ol class="breadcrumbs">', rendered)
        self.assertIn(
            "breadcrumbs-ancestor breadcrumbs-first breadcrumbs-root",
            rendered)
        self.assertIn('data-depth="1"', rendered)
        self.assertIn('data-depth="2"', rendered)
        self.assertIn('data-depth="3"', rendered)
        self.assertIn(
            'breadcrumbs-self breadcrumbs-last breadcrumb-selected',
            rendered)
        self.assertIn(
            '<a href="/HI" class="breadcrumbs-self-link">231</a>',
            rendered)

    def test_basic_usage_as_var(self):
        req = RequestFactory().get('/HI')
        template = Template('''
        {% load menus %}
        {% show_breadcrumbs as crazylegs %}
        {{ crazylegs.menu_node.uri }}
        ''')
        context = Context({
            'request': req,
        })
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '/HI')

    def test_pk_lookup(self):
        req = RequestFactory().get('/HI')
        template = Template('''
        {% load menus %}
        {% show_breadcrumbs 2 as crazylegs %}
        {{ crazylegs.menu_node.uri }}
        ''')
        context = Context({
            'request': req,
        })
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '/a/')

    def test_slug_lookup(self):
        req = RequestFactory().get('/HI')
        template = Template('''
        {% load menus %}
        {% show_breadcrumbs 'hi' as crazylegs %}
        {{ crazylegs.menu_node.uri }}
        ''')
        context = Context({
            'request': req,
        })
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '/HI')

    def test_path_lookup(self):
        template = Template('''
        {% load menus %}
        {% show_breadcrumbs '/a/b/c/' as crazylegs %}
        {{ crazylegs.menu_node.uri }}
        ''')
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '/a/b/c/')

    def test_bad_lookup(self):
        template = Template('''
        {% load menus %}
        {% show_breadcrumbs as crazylegs %}
        {{ crazylegs.menu_node.uri }}
        ''')
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '')

    def test_bad_menuitem(self):
        template = Template('''
        {% load menus %}
        {% show_breadcrumbs '1111111' as crazylegs %}
        {{ crazylegs.menu_node.uri }}
        ''')
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '')


class ParseTitleTestCase(TestCaseUsingDB):
    def setUp(self):
        MenuItem.load_bulk(get_bulk_data())

    def test_has_no_parsed_title_attr(self):
        template = Template('''
        {% load menus %}
        {% parse_title None %}
        ''')
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '')

    def test_parse_title_no_request(self):
        template = Template('''
        {% load menus %}
        {% parse_title testobj %}
        ''')
        context = Context({
            'testobj': MenuItem(title='xxx {site}',
                                site=Site.objects.get_current())
        })
        rendered = template.render(context).strip()
        self.assertEqual(rendered, 'xxx example.com')


    def test_parse_title_with_request(self):
        template = Template('''
        {% load menus %}
        {% parse_title testobj %}
        ''')
        context = Context({
            'testobj': MenuItem(title='xxx {{ request.path|default:"zzz" }}',
                                site=Site.objects.get_current()),
            'request': RequestFactory().get('/wheeee/')
        })
        rendered = template.render(context).strip()
        self.assertEqual(rendered, 'xxx /wheeee/')


class ShowMenuTestCase(TestCaseUsingDB):
    def setUp(self):
        MenuItem.load_bulk(get_bulk_data())

    def test_basic_usage(self):
        req = RequestFactory().get('/HI')
        template = Template('''
        {% load menus %}
        {% show_menu 'default' %}
        ''')
        context = Context({
            'request': req,
        })
        rendered = template.render(context).strip()
        self.assertIn('data-depth="1"', rendered)
        self.assertIn('data-depth="3"', rendered)
        self.assertIn('<a href="/HI" class="menu-link menu-link-level-2 '
                      'menu-link-selected">', rendered)
        # end piece
        self.assertIn('24</a></li></ul></li></ul>', rendered)

    def test_basic_usage_as_var(self):
        req = RequestFactory().get('/HI')
        template = Template('''
        {% load menus %}
        {% show_menu as crazylegs %}
        {{ crazylegs.menu_root.uri }} ... {{ crazylegs.menu_nodes|length }}
        ''')
        context = Context({
            'request': req,
        })
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '/a/ ... 6')

    def test_pk_lookup(self):
        req = RequestFactory().get('/HI')
        template = Template('''
        {% load menus %}
        {% show_menu 4 as crazylegs %}
        {{ crazylegs.menu_root.uri }} ... {{ crazylegs.menu_nodes|length }}
        ''')
        context = Context({
            'request': req,
        })
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '/d/ ... 1')

    def test_slug_lookup(self):
        req = RequestFactory().get('/HI')
        template = Template('''
        {% load menus %}
        {% show_menu 'hi' as crazylegs %}
        {{ crazylegs.menu_root.uri }} ... {{ crazylegs.menu_nodes|length }}
        ''')
        context = Context({
            'request': req,
        })
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '/HI ... 1')

    def test_bad_menuitem(self):
        template = Template('''
        {% load menus %}
        {% show_menu '1111111' as crazylegs %}
        {{ crazylegs.menu_node.uri }}
        ''')
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '')
