# -*- coding: utf-8 -*-
from .models import MenuItem
from django.template.loader import render_to_string


def menuhin_breadcrumbs(request):
    """
    How breadcrumbs will be rendered on the site, to a depth of grandchild.
    """
    node0 = MenuItem(title='default', site_id=1,
                     uri='/', depth=0)
    node0.clean()
    node1 = MenuItem(title='child', site_id=1,
                     uri='/child/', depth=1)
    node1.clean()
    node2 = MenuItem(title='grandchild', site_id=1,
                     uri='/grandchild/', depth=2)
    node2.clean()
    return render_to_string('menuhin/show_breadcrumbs.html', {
        'ancestor_nodes': [node0, node1],
        'menu_node': node2,
    })
