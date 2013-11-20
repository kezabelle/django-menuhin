# -*- coding: utf-8 -*-
from django.shortcuts import get_object_or_404
from django.utils.http import base36_to_int
from django.views.generic import RedirectView
from menuhin.models import Node
from menuhin.signals import shorturl_redirect


class MenuShortUrlRedirect(RedirectView):
    model = Node
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
        endpoint = get_object_or_404(self.model, pk=base36_to_int(b36_int))
        shorturl_redirect.send(sender=self.model, instance=endpoint,
                               user=self.request.user)
        return endpoint.url
