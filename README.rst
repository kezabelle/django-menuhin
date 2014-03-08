==============
django-menuhin
==============

Another menu & breadcrumb application for `Django`_.

Is it usable?
-------------

Nope, not entirely. I keep re-writing it.


What's the idea?
----------------

I wanted to be able to declare menus in Python, but have them be flexible
enough to allow for changes to come via client-input data.

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

Unfinished bits
---------------

* No tests. There is a `test_project` though.
* Lazy middleware needs improvement.
* Lazy context processors need improvement.
* Doesn't take querystrings into account yet.
* Allowing the title to have ``{x}`` (python formatting) and ``{{ x }}``
  (`Django`_ template formatting) isn't yet done in the templates.

License
-------

``django-menuhin`` is available under the terms of the
Simplified BSD License (alternatively known as the FreeBSD License, or
the 2-clause License). See the ``LICENSE`` file in the source
distribution for a complete copy.


.. _Django: https://djangoproject.com/
.. _django-treebeard: https://github.com/tabo/django-treebeard/
