def get_bulk_data():
    from django.contrib.sites.models import Site
    site = Site.objects.get_current().pk
    return [
        {'data': {'title': '1', 'site': site, 'uri': '/',
         'menu_slug': 'root', 'is_published': True}},
        {'data': {'title': '2', 'site': site, 'uri': '/a/', 'menu_slug':
         'default', 'is_published': True}, 'children': [
            {'data': {'title': '21', 'site': site, 'uri': '/a/b/c/',
             'menu_slug': 'abc', 'is_published': True}},
            {'data': {'title': '22', 'site': site, 'uri': '/d/',
             'menu_slug': 'd', 'is_published': True}},
            {'data': {'title': '23', 'site': site, 'uri': '/e',
             'menu_slug': 'e', 'is_published': True}, 'children': [
                {'data': {'title': '231', 'site': site, 'uri': '/HI',
                 'menu_slug': 'hi',
                 'is_published': True}},
            ]},
            {'data': {'title': '24', 'site': site, 'uri': '/x/',
             'menu_slug': 'x', 'is_published': True}},
        ]},
        {'data': {'title': '3', 'site': site, 'uri': '/sup',
         'menu_slug': 'sup', 'is_published': True}},
        {'data': {'title': '4', 'site': site, 'uri': '/yo', 'menu_slug': 'yo',
         'is_published': True}, 'children': [
            {'data': {'title': '41', 'site': site, 'uri': '/hotdog/',
             'menu_slug': 'hotdog', 'is_published': True}},
        ]},
    ]
