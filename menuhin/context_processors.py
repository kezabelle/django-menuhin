
from .models import MenuItem
from .utils import LengthLazyObject, get_relations_for_request


def request_ancestors(request):
    if hasattr(request, 'ancestors'):
        ancestors = request.ancestors
    else:
        def lazy_ancestor_func():
            return get_relations_for_request(
                model=MenuItem, request=request,
                relation='get_ancestors').relations
        ancestors = LengthLazyObject(lazy_ancestor_func)
    return {
        'MENUHIN_ANCESTORS': ancestors
    }


def request_descendants(request):
    if hasattr(request, 'descendants'):
        descendants = request.descendants
    else:
        def lazy_descendants_func():
            return get_relations_for_request(
                model=MenuItem, request=request,
                relation='get_descendants').relations
        descendants = LengthLazyObject(lazy_descendants_func)
    return {
        'MENUHIN_DESCENDANTS': descendants
    }
