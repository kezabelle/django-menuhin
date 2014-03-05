# -*- coding: utf-8 -*-
from django.shortcuts import get_object_or_404
from django.utils.http import base36_to_int
from django.views.generic import RedirectView
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from menuhin.models import MenuItem
from menuhin.signals import shorturl_redirect


def _redirect_implementation(request, model, b36_encoded_pk):
    """
    Signal sender once a model instance has been established.

    :param request: the incoming request to redirect
    :type request: WSGIRequest
    :param b36_int: base36 encoded primary key.
    :type b36_int: string
    :param model: The Django Model class to lookup by.
    :type model: Django Model class.
    :return: the URL to forward to.
    :rtype: string
    """
    endpoint = get_object_or_404(model, pk=base36_to_int(b36_encoded_pk))
    shorturl_redirect.send(sender=model, instance=endpoint, user=request.user)
    return endpoint.url


class MenuShortUrlRedirect(RedirectView):
    model = MenuItem
    permanent = False
    http_method_names = ['get', 'head']

    def get_redirect_url(self, b36_int):
        """
        Allows for anything in a menu to redirect from a short URL to a long
        canonical URL, with signals for catching the redirection.

        The app itself does not do any listening to the signal, but it exists
        as a hook for others.

        :param b36_int: base36 encoded primary key.
        :type b36_int: string
        :return: the URL to forward to.
        :rtype: string
        """
        return _redirect_implementation(request=self.request,
                                        model=self.model,
                                        b36_encoded_pk=b36_int)


@require_http_methods(['GET', 'HEAD'])
def menu_shorturl_redirect(request, b36_int, model=MenuItem):
    """
    Allows for anything in a menu to redirect from a short URL to a long
    canonical URL, with signals for catching the redirection.

    The app itself does not do any listening to the signal, but it exists
    as a hook for others.

    :param request: the incoming request to redirect
    :type request: WSGIRequest
    :param b36_int: base36 encoded primary key.
    :type b36_int: string
    :param model: The Django Model class to lookup by.
    :type model: Django Model class.
    :return: the URL to forward to.
    :rtype: HttpResponseRedirect
    """
    url = _redirect_implementation(request=request, model=model,
                                   b36_encoded_pk=b36_int)
    return redirect(url, permanent=False)
