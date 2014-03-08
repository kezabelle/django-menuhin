import logging
from django.utils.functional import SimpleLazyObject
from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch
from .models import MenuItem
from .utils import (LengthLazyObject, get_menuitem_or_none,
                    get_relations_for_request)


logger = logging.getLogger(__name__)


class RequestTreeMiddleware(object):
    def get_ignorables(self):
        yield settings.STATIC_URL
        yield settings.MEDIA_URL
        try:
            yield reverse('admin:index')
        except NoReverseMatch:
            logger.debug("Admin is not mounted")

    def process_request(self, request):
        if request.path.startswith(tuple(self.get_ignorables())):
            logger.debug("Skipping this request")
            return None

        def lazy_menuitem():
            return get_menuitem_or_none(MenuItem, request.path)

        def lazy_ancestors_func():
            return get_relations_for_request(
                model=MenuItem, request=request,
                relation='get_ancestors').relations

        def lazy_descendants_func():
            return get_relations_for_request(
                model=MenuItem, request=request,
                relation='get_descendants').relations

        def lazy_siblings_func():
            return get_relations_for_request(
                model=MenuItem, request=request,
                relation='get_siblings').relations

        def lazy_children_func():
            return get_relations_for_request(
                model=MenuItem, request=request,
                relation='get_children').relations

        request.menuitem = SimpleLazyObject(lazy_menuitem)
        request.ancestors = LengthLazyObject(lazy_ancestors_func)
        request.descendants = LengthLazyObject(lazy_descendants_func)
        request.siblings = LengthLazyObject(lazy_siblings_func)
        request.children = LengthLazyObject(lazy_children_func)
