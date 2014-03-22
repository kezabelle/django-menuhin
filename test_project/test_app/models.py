from django.contrib import admin
from django.core.urlresolvers import reverse
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.auth.models import User
from menuhin.models import URI
from menuhin.models import MenuItemGroup
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


class UserMenu(MenuItemGroup):
    model = User

    def get_urls(self):
        for x in self.model.objects.all().iterator():
            yield URI(path='/user/{0}'.format(x.username), title='Yay!')
        yield URI(path=reverse('test_login_required'),
                  title='login required')
        yield URI(path=reverse('test_user_passes_test'),
                  title='user passes test')
        yield URI(path=reverse('test_permission_required'),
                  title='permission required')
        yield URI(path=reverse('test_staff_required'),
                  title='staff required')
        yield URI(path=reverse('test_cbv'),
                  title='class based view with decorator')


class AdminMenu(MenuItemGroup):
    def get_urls(self):
        for model, madmin in admin.site._registry.items():
            yield URI(path=reverse(admin_urlname(model._meta, "changelist")),
                      title=force_text(model._meta.verbose_name_plural))
