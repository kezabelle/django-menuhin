from django.utils.functional import lazy
from treebeard.mp_tree import MP_NodeQuerySet
from .models import get_ancestors_for_request, get_descendants_for_request


def request_ancestors(request):
    if hasattr(request, 'ancestors'):
        ancestors = request.ancestors
    else:
        ancestors = lazy(
            lambda: get_ancestors_for_request(request), MP_NodeQuerySet)
    return {
        'MENUHIN_ANCESTORS': ancestors
    }


def request_descendants(request):
    if hasattr(request, 'descendants'):
        descendants = request.descendants
    else:
        descendants = lazy(
            lambda: get_descendants_for_request(request), MP_NodeQuerySet)
    return {
        'MENUHIN_DESCENDANTS': descendants
    }
