# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import swapper
from django import template
from django.core.validators import slug_re
from django.template import Variable
from django.template.loader import render_to_string
from django.utils.encoding import force_text
# from sniplates.templatetags.sniplates import load_widgets
from sniplates.templatetags.sniplates import load_widgets, Widget, reuse, using

register  = template.Library()


def _get_lookup(path_or_menuslug, context):
    path_or_menuslug = force_text(path_or_menuslug)
    if path_or_menuslug.isdigit():
        lookup = {'pk': int(path_or_menuslug)}
    elif slug_re.search(path_or_menuslug):
        lookup = {'menu_slug': path_or_menuslug}
    elif len(path_or_menuslug) > 0:
        lookup = {'uri__iexact': path_or_menuslug}
    elif 'request' in context:
        lookup = {'uri__iexact': context['request'].path}
    elif hasattr(context, 'request'):
        lookup = {'uri__iexact': context.request.path}
    else:
        lookup = None
    return lookup


def _get_menuitem(query):
    model = swapper.load_model('menuhin', 'MenuItem')
    try:
        obj = model.objects.get(**query)
        return obj
    except model.DoesNotExist:
        return None



@register.simple_tag(takes_context=True)
def show_menu(context, menu_slug, start=0, levels=100,
              template='menuhin/show_menu3.html'):
    lookup = _get_lookup(menu_slug, context=context)
    if lookup is None:
        return ''
    menu_root = _get_menuitem(lookup)
    if menu_root is None:
        return None
    max_depth = start + levels
    # import pdb; pdb.set_trace()
    menu_items = (menu_root.__class__.get_published_annotated_list(
        parent=menu_root, min_depth=start, max_depth=max_depth))
    with context.push({'menu_nodes': menu_items, 'menu_template': template}):
        result = render_to_string(template, context=context.flatten())
    # load_widgets(context, menuhin_show_menu='menuhin/show_menu.html', _soft=True)
    #     # level3 = {'title': 'lol', 'children':[]}
    #     # level2 = {'title': 'test2', 'children': [level3]}
    #     # level1 = {'title': 'test', 'children': [level2]}
    #     # menu_items = [level1]
    # with context.push({'menu_nodes': menu_items, 'menu_template': template}):
    #     with using(context, 'menuhin_show_menu'):
    #         result = reuse(context, ['menu'], menu_nodes=menu_items)
    #     # # widget = Widget(block_name, kwargs={}, asvar=None)
    #     # context.push({'menu_nodes': menu_items})
    #     # result = widget.render(context)
    return result


@register.simple_tag(takes_context=True)
def show_breadcrumbs(context, menu_slug):
    lookup = _get_lookup(menu_slug, context=context)
    if lookup is None:
        return ''
    menu_root = _get_menuitem(lookup)
    if menu_root is None:
        return ''
    ancestors = list(menu_root.get_ancestors().filter(is_published=True))
    ancestors.append(menu_root)
    with context.push({'menu_nodes': ancestors}):
        result = render_to_string("menuhin/show_breadcrumbs.html", context=context.flatten())
    return result
