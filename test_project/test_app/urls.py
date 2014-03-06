# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from .views import test_menus


urlpatterns = patterns('',
                       url(regex=r'^$',
                           view=test_menus,
                           name='test_menus'),
                       )
