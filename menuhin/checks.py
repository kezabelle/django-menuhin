# -*- coding: utf-8 -*-
from django.contrib.admin.checks import ModelAdminChecks
from django.core import checks
from django.template import TemplateDoesNotExist
from django.template.loader import get_template


def assert_treebeard_templates(cls, model):
    from django.conf import settings
    errors = []
    if 'treebeard' not in settings.INSTALLED_APPS:
        errors.append(checks.Warning(
            "`treebeard` should be in your INSTALLED_APPS so that "
            "it's templates may be discovered", hint=None, obj=cls,
            id='menuhin.W1'))
    try:
        get_template("admin/tree_change_list.html")
    except TemplateDoesNotExist:
        errors.append(checks.Error(
            "template `admin/tree_change_list.html` was not found by any of "
            "your TEMPLATE_LOADERS",
            hint="put `treebeard` into INSTALLED_APPS",
            obj=cls, id='menuhin.E1',
        ))
    return errors


class MenuhinAdminChecks(ModelAdminChecks):
    def check(self, cls, model, **kwargs):
        checks = super(MenuhinAdminChecks, self).check(cls, model, **kwargs)
        checks.extend(assert_treebeard_templates(cls, model))
        return checks
