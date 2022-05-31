# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modoboa_admin', '0002_rename_content_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='domain',
            name='type',
            field=models.CharField(default=b'domain', max_length=20),
            preserve_default=True,
        ),
    ]
