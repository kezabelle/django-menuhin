from itertools import chain
from django.contrib.sites.models import Site
from celery.decorators import shared_task
from .utils import update_all_urls, _collect_menus
from .models import MenuItem


@shared_task
def update_urls_for_all_sites():
    """
    Run this one periodically, to asynchronously update all the URLs
    for all sites
    """
    for site in Site.objects.only('pk').iterator():
        url_iterables = [x.instance.get_urls() for x in _collect_menus()]
        all_urls = frozenset(chain(*url_iterables))
        update_urls_for_site.delay(site_pk=site, url_set=all_urls)


@shared_task
def update_urls_for_site(site_pk, url_set):
    results = update_all_urls(model=MenuItem, possible_urls=url_set,
                              site_id=site_pk)
    if results is not None:
        results = tuple(results)
    return results
