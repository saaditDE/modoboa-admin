# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def fill_recipients(apps, schema_editor):
    """Fill recipients from existing aliases."""
    Alias = apps.get_model("modoboa_admin", "Alias")
    AliasRecipient = apps.get_model("modoboa_admin", "AliasRecipient")
    to_create = []
    for alias in Alias.objects.select_related().all():
        for mb in alias.mboxes.all():
            address = "{}@{}".format(mb.address, mb.domain.name)
            to_create.append(AliasRecipient(
                address=address, alias=alias, r_mailbox=mb))
        for alias2 in alias.aliases.all():
            address = "{}@{}".format(alias2.address, alias2.domain.name)
            to_create.append(AliasRecipient(
                address=address, alias=alias, r_alias=alias2))
        for address in alias.extmboxes.split(","):
            if not address:
                continue
            to_create.append(AliasRecipient(
                address=address, alias=alias))
    AliasRecipient.objects.bulk_create(to_create)


def empty_recipients(apps, schema_editor):
    """Empty recipients."""
    AliasRecipient = apps.get_model("modoboa_admin", "AliasRecipient")
    AliasRecipient.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('modoboa_admin', '0003_domain_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='AliasRecipient',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.EmailField(max_length=75)),
                ('alias', models.ForeignKey(to='modoboa_admin.Alias')),
                ('r_alias', models.ForeignKey(related_name='alias_recipient_aliases', blank=True, to='modoboa_admin.Alias', null=True)),
                ('r_mailbox', models.ForeignKey(blank=True, to='modoboa_admin.Mailbox', null=True)),
            ],
            options={
                'unique_together': set([('alias', 'r_alias'), ('alias', 'r_mailbox')]),
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='alias',
            name='domain',
            field=models.ForeignKey(to='modoboa_admin.Domain', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='alias',
            name='internal',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.RunPython(fill_recipients, empty_recipients)
    ]
