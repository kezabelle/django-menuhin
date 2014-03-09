# -*- coding: utf-8 -*-
from datetime import datetime
import logging
from django.contrib.sitemaps import Sitemap
from .models import MenuItem


logger = logging.getLogger(__name__)


class MenuItemSitemap(Sitemap):
    model = MenuItem

    def items(self):
        return tuple(x[0] for x in self.model.get_published_annotated_list())

    def lastmod(self, obj):
        return obj.modified

    def changefreq(self, obj):
        datediff = datetime.today() - obj.modified
        if datediff.days < 3:
            return 'daily'
        if datediff.days <= 7:
            return 'weekly'
        return 'monthly'

    def priority(self, obj):
        """
        The farther down the rabbit hole we go, the lest important the pages,
        right?
        """
        start_priority = 1.0
        remove_amount = 0
        # only start trimming the start priority if we're more than 1 deep.
        if obj.depth > 0:
            remove_amount = float(obj.depth) / 10
        remove_amount = min(remove_amount, 0.99)
        remove_depth = start_priority - remove_amount
        logger.debug("{obj!r} has a priority of {depth!s} ({removed!s} "
                     "removed from maximum of {start!s})".format(
                         obj=obj, depth=remove_depth, removed=remove_amount,
                         start=start_priority))
        return remove_depth
