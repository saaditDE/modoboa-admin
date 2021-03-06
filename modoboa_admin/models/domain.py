"""Models related to domains management."""

from django.contrib.contenttypes import generic
from django.db import models
from django.db.models.manager import Manager
from django.utils.translation import ugettext as _, ugettext_lazy

import reversion

from .base import AdminObject
from modoboa.core.models import User, ObjectAccess
from modoboa.lib import events, parameters
from modoboa.lib.exceptions import BadRequest, Conflict


class DomainManager(Manager):

    def get_for_admin(self, admin):
        """Return the domains belonging to this admin

        The result is a ``QuerySet`` object, so this function can be used
        to fill ``ModelChoiceField`` objects.
        """
        if admin.is_superuser:
            return self.get_query_set()
        return self.get_query_set().filter(owners__user=admin)


class Domain(AdminObject):

    """Mail domain."""

    name = models.CharField(ugettext_lazy('name'), max_length=100, unique=True,
                            help_text=ugettext_lazy("The domain name"))
    quota = models.IntegerField()
    enabled = models.BooleanField(
        ugettext_lazy('enabled'),
        help_text=ugettext_lazy("Check to activate this domain"),
        default=True
    )
    owners = generic.GenericRelation(ObjectAccess)
    type = models.CharField(default="domain", max_length=20)

    objects = DomainManager()

    class Meta:
        permissions = (
            ("view_domain", "View domain"),
            ("view_domains", "View domains"),
        )
        ordering = ["name"]
        app_label = "modoboa_admin"
        db_table = "admin_domain"

    @property
    def domainalias_count(self):
        return self.domainalias_set.count()

    @property
    def mailbox_count(self):
        return self.mailbox_set.count()

    @property
    def mbalias_count(self):
        return self.alias_set.count()

    @property
    def identities_count(self):
        """Total number of identities in this domain."""
        return self.mailbox_set.count() + self.alias_set.count()

    @property
    def tags(self):
        if self.type == "domain":
            return [{"name": "domain", "label": _("Domain"), "type": "dom"}]
        return events.raiseQueryEvent("GetTagsForDomain", self)

    @property
    def admins(self):
        """Return the domain administrators of this domain

        :return: a list of User objects
        """
        return [oa.user for oa in self.owners.filter(user__is_superuser=False)]

    @property
    def aliases(self):
        return self.domainalias_set

    def add_admin(self, account):
        """Add a new administrator for this domain

        :param User account: the administrotor to add
        """
        from modoboa.lib.permissions import grant_access_to_object
        grant_access_to_object(account, self)
        for mb in self.mailbox_set.all():
            if mb.user.has_perm("modoboa_admin.add_domain"):
                continue
            grant_access_to_object(account, mb)
            grant_access_to_object(account, mb.user)
        for al in self.alias_set.all():
            grant_access_to_object(account, al)

    def remove_admin(self, account):
        """Remove an administrator of this domain.

        :param User account: administrator to remove
        """
        from modoboa.lib.permissions import \
            ungrant_access_to_object, get_object_owner

        if get_object_owner(self) == account:
            events.raiseEvent('DomainOwnershipRemoved', account, self)
        ungrant_access_to_object(self, account)
        for mb in self.mailbox_set.all():
            if mb.user.has_perm("modoboa_admin.add_domain"):
                continue
            ungrant_access_to_object(mb, account)
            ungrant_access_to_object(mb.user, account)
        for al in self.alias_set.all():
            ungrant_access_to_object(al, account)

    def delete(self, fromuser, keepdir=False):
        """Custom delete method.
        """
        from modoboa.lib.permissions import ungrant_access_to_objects
        from .mailbox import Quota

        if self.domainalias_set.count():
            events.raiseEvent("DomainAliasDeleted", self.domainalias_set.all())
            ungrant_access_to_objects(self.domainalias_set.all())
        if self.alias_set.count():
            events.raiseEvent("MailboxAliasDeleted", self.alias_set.all())
            ungrant_access_to_objects(self.alias_set.all())
        if parameters.get_admin("AUTO_ACCOUNT_REMOVAL") == "yes":
            for account in User.objects.filter(mailbox__domain__name=self.name):
                account.delete(fromuser, keepdir)
        elif self.mailbox_set.count():
            Quota.objects.filter(username__contains='@%s' % self.name).delete()
            events.raiseEvent("MailboxDeleted", self.mailbox_set.all())
            ungrant_access_to_objects(self.mailbox_set.all())
        super(Domain, self).delete()

    def __str__(self):
        return self.name

    def from_csv(self, user, row):
        """Create a new domain from a CSV entry.

        The expected fields order is the following::

          "domain", name, quota, enabled

        :param ``core.User`` user: user creating the domain
        :param str row: a list containing domain's definition
        """
        if len(row) < 4:
            raise BadRequest(_("Invalid line"))
        self.name = row[1].strip()
        if Domain.objects.filter(name=self.name).exists():
            raise Conflict
        try:
            self.quota = int(row[2].strip())
        except ValueError:
            raise BadRequest(
                _("Invalid quota value for domain '%s'") % self.name)
        self.enabled = (row[3].strip() in ["True", "1", "yes", "y"])
        self.save(creator=user)

    def to_csv(self, csvwriter):
        csvwriter.writerow(["domain", self.name, self.quota, self.enabled])
        for dalias in self.domainalias_set.all():
            dalias.to_csv(csvwriter)

    def post_create(self, creator):
        """Post creation actions.

        :param ``User`` creator: user whos created this domain
        """
        super(Domain, self).post_create(creator)
        for domalias in self.domainalias_set.all():
            domalias.post_create(creator)

reversion.register(Domain)
