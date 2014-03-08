import logging
from collections import namedtuple
from operator import or_

try:
    from importlib import import_module
except ImportError:  # pragma: no cover
    from django.utils.importlib import import_module

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils.text import slugify
from django.contrib.sites.models import Site
from .signals import default_for_site_created, default_for_site_needed
from django.conf import settings


logger = logging.getLogger(__name__)


class RequestRelations(namedtuple('RequestRelations', ('relations', 'obj',
                       'requested', 'path'))):
    def has_relations(self):
        return len(self.relations) > 0

    def found_instance(self):
        return self.obj is not None

    def __contains__(self, thing):
        return thing in self.relations

    def __gt__(self, other):
        other = other.strip('/')
        return self.path.startswith(other) and len(other) > len(self.path)

    def __lt__(self, other):
        other = other.strip('/')
        return other.startswith(self.path) and len(self.path) < len(other)

    def __bool__(self):
        return self.has_relations() and self.found_instance()

    __nonzero__ = __bool__


def get_relations_for_request(model, request, relation):
    path = request.path
    sentinel_error = RequestRelations(relations=model.objects.none(),
                                      obj=None, requested=relation, path=path)

    if hasattr(request, 'menuitem') and request.menuitem is not None:
        item = request.menuitem
    elif hasattr(request, 'menuitem') and request.menuitem is None:
        # using the middleware, but we couldn't find a good match.
        return sentinel_error
    else:
        # not using the middleware
        item = get_menuitem_or_none(model, request.path)

    # yeah, we can't do is not None here, because while NoneType may be
    # what item yields, it is potentially a SimpleLazyObject, for which the
    # identity check doesn't work.
    if not item:
        return sentinel_error

    attr = getattr(item, relation)
    while callable(attr):
        attr = attr()
    return RequestRelations(relations=attr.select_related('site'),
                            obj=item, requested=relation,
                            path=path)


DefaultForSite = namedtuple('DefaultForSite', ('obj', 'created'))


def ensure_default_for_site(model, site_id=None):
    if site_id is None:
        site_id = Site.objects.get_current()
    kwargs = {'menu_slug': 'default', 'site_id': site_id}
    try:
        obj = model.objects.get(**kwargs)
        created = False
    except model.DoesNotExist:
        default_for_site_needed.send(sender=ensure_default_for_site,
                                     site=site_id)
        kwargs.update({
            'title': 'Default root for site {0}'.format(site_id),
            'uri': '/',
        })
        obj = model.add_root(**kwargs)
        obj = None
        created = True
        default_for_site_created.send(sender=ensure_default_for_site,
                                      site=site_id, instance=obj)
    return DefaultForSite(obj=obj, created=created)


def get_menuitem_or_none(model, uri):
    lookup = {'site': Site.objects.get_current(),
              'uri__iexact': uri,
              'is_published': True}
    try:
        return model.objects.select_related('site').filter(**lookup)[:1][0]
    except IndexError:
        # multiple things can exist with the same URI, so we ask for the first,
        # best match, which may not exist, but won't raise DoesNotExist.
        return None


CollectedMenu = namedtuple('CollectedMenu', ('path', 'instance', 'name'))


def _collect_menus():
    MENUHIN_MENU_HANDLERS = getattr(settings, 'MENUHIN_MENU_HANDLERS', None)
    if MENUHIN_MENU_HANDLERS is None and settings.DEBUG:
        raise ImproperlyConfigured("MENUHIN_MENU_HANDLERS not found in "
                                   "your settings module")

    # The following is stolen verbatim from Django's basehandler.
    # It basically serves to put the classes into a dictionary, letting useful
    # exception messages occur when stuff goes wrong.
    for menu_handler_path in MENUHIN_MENU_HANDLERS:
        try:
            dot = menu_handler_path.rindex('.')
        except ValueError:
            raise ImproperlyConfigured("%s isn't a valid path to a menu handler" % menu_handler_path)
        handler_module, handler_cls = menu_handler_path[:dot], menu_handler_path[dot+1:]
        try:
            mod = import_module(handler_module)
        except ImportError as e:
            raise ImproperlyConfigured('Error importing menu handler %s: "%s"' % (handler_module, e))
        try:
            final_menu_handler = getattr(mod, handler_cls)
        except AttributeError:
            raise ImproperlyConfigured('Menu handler module "%s" does not define a "%s" class' % (handler_module, handler_cls))

        menu_itself = final_menu_handler()
        yield CollectedMenu(path=menu_handler_path, instance=menu_itself,
                            name=menu_itself.title)


def change_published_status(modeladmin, request, queryset):
    unpublish = queryset.filter(is_published=True)
    unpublish_pks = tuple(unpublish.values_list('pk', flat=True))
    publish = queryset.filter(is_published=False)
    publish_pks = tuple(publish.values_list('pk', flat=True))
    unpublish.filter(pk__in=unpublish_pks).update(is_published=False)
    publish.filter(pk__in=publish_pks).update(is_published=True)
change_published_status.short_description = "Toggle published"


# MissingURI = namedtuple('MissingURI', ('uri',))

def find_missing(model, urls, site_id=None):
    if site_id is None:
        site_id = Site.objects.get_current()

    paths = reduce(or_, (Q(uri__iexact=x.path) for x in urls))
    url_count = len(paths)
    if url_count == 0:
        return None
    existing = frozenset(
        model.objects.filter(paths).filter(site_id=site_id)
        .values_list('uri', flat=True))
    found_count = len(existing)
    if found_count < url_count:
        return (x for x in urls if x.path not in existing)
    return None


#: instance is a Menu model object, uri is a URI instance.
MenuItemURI = namedtuple('MenuItemURI', ('instance', 'uri'))


def add_urls(model, urls, site_id=None):
    if site_id is None:
        site_id = Site.objects.get_current()
    for url in urls:
        instance = model.add_root(uri=url.path, is_published=False,
                                  title=url.title, site_id=site_id,
                                  menu_slug=set_menu_slug(url.path))
        yield MenuItemURI(instance=instance, uri=url)


def update_all_urls(model, possible_urls, site_id=None):
    missing_urls = find_missing(model, urls=possible_urls)
    if missing_urls is not None:
        return add_urls(model, urls=tuple(missing_urls))
    return None


def set_menu_slug(uri, model=None):
    path, split, qs = uri.partition('?')
    menu_slug = slugify(force_text(path.replace('/', ' ')))
    return menu_slug[:100]
