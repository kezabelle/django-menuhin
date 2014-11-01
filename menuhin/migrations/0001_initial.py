# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields
import menuhin.models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MenuItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(unique=True, max_length=255)),
                ('depth', models.PositiveIntegerField()),
                ('numchild', models.PositiveIntegerField(default=0)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('menu_slug', models.SlugField(help_text='an internally consistent title used to find menus.', max_length=100, verbose_name='unique title')),
                ('title', models.CharField(help_text='a meaningful description of this menu', max_length=50, verbose_name='title')),
                ('uri', models.TextField(verbose_name='URL', validators=[menuhin.models.is_valid_uri])),
                ('is_published', models.BooleanField(default=False, db_index=True)),
                ('site', models.ForeignKey(to='sites.Site')),
            ],
            options={
                'verbose_name': 'menu item',
                'verbose_name_plural': 'menus',
            },
            bases=(models.Model,),
        ),
    ]
