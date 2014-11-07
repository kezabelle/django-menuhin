import logging
from collections import namedtuple
import functools
import operator
from django.contrib.contenttypes.models import ContentType
from django.utils.html import strip_tags
from django.utils.functional import SimpleLazyObject, new_method_proxy
from django.core.urlresolvers import resolve, Resolver404

try:
    from importlib import import_module
except ImportError:  # pragma: no cover
    from django.utils.importlib import import_module

try:
    from django.utils.encoding import force_text
except ImportError:  # pragma: no cover
    from django.utils.encoding import force_unicode as force_text

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q

try:
    from django.utils.text import slugify
except ImportError:  # pragma: no cover
    from django.template.defaultfilters import slugify

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

    def __bool__(self):
        return self.has_relations() and self.found_instance()

    __nonzero__ = __bool__


class LengthLazyObject(SimpleLazyObject):
    __dir__ = new_method_proxy(dir)
    __len__ = new_method_proxy(len)
    __getitem__ = new_method_proxy(operator.getitem)
    __contains__ = new_method_proxy(operator.contains)


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
    # this should be a MenuItem queryset ...
    relations = (attr.defer('_original_content_type', '_original_content_id')
                 .select_related('site'))
    return RequestRelations(relations=relations,
                            obj=item, requested=relation,
                            path=path)


DefaultForSite = namedtuple('DefaultForSite', ('obj', 'created'))


def ensure_default_for_site(model, site_id=None):
    if site_id is None:
        site_id = Site.objects.get_current()
    kwargs = {'menu_slug': 'default', 'site': site_id}
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
        created = True
        default_for_site_created.send(sender=ensure_default_for_site,
                                      site=site_id, instance=obj)
    return DefaultForSite(obj=obj, created=created)


def get_menuitem_or_none(model, uri):
    lookup = {'site': Site.objects.get_current(),
              'uri__iexact': uri,
              'is_published': True}
    try:
        return (model.objects.select_related('site')
                .defer('_original_content_type', '_original_content_id')
                .filter(**lookup)[:1][0])
    except IndexError:
        # multiple things can exist with the same URI, so we ask for the first,
        # best match, which may not exist, but won't raise DoesNotExist.
        return None


CollectedMenu = namedtuple('CollectedMenu', ('path', 'instance', 'name'))


def _collect_menus():
    MENUHIN_MENU_HANDLERS = getattr(settings, 'MENUHIN_MENU_HANDLERS', None)
    if MENUHIN_MENU_HANDLERS is None:
        raise ImproperlyConfigured("MENUHIN_MENU_HANDLERS not found in "
                                   "your settings module")

    # The following is stolen verbatim from Django's basehandler.
    # It basically serves to put the classes into a dictionary, letting useful
    # exception messages occur when stuff goes wrong.
    for menu_handler_path in MENUHIN_MENU_HANDLERS:
        try:
            dot = menu_handler_path.rindex('.')
        except ValueError:  # pragma: no cover
            raise ImproperlyConfigured("%s isn't a valid path to a menu handler" % menu_handler_path)
        handler_module, handler_cls = menu_handler_path[:dot], menu_handler_path[dot+1:]
        try:
            mod = import_module(handler_module)
        except ImportError as e:  # pragma: no cover
            raise ImproperlyConfigured('Error importing menu handler %s: "%s"' % (handler_module, e))
        try:
            final_menu_handler = getattr(mod, handler_cls)
        except AttributeError:  # pragma: no cover
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

    url_count = len(urls)
    if url_count == 0:
        return None

    paths = functools.reduce(operator.or_,
                             (Q(uri__iexact=x.path) for x in urls))
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
        site_id = Site.objects.get_current().pk
    for url in urls:
        kwargs = {
            'uri': url.path,
            'is_published': False,
            'title': url.title,
            'site_id': site_id,
            'menu_slug': set_menu_slug(url.path)
        }
        original_obj = getattr(url, 'model_instance', None)
        if original_obj is not None:
            kwargs.update({
                '_original_content_type': ContentType.objects.get_for_model(original_obj),
                '_original_content_id': original_obj.pk
            })

        instance = model.add_root(**kwargs)
        yield MenuItemURI(instance=instance, uri=url)


def update_all_urls(model, possible_urls, site_id=None):
    missing_urls = find_missing(model, urls=possible_urls, site_id=site_id)
    if missing_urls is not None:
        missing_urls = tuple(missing_urls)
        return tuple(add_urls(model, urls=missing_urls, site_id=site_id))
    return None


def set_menu_slug(uri, model=None):
    path, split, qs = uri.partition('?')
    menu_slug = slugify(force_text(path.replace('/', ' ')))
    max_length = 100
    if model is not None:
        max_length = model._meta.get_field_by_name('menu_slug')[0].max_length
    return menu_slug[:max_length]


def get_title(instance):
    if hasattr(instance, 'get_menu_title'):
        title = instance.get_menu_title()
    elif hasattr(instance, 'get_title'):
        title = instance.get_title()
    elif hasattr(instance, 'title'):
        title = instance.title
    elif hasattr(instance, 'get_headline'):
        title = instance.get_headline()
    elif hasattr(instance, 'headline'):
        title = instance.headline
    else:
        title = instance  # rely on calling str or unicode

    title = strip_tags(force_text(title)).strip()
    if title == "":
        title = '<No title>'
    return title


def get_list_title(instance, url=None):
    """
    On the offchance you've set the list page's title on the model instance,
    then yay, we can look it up.
    """
    title = url
    if hasattr(instance, 'get_list_menu_title'):
        title = instance.get_list_menu_title(url)
    elif hasattr(instance, 'get_list_title'):
        title = instance.get_list_title(url)
    elif hasattr(instance, 'get_list_headline'):
        title = instance.get_list_headline(url)

    if title is not None:
        title = strip_tags(force_text(title)).strip()
        if title == "":
            title = url
    return title  # may be None or the URL again...


def marked_annotated_list(request, tree):
    """
    Mark up the tree objects with
    """
    current_node = None
    # first we need to find the active one, in a separate loop :|
    for tree_node, tree_info in tree:
        if request.path == tree_node.uri:
            tree_node.is_active = True
            current_node = tree_node
            logger.debug("Marked {node!r} as the current "
                         "node".format(node=tree_node))

    if current_node is None:
        logger.debug("No current node, returning tree without modifying it")
        return tree

    request_user = getattr(request, 'user', None)

    for tree_node, tree_info in tree:
        tree_node.is_descendant = tree_node.is_descendant_of(current_node)
        tree_node.is_sibling = (tree_node.is_sibling_of(current_node) and
                                tree_node != current_node)
        # there is no is_ancestor_of, so we can invert it.
        tree_node.is_ancestor = current_node.is_descendant_of(tree_node)

        # local URL, may be resolvable
        if tree_node.uri.startswith('/') and request_user is not None:
            decorators = get_resolvermatch_decorators(match_path=tree_node.uri)
            if decorators is None:
                tree_node.vary_on_user = False
                tree_node.user_passes_test = True
            else:
                passes = tuple(run_resolvermatch_decorators(
                    callables=decorators, for_user=request_user))
                if len(passes) > 0:
                    tree_node.vary_on_user = True
                    tree_node.user_passes_test = all(x.result for x in passes)
        logger.debug("After mutating toggles - {node!r}".format(node=tree_node))
    return tree


ResolvedDecorator = namedtuple('ResolvedDecorator',
                               ('resolved', 'decorator', 'path'))


def get_resolvermatch_decorators(match_path):
    try:
        match = resolve(match_path)
    except Resolver404:
        return None

    if (hasattr(match.func, '__closure__')
            and match.func.__closure__ is not None):
        return (
            ResolvedDecorator(resolved=match, decorator=x.cell_contents,
                              path=match_path)
            for x in match.func.__closure__
            if hasattr(x, 'cell_contents') and x.cell_contents
            and callable(x.cell_contents))
    return None


DecoratorResult = namedtuple('DecoratorResult', ('resolved', 'result'))


def run_resolvermatch_decorators(callables, for_user):
    for resolved, x, path in callables:
        if not hasattr(x, 'func_code'):
            continue

        var_count = len(x.func_code.co_varnames)
        first_param = x.func_code.co_varnames[0].lower()
        # consider self/cls and shift which param to look at.
        second_param = None
        if var_count > 1:
            second_param = x.func_code.co_varnames[1].lower()

        is_user_callable = (
            var_count == 1 and first_param in ('u', 'user'),
            var_count > 1 and second_param in ('u', 'user'),
        )

        if any(is_user_callable):
            yield DecoratorResult(
                resolved=resolved, result=x(for_user, *resolved.args,
                                            **resolved.kwargs))
