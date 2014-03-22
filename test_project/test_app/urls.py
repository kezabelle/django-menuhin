# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from .views import (test_menus, test_login_required, test_user_passes_test,
                    test_permission_required, test_staff_required, TestCBV)


urlpatterns = patterns('',
                       url(regex=r'^$',
                           view=test_menus,
                           name='test_menus'),

                       url(regex=r'^login_required/$',
                           view=test_login_required,
                           name='test_login_required'),

                       url(regex=r'^user_passes_test/$',
                           view=test_user_passes_test,
                           name='test_user_passes_test'),

                       url(regex=r'^permission_required/$',
                           view=test_permission_required,
                           name='test_permission_required'),

                       url(regex=r'^staff_required/$',
                           view=test_staff_required,
                           name='test_staff_required'),

                       url(regex=r'^cbv/$',
                           view=TestCBV.as_view(),
                           name='test_cbv'),
                       )
