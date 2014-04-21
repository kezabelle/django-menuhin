import logging
try:
    from django.contrib.contenttypes.admin import GenericInlineModelAdmin
    from django.forms.utils import ErrorList
except ImportError:  # < 1.7 ... pragma: no cover
    from django.contrib.contenttypes.generic import GenericInlineModelAdmin
    from django.forms.util import ErrorList
from django.forms import Media
from django.db.models.options import Options
from .models import MenuItem


logger = logging.getLogger(__name__)

class MenuItemFakeForm(object):
    """
    Used by MenuItemFakeFormSet
    """
    media = Media()
    base_fields = ()

    @property
    def _meta(self):
        opts = Options(meta=None)
        opts.model = MenuItem
        return opts


class MenuItemFakeFormSet(object):
    """
    A minimal representation of a FormSet as called by the Django inline
    admin code.
    """
    initial_forms = []
    extra_forms = []
    media = Media()
    form = MenuItemFakeForm
    empty_form = MenuItemFakeForm()
    errors = {}

    # used for constructing change messages
    new_objects = []
    changed_objects = []
    deleted_objects = []

    @classmethod
    def get_default_prefix(cls):
        return 'fake_menuitem_formset'

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self

    def get_queryset(self, *args, **kwargs):
        return self.kwargs.get('queryset', ())

    def is_valid(self, *args, **kwargs):
        return True

    def save(self, *args, **kwargs):
        return True

    def non_form_errors(self):
        return ErrorList()

    @property
    def _pk_field(self):
        class FakePK(object):
            name = 'pk'
        return FakePK()


class MenuItemFakeInline(GenericInlineModelAdmin):
    """
    GenericInlineModelAdmin allows for the easiest faking, unfortunately
    """
    model = MenuItem
    template = 'admin/menuhin/menuitem/fake_inline.html'
    max_num = 1
    extra = 0

    @classmethod
    def validate(*args, **kwargs):
        return None

    def get_formset(self, request, obj=None, **kwargs):
        self.formset = MenuItemFakeFormSet()
        self.formset.tree_lookup = None
        if obj is not None and hasattr(obj, 'get_absolute_url'):
            url = obj.get_absolute_url()
            lookup = {'uri__iexact': url}
            try:
                menu_root = MenuItem.objects.get(**lookup)
            except MenuItem.DoesNotExist:
                pass
            else:
                self.formset.tree_lookup = menu_root
        return self.formset
