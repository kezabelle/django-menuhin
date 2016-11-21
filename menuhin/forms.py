# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.forms import TypedChoiceField, Form
from django.utils.six import text_type


class ImportMenusForm(Form):
    klass = TypedChoiceField(choices=(), coerce=text_type, required=True,
                             label=_("Menu"), help_text=_(
                                 "Select a configured menu whose URLs you "
                                 "want to add to the given site."))

    def _collected_menus(self):
        return tuple(_collect_menus())

    def _menu_class_choices(self):
        return ((x.path, x.name) for x in self._collected_menus())

    def __init__(self, *args, **kwargs):
        super(ImportMenusForm, self).__init__(*args, **kwargs)
        if 'klass' in self.fields:
            choices = (BLANK_CHOICE_DASH + list(self._menu_class_choices()))
            self.fields['klass'].choices = choices
            if len(choices) <= 1:
                self.fields['klass'].widget.attrs.update({
                    'disabled': 'disabled',
                    'readonly': 'readonly'})
                self.fields['klass'].help_text = _("No menus have been "
                                                   "configured yet")

    # def clean(self):
    #     super(ImportMenusForm, self).clean()
    #     cd = self.cleaned_data
    #     menu_selected = cd.get('existing_menu', None)
    #     new_menu = cd.get('new_menu', None)
    #     if menu_selected and new_menu:
    #         msg = '{menu_label} and {new_label} may not both be selected'
    #         msg_formatted = msg.format(
    #             menu_label=self.fields['existing_menu'].label,
    #             new_label=self.fields['new_menu'].label)
    #         raise ValidationError(msg_formatted)
    #     return cd

    def _menu_class_instance_from_cleaned_data(self):
        klass = self.cleaned_data['klass']
        for menu in self._collected_menus():
            if klass == menu.path:
                return menu.instance
        raise ValueError("Menu instance went missing.")

    def save(self):
        klass = self._menu_class_instance_from_cleaned_data()
        possibilities = tuple(klass.get_urls())
        results = update_all_urls(MenuItem, possibilities)
        if results is not None:
            return tuple(results)
return None
