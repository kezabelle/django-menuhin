# -*- coding: utf-8 -*-
import logging
from functools import update_wrapper
from treebeard.admin import TreeAdmin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
try:
    from django.utils.encoding import force_text
except ImportError:  # pragma: no cover
    from django.utils.encoding import force_unicode as force_text
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from menuhin.models import MenuItem
from .forms import MenuItemTreeForm, ImportMenusForm
from .utils import (ensure_default_for_site, change_published_status,
                    find_missing)

logger = logging.getLogger(__name__)


class MenuItemAdmin(TreeAdmin):
    list_display = ('title', 'uri', 'site', 'menu_slug', 'is_published')
    list_display_links = ('title',)
    # list_filter = ('site', 'modified')
    search_fields = ('title', 'menu_slug', 'uri')
    readonly_fields = ('menu_slug', 'created', 'modified')
    form = MenuItemTreeForm
    actions = [change_published_status]
    fieldsets = [
        ('dates', {
            'classes': ('collapse',),
            'fields': ('created', 'modified'),
        }),
        (None, {
            'fields': ('title', 'uri', 'is_published'),
        }),
        ('metadata', {
            'fields': ('menu_slug', 'site'),
        }),
        ('location', {
            'classes': (),
            'fields': ('_position', '_ref_node_id'),
        }),
    ]
    change_list_template = 'admin/menuhin/menuitem/tree_change_list.html'

    @property
    def media(self):
        obj, created = ensure_default_for_site(model=self.model)
        return super(MenuItemAdmin, self).media

    def get_urls(self):
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name
        import_url = url(regex=r'^import/$',
                         view=wrap(self.import_view),
                         name='%s_%s_import' % info)
        return patterns('', import_url) + super(MenuItemAdmin, self).get_urls()

    def import_view(self, request):
        form = ImportMenusForm(data=request.POST or None, files=None)

        app_label = self.model._meta.app_label
        if hasattr(self.model._meta, 'model_name'):
            model_name = self.model._meta.model_name
        else:
            model_name = self.model._meta.module_name

        do_ajax = request.method == 'POST' and request.is_ajax()
        do_post = request.method == 'POST' and not request.is_ajax()

        if do_ajax:
            if form.is_valid():
                urls = form._menu_class_instance_from_cleaned_data().get_urls()
                missing = find_missing(model=self.model, urls=tuple(urls))
                if missing is not None:
                    missing = tuple(missing)
                templates = (
                    "admin/{0}/{1}/missing_ajax.html".format(app_label,
                                                             model_name),
                    "admin/{0}/missing_ajax.html".format(app_label)
                )
                status_code = 200
                if missing is None or len(missing) == 0:
                    status_code = 202
                return TemplateResponse(request, templates,
                                        {'missing': missing},
                                        status=status_code,
                                        current_app=self.admin_site.name)
            else:
                return HttpResponseForbidden("Invalid form data")

        if do_post and form.is_valid():
            result = form.save()
            self.message_user(request, "Imported successfully")
            return redirect(admin_urlname(self.model._meta, 'changelist'))

        templates = (
            "admin/{0}/{1}/import_form.html".format(app_label, model_name),
            "admin/{0}/import_form.html".format(app_label)
        )
        context = {
            'form': form,
            # 'app_label': app_label,
            'opts': self.model._meta,
            'title':_('Import %s') % force_text(
                self.model._meta.verbose_name_plural),
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
