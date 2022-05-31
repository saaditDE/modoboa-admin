# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def update_records(apps, schema_editor):
    """Update aliases."""
    Alias = apps.get_model("modoboa_admin", "Alias")
    AliasRecipient = apps.get_model("modoboa_admin", "AliasRecipient")
    Mailbox = apps.get_model("modoboa_admin", "Mailbox")
    DomainAlias = apps.get_model("modoboa_admin", "DomainAlias")
    ObjectDates = apps.get_model("modoboa_admin", "ObjectDates")
    for alias in Alias.objects.select_related("domain"):
        if alias.address.startswith("*"):
            alias.address = "@{}".format(alias.domain.name)
        else:
            alias.address = "{}@{}".format(alias.address, alias.domain.name)
        alias.save()
    for mbox in Mailbox.objects.select_related("domain", "user"):
        address = "{}@{}".format(mbox.address, mbox.domain.name)
        od = ObjectDates.objects.create()
        alias = Alias.objects.create(
            address=address,
            domain=mbox.domain,
            enabled=mbox.user.is_active,
            internal=True,
            dates=od
        )
        AliasRecipient.objects.create(
            address=address,
            alias=alias,
            r_mailbox=mbox
        )

    for dalias in DomainAlias.objects.select_related("target"):
        od = ObjectDates.objects.create()
        alias = Alias.objects.create(
            address="@{}".format(dalias.name), enabled=dalias.enabled,
            internal=True, dates=od
        )
        AliasRecipient.objects.create(
            address="@{}".format(dalias.target.name), alias=alias)


def restore_old_records(apps, schema_editor):
    """Restore old addresses."""
    Alias = apps.get_model("modoboa_admin", "Alias")
    for alias in Alias.objects.select_related("domain"):
        if alias.address.startswith("@"):
            alias.address = "*"
        else:
            alias.address = alias.address.replace(
                "@{}".format(alias.domain.name), "")
        alias.save()


class Migration(migrations.Migration):

    dependencies = [
        ('modoboa_admin', '0004_aliasrecipient'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='alias',
            unique_together=set(),
        ),
        migrations.RunPython(update_records, restore_old_records),
    ]
