try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text
from django.contrib.sites.models import Site
from .models import MenuItem, URI
from .utils import update_all_urls, get_title


def create_menu_url(sender, instance, created, **kwargs):
    """
    post_save listener to create a MenuItem the first time an object is saved.
    Requires a get_absolute_url implementation existing on the class instance.
    """
    if not created:
        return None

    if not hasattr(instance, 'get_absolute_url'):
        return None

    title = get_title(instance)
    abs_url = instance.get_absolute_url()
    uri = URI(path=abs_url, title=title)
    return update_all_urls(model=MenuItem, possible_urls=(uri,))


def update_old_url(sender, instance, raw, using, **kwargs):
    """
    pre_save listener to update a URL if it moves. Requires an existing
    instance and a get_absolute_url implementation.
    """
    if not instance.pk:
        return None

    if not hasattr(instance, 'get_absolute_url'):
        return None

    new_url = instance.get_absolute_url()
    old_instance = instance.__class__.objects.using(using).get(pk=instance.pk)
    old_url = old_instance.get_absolute_url()
    if old_url == new_url:
        return None

    filter_by = {'uri__iexact': old_url, 'site': Site.objects.get_current()}
    update_on = {'uri': new_url}
    return MenuItem.objects.using(using).filter(**filter_by).update(
        **update_on)


def unpublish_on_delete(sender, instance, **kwargs):
    """
    pre_delete signal to unpublish given menu items.
    """
    if not hasattr(instance, 'get_absolute_url'):
        return None
    old_url = instance.get_absolute_url()
    filter_by = {'uri__iexact': old_url, 'site': Site.objects.get_current()}
    return MenuItem.objects.filter(**filter_by).update(is_published=False)
