# -*- coding: utf-8 -*-
from copy import deepcopy
from django.contrib import admin
from django.forms import ModelForm, Select
from helpfulfields.admin import (changetracking_fieldset,
                                 changetracking_readonlys)
from menuhin.models import Menu, menu_handlers, CustomMenuItem
from menuhin.text import config_fieldset_label


class CustomMenuItemForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(CustomMenuItemForm, self).__init__(*args, **kwargs)
        self.fields['parent_id'].widget = Select(choices=())
        self.fields['attach_menu'].required = False

    def clean(self):
        return super(CustomMenuItemForm, self).clean()

    class Meta:
        model = CustomMenuItem


class CustomMenuItemInline(admin.StackedInline):
    model = CustomMenuItemForm.Meta.model
    extra = 0
    fk_name = 'menu'
    fields = (
        'title',
        ('url', 'attach_menu'),
        ('position', 'parent_id'),
        'is_published'
    )
    form = CustomMenuItemForm


class MenuAdmin(admin.ModelAdmin):
    list_display = [
        'get_title',
        'display_title',
        'site',
        'is_published',
        'modified'
    ]
    list_display_links = [
        'get_title',
        'display_title'
    ]
    search_fields = [
        'title',
        'display_title',
    ]
    list_filter = [
        'is_published',
        'site'
    ]
    actions = None
    fieldsets = [
        changetracking_fieldset,
        [None, {
            'fields': [
                'title',
                'display_title',
            ]
        }],
        [config_fieldset_label, {
            'fields': [
                'site',
                'is_published',
            ]
        }]
    ]
    inlines = (
        CustomMenuItemInline,
    )
    readonly_fields = changetracking_readonlys

    def get_title(self, obj):
        return obj.title
    get_title.short_description = ''
    get_title.admin_order_field = 'title'

    def get_readonly_fields(self, request, obj=None):
        """
        Adds the internal slug field `title` to the non-editable fields list
        when in edit mode.

        This ensures we can still create menus via the admin, but cannot break
        any usages elsewhere on the site.
        """
        if obj:
            return ['title'] + deepcopy(self.readonly_fields)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        """
        Do we have permission to delete this menu?
        """
        if obj is not None:
            all_menus = menu_handlers.menus
            if obj.title in all_menus.keys():
                return False
        return super(MenuAdmin, self).has_delete_permission(request, obj)

    def get_object(self, *args, **kwargs):
        """
        On viewing an object, let's make sure we've loaded all the menus.
        """
        obj = super(MenuAdmin, self).get_object(*args, **kwargs)
        if obj is not None:
            menu_handlers.load_menus()
        return obj
admin.site.register(Menu, MenuAdmin)
