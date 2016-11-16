# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import menuhin.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='MenuItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(unique=True, max_length=255)),
                ('depth', models.PositiveIntegerField()),
                ('numchild', models.PositiveIntegerField(default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('menu_slug', models.SlugField(help_text='an internally consistent key used to find menus.', max_length=100, verbose_name='unique key')),
                ('title', models.CharField(help_text='a meaningful display title for this menu item', max_length=50, verbose_name='title')),
                ('uri', models.TextField(verbose_name='URL', validators=[menuhin.models.is_valid_uri])),
                ('is_published', models.BooleanField(default=False, db_index=True)),
                ('_original_content_id', models.CharField(default=None, max_length=255, null=True)),
                ('_original_content_type', models.ForeignKey(related_name='+', default=None, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'swappable': 'MENUHIN_MENUITEM_MODEL',
            },
        ),
    ]
