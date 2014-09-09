from django.test import TestCase as TestCaseWithDB
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings
from django.contrib.sites.models import Site
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.sites import NotRegistered
from django.forms.models import modelform_factory
from treebeard.forms import movenodeform_factory
from menuhin.models import MenuItem
from menuhin.admin import MenuItemAdmin
from menuhin.forms import ImportMenusForm, MenuItemTreeForm
from .data import get_bulk_data, TestMenu2


HANDLERS = (
    'menuhin.tests.data.TestMenu1',
    'menuhin.tests.data.TestMenu2'
)


class ImportMenusFormTestCase(TestCaseWithDB):

    def test_setting_not_found_raises_error(self):
        with self.settings(MENUHIN_MENU_HANDLERS=None):
            with self.assertRaises(ImproperlyConfigured):
                ImportMenusForm(data=None, files=None)

    @override_settings(SITE_ID=2, MENUHIN_MENU_HANDLERS=HANDLERS)
    def test_site_initial(self):
        site = Site(domain='x.com', name='x')
        site.full_clean()
        site.save()
        form = ImportMenusForm(data=None, files=None)
        self.assertEqual(form.fields['site'].initial, 2)

    @override_settings(MENUHIN_MENU_HANDLERS=HANDLERS)
    def test_menu_choices(self):
        form = ImportMenusForm(data=None, files=None)
        expected = [
            ('', '---------'),
            ('menuhin.tests.data.TestMenu1', 'test menu 1'),
            ('menuhin.tests.data.TestMenu2', 'test menu2')
        ]
        self.assertEqual(form.fields['klass'].choices, expected)

    @override_settings(MENUHIN_MENU_HANDLERS=HANDLERS)
    def test_menu_class_instance_from_cleaned_data(self):
        form = ImportMenusForm(data={
            'klass': 'menuhin.tests.data.TestMenu2',
            'site': 1,
        }, files=None)
        self.assertTrue(form.is_valid())
        klass = form._menu_class_instance_from_cleaned_data()
        self.assertIsInstance(klass, TestMenu2)

    @override_settings(MENUHIN_MENU_HANDLERS=HANDLERS)
    def test_invalid_cleaned_data_instance(self):
        form = ImportMenusForm(data={
            'klass': 'menuhin.tests.data.TestMenu999999',
            'site': 1,
        }, files=None)
        self.assertFalse(form.is_valid())
        # now fake some stuff, just to cover the branch.
        form.cleaned_data = {
            'klass': 'menuhin.tests.data.TestMenu999999'
        }
        with self.assertRaises(ValueError):
            form._menu_class_instance_from_cleaned_data()

    @override_settings(MENUHIN_MENU_HANDLERS=HANDLERS)
    def test_save_none_in_menu(self):
        form = ImportMenusForm(data={
            'klass': 'menuhin.tests.data.TestMenu1',
            'site': 1,
        }, files=None)
        self.assertTrue(form.is_valid())
        result = form.save()
        self.assertIsNone(result)

    @override_settings(MENUHIN_MENU_HANDLERS=HANDLERS)
    def test_save_some_in_menu(self):
        try:
            admin.site.unregister(User)
        except NotRegistered:
            pass
        admin.site.register(User, UserAdmin)
        try:
            admin.site.unregister(MenuItem)
        except NotRegistered:
            pass
        admin.site.register(MenuItem, MenuItemAdmin)
        form = ImportMenusForm(data={
            'klass': 'menuhin.tests.data.TestMenu2',
            'site': 1,
        }, files=None)
        self.assertTrue(form.is_valid())
        result = form.save()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)


class MenuItemTreeFormTestCase(TestCaseWithDB):
    @override_settings(SITE_ID=2)
    def test_site_initial(self):
        site = Site(domain='x.com', name='x')
        site.full_clean()
        site.save()
        form_for_class = movenodeform_factory(model=MenuItem,
                                              form=MenuItemTreeForm)
        form = form_for_class(data=None, files=None)
        self.assertEqual(form.fields['site'].initial, 2)

    def test_slug_not_in_cd(self):
        form_for_class = movenodeform_factory(model=MenuItem,
                                              form=MenuItemTreeForm,
                                              exclude=['menu_slug'])
        bound_data = {
            '_ref_node_id': 0,
            '_save': 'Save',
            '_position': 'first-child',
            'site': 1,
            'is_published': 'on',
            'uri': '/aaaaaaaaaaaaa/',
            'title': 'yays',
        }
        form = form_for_class(data=bound_data, files=None)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertIn('menu_slug', form.cleaned_data)
        self.assertEqual(form.cleaned_data['menu_slug'], 'aaaaaaaaaaaaa')
