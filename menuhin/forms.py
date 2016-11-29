# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.forms import TextInput
from treebeard.forms import MoveNodeForm


class MenuItemTreeForm(MoveNodeForm):
    def __init__(self, *args, **kwargs):
        super(MenuItemTreeForm, self).__init__(*args, **kwargs)
        if 'uri' in self.fields:
            self.fields['uri'].widget = TextInput(
                attrs={'required': 'required', 'class': 'vLargeTextField'})

    def save(self, commit=True):
        has_slug = bool(self.instance.menu_slug)
        slug_in_cleaned_data = self.cleaned_data.get('menu_slug', False)
        if has_slug and not slug_in_cleaned_data:
            self.cleaned_data['menu_slug'] = self.instance.menu_slug
        return super(MenuItemTreeForm, self).save(commit=commit)

    class Meta:
        fields = ['path', 'depth', 'numchild', 'menu_slug', 'title',
'uri', 'is_published', '_position', '_ref_node_id']
