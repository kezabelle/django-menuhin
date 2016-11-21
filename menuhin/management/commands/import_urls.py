# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django.core.management.base import BaseCommand, CommandError
from django.utils.six.moves import input
from menuhin.models import registry


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--noinput',
            action='store_false', dest='interactive', default=True,
            help="Do NOT prompt the user for input of any kind.")

    def set_options(self, **options):
        self.interactive = options['interactive']

    def handle(self, *args, **options):
        self.set_options(**options)
        items = tuple(registry.items_to_update())
        if not items:
            return None
        for menu, urls in items:
            self.stdout.write(self.style.SQL_COLTYPE('Menu: {0}'.format(menu)))
            for index, url in enumerate(urls, start=1):
                self.stdout.write(self.style.SQL_KEYWORD("\tURL: {0}".format(url.path)))
                if index == 10:
                    count = len(urls) - index
                    self.stdout.write(self.style.SQL_KEYWORD("\t + {0} more ...".format(count)))
                    break
        message = "Would you like to import the URLs listed?\n"
        if self.interactive and input(''.join(message)) not in ("yes", "y", "YES", "Y"):
            raise CommandError("Importing URLs cancelled")
        results = registry.update()
        if results is not None:
            self.stdout.write(self.style.MIGRATE_HEADING(
                "Imported {0} URLs successfully".format(len(results))))
        else:
            raise CommandError("Failed to import the URLs")
