# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from datetime import datetime
import logging
import swapper
from django.contrib.sitemaps import Sitemap

logger = logging.getLogger(__name__)


class MenuItemSitemap(Sitemap):
    @property
    def model(self):
        return swapper.load_model('menuhin', 'MenuItem')

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
        return remove_depth

0
