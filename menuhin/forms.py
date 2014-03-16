from django.forms import Form
from django.forms.fields import TypedChoiceField
from django.forms.models import ModelChoiceField
from django.forms.widgets import TextInput
from django.db.models import BLANK_CHOICE_DASH
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from treebeard.forms import MoveNodeForm
try:
    from django.utils.six import text_type
except ImportError:  # pragma: no cover
    text_type = unicode
from .utils import _collect_menus, update_all_urls
from .models import MenuItem


class MenuItemTreeForm(MoveNodeForm):
    def __init__(self, *args, **kwargs):
        super(MenuItemTreeForm, self).__init__(*args, **kwargs)
        if 'site' in self.fields:
            self.fields['site'].initial = settings.SITE_ID

        if 'uri' in self.fields:
            self.fields['uri'].widget = TextInput(
                attrs={'required': 'required', 'class': 'vLargeTextField'})

    def save(self, commit=True):
        has_slug = bool(self.instance.menu_slug)
        slug_in_cleaned_data = self.cleaned_data.get('menu_slug', False)
        if has_slug and not slug_in_cleaned_data:
            self.cleaned_data['menu_slug'] = self.instance.menu_slug
        return super(MenuItemTreeForm, self).save(commit=commit)


class ImportMenusForm(Form):
    site = ModelChoiceField(queryset=Site.objects.none(), required=True,
                            label=_("Site"), help_text=_(
                                "The site to import the selected menu into"))
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
        if 'site' in self.fields:
            self.fields['site'].queryset = Site.objects.all()
            self.fields['site'].initial = settings.SITE_ID

        if 'klass' in self.fields:
            self.fields['klass'].choices = (BLANK_CHOICE_DASH +
                                            list(self._menu_class_choices()))

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
