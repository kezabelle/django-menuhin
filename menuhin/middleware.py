from django.utils.functional import lazy
from .models import get_ancestors_for_request, get_descendants_for_request


class RequestTreeMiddleware(object):
    def process_request(self, request):
        # import pdb; pdb.set_trace()
        request.ancestors = get_ancestors_for_request(request)
        request.descendants = get_descendants_for_request(request)
