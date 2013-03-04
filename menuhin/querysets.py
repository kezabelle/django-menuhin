# -*- coding: utf-8 -*-
from helpfulfields.querysets import ChangeTrackingQuerySet, PublishingQuerySet


class MenuQuerySet(ChangeTrackingQuerySet, PublishingQuerySet):
    pass
