def get_bulk_data():
    from django.contrib.sites.models import Site
    site = Site.objects.get_current().pk
    return [
        {'data': {'title': '1', 'site': site, 'uri': '/', 'is_published': True}},
        {'data': {'title': '2', 'site': site, 'uri': '/a/', 'is_published': True}, 'children': [
            {'data': {'title': '21', 'site': site, 'uri': '/a/b/c/', 'is_published': True}},
            {'data': {'title': '22', 'site': site, 'uri': '/d/', 'is_published': True}},
            {'data': {'title': '23', 'site': site, 'uri': '/e', 'is_published': True}, 'children': [
                {'data': {'title': '231', 'site': site, 'uri': '/HI',
                'is_published': True}},
            ]},
            {'data': {'title': '24', 'site': site, 'uri': '/x/', 'is_published': True}},
        ]},
        {'data': {'title': '3', 'site': site, 'uri': '/sup', 'is_published': True}},
        {'data': {'title': '4', 'site': site, 'uri': '/yo', 'is_published': True}, 'children': [
            {'data': {'title': '41', 'site': site, 'uri': '/hotdog/',
            'is_published': True}},
        ]},
    ]
