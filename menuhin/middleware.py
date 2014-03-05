from django.utils.functional import lazy, SimpleLazyObject
from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch
from treebeard.mp_tree import MP_NodeQuerySet
from .models import MenuItem, get_ancestors_for_request, get_descendants_for_request


class RequestTreeMiddleware(object):
    def get_ignorables(self):
        yield settings.STATIC_URL
        yield settings.MEDIA_URL
        # try:
        #     yield reverse('admin:index')
        # except NoReverseMatch:
        #     pass

    def process_request(self, request):
        if request.path.startswith(tuple(self.get_ignorables())):
            return None

        returntypes = (MP_NodeQuerySet, tuple)
        request.ancestors = lazy(
            lambda: get_ancestors_for_request(request), *returntypes)
        request.descendants = lazy(
            lambda: get_descendants_for_request(request), *returntypes)
