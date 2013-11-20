==============
django-menuhin
==============

Another menu application for `Django`_.

Is it usable?
-------------

Nope, not entirely. There's a bunch of tests, and coverage is 100% excluding
the template tags, but it's not ready for prime time.

It's rough around the edges, both in API and functionality, but it is
inherently lazy, and attempts to be efficient where possible - the biggest
hits to the database are hopefully from the userland ``get_nodes()``
implementations.

What's the idea?
----------------

I wanted to be able to declare menus in Python, but have them be flexible
enough to allow for changes to come via client-input data.

The idea in brief::

    from menuhin.models import Menu, MenuNode

    class MyMenu(Menu):
        def get_nodes(self, request=None, parent_node=None):
            yield MenuNode(title='master', url='/master/',
                           unique_id='masternode')
            # the following are all children of the above...
            for i in xrange(1, 10):
                yield MenuNode(title=i, url='/example/%d/' % i,
                               unique_id='example_%d' % i,
                               parent_id='masternode')

        class Meta:
            proxy = True

    from menuhin.models import CustomMenuItem
    # the theory runs that this should replace the previous `master`
    CustomMenuItem.objects.create(title='replacing the masternode',
                                  url='/newmaster/',
                                  unique_id='newmasternode',
                                  position=CustomMenuItem.POSITIONS.replacing,
                                  target_id='masternode',
                                  menu_id='my-menu')

    items = list(MyMenu.menus.all())

That's it.

Anything that is a proxy of ``Menu`` is autodiscovered and usable. Individual
``MenuNode`` instances may be prepended and appended to, or replaced entirely.

``Menu`` instances expose a vaguely ``QuerySet`` like API, with
``Menu.menus.all()`` and ``Menu.menus.filter()``.

The future
----------

* A decent Admin implementation.
* Template tags that are correct.
* Further exploration of attaching menus to other menus - hopefully without
  ending up in a recursion loop.

License
-------

``django-menuhin`` is available under the terms of the
Simplified BSD License (alternatively known as the FreeBSD License, or
the 2-clause License). See the ``LICENSE`` file in the source
distribution for a complete copy.


.. _Django: https://djangoproject.com/
