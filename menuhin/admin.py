# -*- coding: utf-8 -*-
from copy import deepcopy
from django.contrib import admin
from helpfulfields.admin import changetracking_fieldset, changetracking_readonlys
from menuhin.models import Menu, menu_handlers
from menuhin.text import config_fieldset_label

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
    readonly_fields = changetracking_readonlys

    def __init__(self, *args, **kwargs):
        """Make sure that we call the menu loading as late as possible, but
        still make sure it's called before we show the admin
        """
        super(MenuAdmin, self).__init__(*args, **kwargs)
        menu_handlers.load_menus()

    def get_title(self, obj):
        return obj.title
    get_title.short_description = ''
    get_title.admin_order_field = 'title'

    def get_readonly_fields(self, request, obj=None):
        """Adds the internal slug field `title` to the non-editable fields list
        when in edit mode.

        This ensures we can still create menus via the admin, but cannot break
        any usages elsewhere on the site.
        """
        if obj:
            return ['title'] + deepcopy(self.readonly_fields)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        """ Do we have permission to delete this menu?
        We never have permission to delete a menu if it's mounted on the standard
        `menu_handler` (ugh, a global!) - it has to be unmounted (removed from
        the `MENUHIN_MENU_HANDLERS` project setting) before it can be safely removed.
        """
        if obj is not None:
            all_menus = menu_handlers.menus
            if obj.title in all_menus.keys():
                return False
        return super(MenuAdmin, self).has_delete_permission(request, obj)

admin.site.register(Menu, MenuAdmin)

#class NodeAdjacencyInline(admin.StackedInline):
##    model = Node.adjacencies.through
#    fk_name = 'ancestor'
#    extra = 0
##
#class NodeAdmin(admin.ModelAdmin):
#    list_display = ['get_title', 'get_absolute_url', 'modified']
#    inlines = [NodeAdjacencyInline]
#
#    def get_model_perms(self, request):
#        if Menu.objects.count() < 1:
#            return {}
#        return super(NodeAdmin, self).get_model_perms(request)
#admin.site.register(Node, NodeAdmin)
