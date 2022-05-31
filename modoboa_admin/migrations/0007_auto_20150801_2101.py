# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modoboa_admin', '0006_auto_20150729_1329'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alias',
            name='address',
            field=models.CharField(help_text='The alias address.', max_length=254, verbose_name='address'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='alias',
            unique_together=set([('address', 'internal')]),
        ),
    ]
