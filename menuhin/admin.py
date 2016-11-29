# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from functools import update_wrapper

from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from treebeard.admin import TreeAdmin

from menuhin.forms import MenuItemTreeForm
from .models import MenuItem, registry


@transaction.atomic
def change_published_status(modeladmin, request, queryset):
    unpublish = queryset.filter(is_published=True)
    unpublish_pks = tuple(unpublish.values_list('pk', flat=True))
    publish = queryset.filter(is_published=False)
    publish_pks = tuple(publish.values_list('pk', flat=True))
    unpublish.filter(pk__in=unpublish_pks).update(is_published=False)
    publish.filter(pk__in=publish_pks).update(is_published=True)
    msg = []
    if publish_pks:
        msg.append("Published {count!s} {name!s}".format(
            count=len(publish_pks), name=modeladmin.model._meta.verbose_name_plural))
    if unpublish_pks:
        msg.append("Unpublished {count!s} {name!s}".format(
            count=len(unpublish_pks), name=modeladmin.model._meta.verbose_name_plural))
    msg = ", ".join(msg)
    messages.success(request=request, message=msg)
change_published_status.short_description = "Toggle published"


class MenuItemAdmin(TreeAdmin):
    list_display = ('title', 'uri', 'menu_slug', 'is_published')
    list_display_links = ('title',)
    search_fields = ('title', 'menu_slug', 'uri')
    readonly_fields = ('menu_slug', 'created', 'modified')
    change_list_template = 'admin/menuhin/menuitem/tree_change_list.html'
    actions = [change_published_status]
    form = MenuItemTreeForm
    fieldsets = [
        (None, {
            'fields': ('title', 'uri', 'is_published'),
        }),
        ('metadata', {
            'fields': ('menu_slug',),
        }),
        ('location', {
            'classes': (),
            'fields': ('_position', '_ref_node_id'),
        }),
    ]

    def get_urls(self):
        from django.conf.urls import url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            return update_wrapper(wrapper, view)

        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        import_url = url(regex=r'^import/$',
                         view=wrap(self.import_view),
                         name='%s_%s_import' % (app_label, model_name))

        return [import_url] + super(MenuItemAdmin, self).get_urls()

    def import_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied("Cannot add new menu items")

        app_label = self.model._meta.app_label
        if hasattr(self.model._meta, 'model_name'):
            model_name = self.model._meta.model_name
        else:
            model_name = self.model._meta.module_name

        if request.method == 'POST':
            items = registry.update()
            if items is None:
                self.message_user(request, "No items imported",
                                  level=messages.ERROR)
            else:
                msg = "Imported {count} successfully".format(
                            count=len(items))
                self.message_user(request, msg, level=messages.SUCCESS)
            return redirect(admin_urlname(self.model._meta, 'changelist'))
        else:
            items = registry.items_to_update()

        templates = (
            "admin/{0}/{1}/import.html".format(app_label, model_name),
            "admin/{0}/import.html".format(app_label)
        )
        context = {
            'items': tuple(items),
            'app_label': self.model._meta.app_label,
            'opts': self.model._meta,
            'title': _('Import %s') % force_text(self.model._meta.verbose_name_plural),
            'change': False,
            'add': True,
            'is_popup': False,
            'save_as': False,
            'has_delete_permission': False,
            'has_add_permission': False,
            'has_change_permission': False,
        }
        return TemplateResponse(request, templates, context,
                                current_app=self.admin_site.name)
admin.site.register(MenuItem, MenuItemAdmin)
