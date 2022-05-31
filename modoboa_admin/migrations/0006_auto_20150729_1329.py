# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modoboa_admin', '0005_set_full_address'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='alias',
            options={'ordering': ['address'], 'permissions': (('view_aliases', 'View aliases'),)},
        ),
        migrations.RemoveField(
            model_name='alias',
            name='mboxes',
        ),
        migrations.RemoveField(
            model_name='alias',
            name='extmboxes',
        ),
        migrations.RemoveField(
            model_name='alias',
            name='aliases',
        ),
    ]
