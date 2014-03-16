==============
django-menuhin
==============

Another menu & breadcrumb application for `Django`_, with support for
syncing all links from Python, and allowing website admins to customise
the trees.

Is it usable?
-------------

Maybe. You should try it.


What's the idea?
----------------

I want to be able to declare menus in Python, but have them be flexible
enough to allow for changes to come via client-input data (eg: users)

The idea in brief::

    from menuhin.models import MenuItemGroup, URI

    class MyMenu(MenuItemGroup):
        def get_urls(self):
            for i in xrange(1, 10):
                yield URI(title=i, url='/example/%d/' % i)

That's it.

Discovery of menus is done by configuring a ``MENUHIN_MENU_HANDLERS`` setting,
emulating the form of Django's ``MIDDLEWARE_CLASSES``::

  MENUHIN_MENU_HANDLERS = (
    'myapp.mymenus.MyMenu',
  )

These Python classes may then be used by the Django admin, or the bundled
management command, to **import** the URL + Title into a tree hierarchy
provided by `django-treebeard`_.


Keeping menu classes in sync
----------------------------

To keep the python-written URIs up to date, the following are available:

* a management command, ``python manage.py update_menus``

  * It accepts ``--site=N`` to target only a specific Django ``SITE_ID``
  * It accepts ``--dry-run`` where no inserts will be done. Most useful
    with ``--verbosity=2``

* The Django admin ``Menus`` tree view exposes a new **Import** page,
  where one of the ``MENUHIN_MENU_HANDLERS`` may be selected, along
  with a ``Site`` to apply it to.
* a **Post Save** signal handler (``menuhin.listeners.create_menu_url``)
  to create a new ``MenuItem`` when the given instance is first created,
  as long as the model has a ``get_absolute_url``, and optionally, a
  ``get_menu_title`` or ``get_title`` method
* a **Pre Save** signal handler (``menuhin.listeners.update_old_url``)
  to update ``MenuItem`` instances should the original model's
  ``get_absolute_url`` change, to keep the URL correct.
* a **Pre Delete** signal handler (``menuhin.listeners.unpublish_on_delete``)
  for quietly removing menu items which represent URLs that can no longer
  exist because they've been deleted.


Getting relations
-----------------

There is a middleware, ``menuhin.middleware.RequestTreeMiddleware`` which
puts the following **lazy** attributes onto ``request``:

* ``request.menuitem`` - the ``MenuItem`` for the current request, or ``None``
  if no suitable match was found.
* ``request.ancestors`` - any ``MenuItem`` instances further up the tree,
  from ``request.menuitem`` based on the arrangement (in the admin, usually)
* ``request.descendants`` - all ``MenuItem`` instances below this one.
* ``request.siblings`` - all ``MenuItem`` instances adjacent to this one in
  the tree. Includes itself, so there will always be one sibling, I think.
* ``request.children`` - only ``MenuItem`` instances one level directly
  below this one.

If you don't want the middleware, there are context processors too:

* ``menuhin.context_processors.request_ancestors`` exposes the context
  variable ``MENUHIN_ANCESTORS``, which should contain the same as the
  middleware's ``request.ancestors``
* ``menuhin.context_processors.request_descendants`` exposes the context
  variable ``MENUHIN_DESCENDANTS``, which should contain the same as the
  middleware's ``request.descendants``


Dynamic titles
--------------

If a stored title has ``{{ xyz }}`` in it when rendered by the template tags,
the title will be parsed as if it were a Django template, using the
``MenuItem`` field attributes as kwargs, plus ``request`` if it was in the
parent context.

If the stored title has ``{x}`` in it, and didn't have ``{{ abc }}`` in it,
the title is parsed using the `Python string formatting DSL`_, such that
every field attribute of the ``MenuItem`` is given as a kwarg, as is
``request`` if it was in the parent context.

Thus, both of the following are valid titles:

* ``hello, {{ request.user|default:'anonymous' }}``
* ``hello, {request.user}``


Usage in templates
------------------

A brief overview of the template tags available:

show_breadcrumbs
^^^^^^^^^^^^^^^^

Requires a single argument, which is used to look up the ``MenuItem`` in
question::

  {% load menus %}
  {% show_breadcrumbs request.path %}
  {% show_breadcrumbs "my-slug" %}
  {% show_breadcrumbs 4 %}

* If the argument is all digits, it is presumed to be the **primary key**,
  and is used as-is to fetch the ``MenuItem`` in question, along with
  it's ancestors.
* If the argument is a valid slug (that is, contains no characters invalid
  for a ``SlugField``) it is treated as such, and is used in combination
  with the current ``Site`` (based on the ``SITE_ID``) to fetch the
  ``MenuItem`` in question, along with it's ancestors.
* If the argument is neither of the above, it is presumed to be a URL,
  and so is looked up by ``MenuItem`` path and the current ``Site`` (based
  on the ``SITE_ID``) to fetch the ``MenuItem`` in question, along with
  it's ancestors.

The default template for showing breadcrumbs (
``menuhin/show_breadcrumbs.html``) puts a whole bunch of CSS classes
and data-* attributes on the HTML elements, so you can customise heavily.
You can change the template used by providing a second argument pointing
at your chosen file::

  {% load menus %}
  {% show_breadcrumbs request.path "a/b/c.html" %}

The tag may also be used to promote a new context variable, which sidesteps the
rendering process and ignores the template::

  {% load menus %}
  {% show_breadcrumbs request.path as breadcrumb_data %}
  {% for node in breadcrumb_data.ancestor_nodes %}
  {{ node }}
  {% endfor %}


show_menu
^^^^^^^^^

Takes a string representing a ``MenuItem`` slug and optionally a depth to
descend to from the discovered ``MenuItem`` to display a tree::

  {% load menus %}
  {% show_menu "default" 10 %}

Finds the ``MenuItem`` for the current ``Site`` which matches that slug,
and outputs up to ten levels below it.

The default template (``menuhin/show_menu.html``) for showing the menu puts
a whole bunch of CSS classes and data-* attributes on the HTML elements, so
you can customise heavily without needing to override it, though that is
possible too::

  {% load menus %}
  {% show_menu "xyz" 100 "x/y/z.html" %}

Like the ``show_breadcrumbs`` tag, ``show_menu`` may be used to create a new
context variable containing the data otherwise provided to the included
template::

  {% load menus %}
  {% show_menu ... as outvar %}
  {{ outvar.menu_root }}
  {% for x in outvar.menu_nodes %}
  {{ x }}
  {% endfor %}


Sitemaps
--------

There's a ``menuhin.sitemaps.MenuItemSitemap`` which will output all
**published** menu items for the current **site** (as set by the ``SITE_ID``)

Assuming your menus cover most/all of your pages, it's an efficient way to
provide the sitemap, though it can be improved by using
`django-static-sitemaps`_.

Published ``MenuItem`` instances in the sitemap get a lower priority the
deeper into the tree they are, and the change frequency is dynamically set
depending on how recently the ``MenuItem`` was last changed.

Unfinished bits
---------------

* Test coverage is not 100%.
* Doesn't take querystrings into account yet.

Requirements
------------

* `Django`_
* `django-treebeard`_
* `django-model-utils`_
* `django-classy-tags`_

License
-------

``django-menuhin`` is available under the terms of the
Simplified BSD License (alternatively known as the FreeBSD License, or
the 2-clause License). See the ``LICENSE`` file in the source
distribution for a complete copy.


.. _Django: https://djangoproject.com/
.. _django-treebeard: https://github.com/tabo/django-treebeard/
.. _Python string formatting DSL: http://docs.python.org/2/library/string.html#format-examples
.. _django-static-sitemaps: https://github.com/xaralis/django-static-sitemaps
.. _django-model-utils: https://github.com/carljm/django-model-utils
.. _django-classy-tags: https://github.com/ojii/django-classy-tags
