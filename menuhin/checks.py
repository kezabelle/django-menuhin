# -*- coding: utf-8 -*-
from django.contrib.admin.checks import ModelAdminChecks
from django.core import checks
from django.core.checks import register
from django.template import TemplateDoesNotExist
from django.template.loader import get_template


def treebeard_in_installed_apps(cls):
    from django.conf import settings
    errors = []
    if 'treebeard' not in settings.INSTALLED_APPS:
        errors.append(checks.Warning(
            "`treebeard` should be in your INSTALLED_APPS so that "
            "it's templates may be discovered", hint=None, obj=cls.__name__,
            id='menuhin.W1'))
    return errors


def treebeard_template_found(cls):
    errors = []
    try:
        get_template("admin/tree_change_list.html")
    except TemplateDoesNotExist:
        errors.append(checks.Error(
            "template `admin/tree_change_list.html` was not found by any of "
            "your TEMPLATE_LOADERS",
            hint="put `treebeard` into INSTALLED_APPS",
            obj=cls.__name__, id='menuhin.E1',
        ))
    return errors


def treebeard_has_request_context_processor(cls):
    from django.conf import settings
    errors = []
    if 'django.core.context_processors.request' not in settings.TEMPLATE_CONTEXT_PROCESSORS:  # noqa
        errors.append(checks.Error(
            "treebeard requires the request be in the template context",
            hint="put `django.core.context_processors.request` "
                 "into TEMPLATE_CONTEXT_PROCESSORS",
            obj=cls.__name__, id='menuhin.E2',
        ))
    return errors


@register('menuhin', 'settings')
def settings_defined(app_configs):
    from django.conf import settings
    errors = []
    try:
        handlers = settings.MENUHIN_MENU_HANDLERS
    except AttributeError:
        errors.append(checks.Error(
            "You won't be able to use the `menuhin` app without setting "
            "`MENUHIN_MENU_HANDLERS`",
            hint="use dotted paths to MenuItemGroup subclasses",
            obj=__name__, id='menuhin.E2',
        ))
    else:
        if len(handlers) == 0:
            errors.append(checks.Warning(
                "You haven't defined any handlers for `menuhin`",
                hint="make the MENUHIN_MENU_HANDLERS setting a tuple of dotted "
                     "paths to MenuItemGroup subclasses.",
                obj=__name__, id='menuhin.W2',
            ))
    return errors


class MenuhinAdminChecks(ModelAdminChecks):
    def check(self, cls, model, **kwargs):
        checks = super(MenuhinAdminChecks, self).check(cls, model, **kwargs)
        checks.extend(treebeard_in_installed_apps(cls=cls))
        checks.extend(treebeard_template_found(cls=cls))
        checks.extend(treebeard_has_request_context_processor(cls=cls))
        return checks
