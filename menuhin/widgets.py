# -*- coding: utf-8 -*-
from django.db.models import BLANK_CHOICE_DASH
from django.forms import Select
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from menuhin.models import MenuItem


class MenuItemSelect(Select):
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = ''
        value = force_text(value)
        widget_attrs = self.build_attrs(attrs, name=name)
        options = MenuItem.get_published_annotated_list()
        return render_to_string('menuhin/widget.html', {
            'widget_attrs': widget_attrs,
            'options': options,
            'value': value,
            'empty_label': BLANK_CHOICE_DASH[0][1]
        })
