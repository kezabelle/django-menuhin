# -*- coding: utf-8 -*-
from copy import deepcopy
from django.contrib import admin
from django.forms import ModelForm, Select
from django.forms.models import BaseInlineFormSet
from helpfulfields.admin import (changetracking_fieldset,
                                 changetracking_readonlys)
from menuhin.models import Menu, CustomMenuItem
from menuhin.text import config_fieldset_label


class CustomMenuItemForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.parent_instance = None
        if 'parent_instance' in kwargs:
            self.parent_instance = kwargs.pop('parent_instance')

        super(CustomMenuItemForm, self).__init__(*args, **kwargs)
        self.fields['target_id'].widget = Select(choices=())
        self.fields['attach_menu'].required = False

        # don't allow linking to self
        # TODO: + any in self's descendant nodes?
        if self.parent_instance is not None and self.parent_instance.pk:
            exclude = Menu.objects.exclude(pk=self.parent_instance.pk)
            self.fields['attach_menu'].queryset &= exclude

    class Meta:
        model = CustomMenuItem


class CustomMenuItemFormSet(BaseInlineFormSet):
    """
    This crap is needed to put the currently edited object into the bloody
    modelform ...
    """
    def _construct_form(self, i, **kwargs):
        kwargs['parent_instance'] = self.instance
        return super(CustomMenuItemFormSet, self)._construct_form(i, **kwargs)

    @property
    def empty_form(self):
        """
        Exactly the same as upstream, + parent_instance.
        """
        form = self.form(
            auto_id=self.auto_id,
            prefix=self.add_prefix('__prefix__'),
            empty_permitted=True,
            parent_instance=self.instance,
        )
        self.add_fields(form, None)
        return form


class CustomMenuItemInline(admin.StackedInline):
    model = CustomMenuItemForm.Meta.model
    extra = 0
    fk_name = 'menu'
    fields = (
        'title',
        ('url', 'attach_menu'),
        ('position', 'target_id'),
        'is_published'
    )
    form = CustomMenuItemForm
    formset = CustomMenuItemFormSet


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

    def ensure_menus(self):
        return len(set(Menu.menus.get_or_create())) > 0

    def __init__(self, *args, **kwargs):
        super(MenuAdmin, self).__init__(*args, **kwargs)

    def get_model_perms(self, request):
        self.ensure_menus()
        return super(MenuAdmin, self).get_model_perms(request=request)

admin.site.register(Menu, MenuAdmin)
