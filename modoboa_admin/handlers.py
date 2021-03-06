"""Django signal handlers for modoboa_admin."""

from django.db.models import signals
from django.dispatch import receiver

from . import models


@receiver(signals.post_save, sender=models.DomainAlias)
def create_alias_for_domainalias(sender, instance, **kwargs):
    """Create a dedicated alias for domain alias."""
    if not kwargs.get("created"):
        return
    alias = models.Alias.objects.create(
        address="@{}".format(instance.name), enabled=True, internal=True)
    models.AliasRecipient.objects.create(
        address="@{}".format(instance.target.name), alias=alias)


@receiver(signals.post_delete, sender=models.DomainAlias)
def remove_alias_for_domainalias(sender, instance, **kwargs):
    """Remove the alias associated to domain alias."""
    models.Alias.objects.filter(
        address="@{}".format(instance.name)).delete()


@receiver(signals.post_save, sender=models.Mailbox)
def manage_alias_for_mailbox(sender, instance, **kwargs):
    """Create or update a "self alias" for mailbox (catchall)."""
    if kwargs.get("created"):
        alias, created = models.Alias.objects.get_or_create(
            address=instance.full_address, domain=instance.domain,
            internal=True)
        models.AliasRecipient.objects.create(
            address=instance.full_address, alias=alias, r_mailbox=instance)
        return
    old_address = getattr(instance, "old_full_address", None)
    if old_address is None or old_address == instance.full_address:
        return
    alr = models.AliasRecipient.objects.select_related("alias").get(
        alias__address=old_address, address=old_address,
        r_mailbox=instance, alias__internal=True)
    alr.address = instance.full_address
    alr.save()
    alr.alias.address = instance.full_address
    alr.alias.save()


@receiver(signals.pre_delete, sender=models.Mailbox)
def mailbox_deleted_handler(sender, **kwargs):
    """``Mailbox`` pre_delete signal receiver

    In order to properly handle deletions (ie. we don't want to leave
    orphan records into the db), we define this custom receiver.

    It manually removes the mailbox from the aliases it is linked to
    and then remove all empty aliases.
    """
    from modoboa.lib import events
    from modoboa.lib.permissions import ungrant_access_to_object

    mb = kwargs['instance']
    events.raiseEvent("MailboxDeleted", mb)
    ungrant_access_to_object(mb)
    for ralias in mb.aliasrecipient_set.select_related("alias"):
        alias = ralias.alias
        ralias.delete()
        if not alias.aliasrecipient_set.exists():
            alias.delete()


@receiver(signals.post_delete, sender=models.Mailbox)
def remove_alias_for_mailbox(sender, instance, **kwargs):
    """Remove "self alias" for this mailbox."""
    models.Alias.objects.filter(
        address=instance.full_address).delete()
