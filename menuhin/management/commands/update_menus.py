from itertools import chain
from optparse import make_option
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site
from menuhin.models import MenuItem
from menuhin.utils import (_collect_menus, find_missing,
                           ensure_default_for_site, add_urls)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput',
                    action='store_false',
                    dest='interactive',
                    default=True,
                    help='Tells Django to NOT prompt the user for input '
                    'of any kind.'),

        make_option('--site',
                    action='store',
                    dest='site_id',
                    help='Tells Django to NOT prompt the user for input '
                    'of any kind.'),


        make_option('--dry-run',
                    action='store_true',
                    dest='dry_run',
                    default=False,
                    help='Tells Django to NOT prompt the user for input '
                    'of any kind.'),
    )

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity'))
        dry_run = options.get('dry_run')
        site_id = int(options.get('site_id') or settings.SITE_ID)

        if not Site.objects.filter(pk=site_id).exists():
            if verbosity > 0:
                self.stdout.write(self.style.HTTP_BAD_REQUEST("That site ID "
                                  "doesn't exist in the database."))
            return

        if dry_run and verbosity > 0:
            self.stdout.write(self.style.HTTP_BAD_REQUEST("This is a "
                              "dry-run, nothing new will be installed "
                              "into the database"))

        if not dry_run:
            ensure_default_for_site(model=MenuItem, site_id=site_id)
        url_iterables = [x.instance.get_urls() for x in _collect_menus()]
        all_urls = frozenset(chain(*url_iterables))

        if verbosity > 1:
            self.stdout.write(self.style.HTTP_REDIRECT("The following URLs "
                              "have been automatically discovered and will "
                              "be installed if not already in the database"))
            for possible_insert in all_urls:
                self.stdout.write(self.style.HTTP_NOT_FOUND(
                                  possible_insert.path))

        the_missing = find_missing(model=MenuItem, urls=all_urls,
                                   site_id=site_id)

        # no missing things, so fail early.
        if the_missing is None:
            if verbosity > 0:
                self.stdout.write(self.style.HTTP_REDIRECT("No URLs need "
                                  "to be added, yay!"))
                return

        actually_missing = frozenset(the_missing)

        # fail early as there is nothing to consider
        if len(actually_missing) == 0:
            if verbosity > 0:
                self.stdout.write(self.style.HTTP_REDIRECT("No URLs need "
                                  "to be added, yay!"))
            return
        else:
            # print wtf is going to happen
            if verbosity > 0:
                self.stdout.write(self.style.HTTP_REDIRECT("The following "
                                  "URLs are missing and will be "
                                  "installed."))
                for missing in actually_missing:
                    self.stdout.write(self.style.HTTP_NOT_FOUND(
                                      missing.path))
            # possibly do inserts
            if not dry_run:
                responses = add_urls(model=MenuItem, urls=actually_missing,
                                     site_id=site_id)
            else:
                responses = actually_missing

            if responses is not None:
                responses = tuple(responses)
            if verbosity > 0 and responses is not None:
                count = len(responses)
                self.stdout.write(self.style.HTTP_REDIRECT("{0} URLs have "
                                  "been added".format(count)))
            return
