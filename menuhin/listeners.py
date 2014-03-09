try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text
from django.conf import settings
from .models import MenuItem, URI
from .utils import update_all_urls


def create_menu_url(sender, instance, created, **kwargs):
    """
    post_save listener to create a MenuItem the first time an object is saved.
    Requires a get_absolute_url implementation existing on the class instance.
    """
    if not created:
        return None

    if not hasattr(instance, 'get_absolute_url'):
        return None

    if hasattr(instance, 'get_menu_title'):
        title = instance.get_menu_title()
    elif hasattr(instance, 'get_title'):
        title = instance.get_title()
    elif hasattr(instance, 'title'):
        title = instance.title
    else:
        title = force_text(instance)

    uri = URI(path=instance.get_absolute_url(), title=title)
    return update_all_urls(model=MenuItem, urls=(uri,))


def update_old_url(sender, instance, created, **kwargs):
    """
    pre_save listener to update a URL if it moves. Requires an existing
    instance and a get_absolute_url implementation.
    """
    if created:
        return None

    if not hasattr(instance, 'get_absolute_url'):
        return None

    new_url = instance.get_absolute_url()
    old_instance = instance.__class__.objects.get(pk=instance.pk)
    old_url = old_instance.get_absolute_url()
    if old_url == new_url:
        return None

    filter_by = {'uri__iexact': old_url, 'site_id': settings.SITE_ID}
    update_on = {'uri': new_url}
    return MenuItem.objects.filter(**filter_by).update(**update_on)