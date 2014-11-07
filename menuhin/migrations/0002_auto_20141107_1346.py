# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
        ('menuhin', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='menuitem',
            name='_original_content_id',
            field=models.CharField(db_index=True, default=None, max_length=255, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='menuitem',
            name='_original_content_type',
            field=models.ForeignKey(related_name='+', default=None, to='contenttypes.ContentType', null=True),
            preserve_default=True,
        ),
    ]
