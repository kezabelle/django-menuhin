

def request_ancestors(request):
    return {
        'MENUHIN_ANCESTORS': lazy(get_ancestors_for_request(request)),
    }

def request_descendants(request):
    return {
        'MENUHIN_DESCENDANTS': lazy(get_descendants_for_request(request)),
    }

def request_siblings(request):
    return {
        'MENUHIN_SIBLINGS': (),
    }
