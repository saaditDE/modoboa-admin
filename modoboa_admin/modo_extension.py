"""Registration with Modoboa takes place here."""

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _, ugettext_lazy

from modoboa.core.extensions import ModoExtension, exts_pool
from modoboa.lib import parameters, events
from modoboa.lib.email_utils import split_mailbox
from modoboa.lib.exceptions import PermDeniedException, BadRequest, Conflict

from .models import (
    Domain, DomainAlias, Mailbox, Alias
)


ADMIN_EVENTS = [
    "DomainCreated",
    "DomainModified",
    "DomainDeleted",
    "DomainOwnershipRemoved",
    "GetTagsForDomain",
    "ExtraDomainMenuEntries",
    "ExtraDomainFilters",
    "ExtraDomainQsetFilters",
    "ExtraDomainTypes",
    "ExtraDomainWizardSteps",
    "GetDomainModifyLink",
    "CheckDomainName",

    "DomainAliasCreated",
    "DomainAliasDeleted",

    "MailboxCreated",
    "MailboxDeleted",
    "MailboxModified",

    "MailboxAliasCreated",
    "MailboxAliasDeleted",

    "ExtraDomainForm",
    "FillDomainInstances",

    "ExtraAccountForm",
    "CheckExtraAccountForm",
    "FillAccountInstances",

    "ExtraDomainImportHelp",
    "ImportObject"
]

PERMISSIONS = {
    "DomainAdmins": [
        ["core", "user", "add_user"],
        ["core", "user", "change_user"],
        ["core", "user", "delete_user"],
        ["modoboa_admin", "domain", "view_domains"],
        ["modoboa_admin", "domain", "view_domain"],
        ["modoboa_admin", "mailbox", "add_mailbox"],
        ["modoboa_admin", "mailbox", "change_mailbox"],
        ["modoboa_admin", "mailbox", "delete_mailbox"],
        ["modoboa_admin", "alias", "add_alias"],
        ["modoboa_admin", "alias", "change_alias"],
        ["modoboa_admin", "alias", "delete_alias"],
        ["modoboa_admin", "mailbox", "view_mailboxes"],
        ["modoboa_admin", "alias", "view_aliases"],
        ["modoboa_admin", "domainalias", "view_domaliases"],
        ["modoboa_admin", "domainalias", "add_domainalias"],
        ["modoboa_admin", "domainalias", "change_domainalias"],
        ["modoboa_admin", "domainalias", "delete_domainalias"]
    ]
}


class AdminConsole(ModoExtension):
    name = "modoboa_admin"
    label = ugettext_lazy("Administration console")
    version = "1.1.2"
    description = ugettext_lazy(
        "Web based console to manage domains, accounts and aliases"
    )
    always_active = True
    url = "admin"

    def load(self):
        from .app_settings import AdminParametersForm

        parameters.register(
            AdminParametersForm, ugettext_lazy("Administration"))
        events.declare(ADMIN_EVENTS)

exts_pool.register_extension(AdminConsole)


@events.observe("GetExtraRoles")
def extra_roles(user, account):
    """Return new roles."""
    filters = events.raiseQueryEvent(
        "UserCanSetRole", user, "DomainAdmins", account
    )
    if user.has_perm("modoboa_admin.add_domain") and \
            (not filters or True in filters):
        return [("DomainAdmins", _("Domain administrator"))]
    return []


@events.observe("GetExtraRolePermissions")
def extra_permissions(rolename):
    """Return extra permissions for :kw:`rolename`."""
    return PERMISSIONS.get(rolename, [])


@events.observe("ExtraUprefsRoutes")
def extra_routes():
    from django.conf.urls import url
    return [
        url(r'^user/forward/',
            'modoboa_admin.views.user.forward',
            name="user_forward"),
    ]


@events.observe("AdminMenuDisplay")
def admin_menu(target, user):
    if target != "top_menu":
        return []
    entries = []
    if user.has_perm("modoboa_admin.view_domains"):
        entries += [
            {"name": "domains",
             "url": reverse("modoboa_admin:domain_list"),
             "label": _("Domains")}
        ]
    conditions = (
        user.has_perm("core.add_user"),
        user.has_perm("modoboa_admin.add_alias")
    )
    if any(conditions):
        entries += [
            {"name": "identities",
             "url": reverse("modoboa_admin:identity_list"),
             "label": _("Identities")},
        ]
    return entries


@events.observe("UserMenuDisplay")
def user_menu(target, user):
    if target != "uprefs_menu":
        return []
    if not hasattr(user, "mailbox"):
        return []
    return [
        {"name": "forward",
         "class": "ajaxnav",
         "url": "forward/",
         "label": ugettext_lazy("Forward")}
    ]


@events.observe("RoleChanged")
def grant_access_to_all_objects(user, role):
    from django.contrib.contenttypes.models import ContentType
    from modoboa.lib.permissions import grant_access_to_objects
    from modoboa.core.models import User

    if role != "SuperAdmins":
        return
    grant_access_to_objects(
        user, User.objects.all(),
        ContentType.objects.get_for_model(User)
    )
    grant_access_to_objects(
        user, Domain.objects.all(),
        ContentType.objects.get_for_model(Domain)
    )
    grant_access_to_objects(
        user, DomainAlias.objects.all(),
        ContentType.objects.get_for_model(DomainAlias)
    )
    grant_access_to_objects(
        user, Mailbox.objects.all(),
        ContentType.objects.get_for_model(Mailbox)
    )
    grant_access_to_objects(
        user, Alias.objects.all(),
        ContentType.objects.get_for_model(Alias)
    )


@events.observe("AccountExported")
def export_admin_domains(admin):
    result = [admin.mailbox.quota] \
        if hasattr(admin, "mailbox") else [""]
    if admin.group != "DomainAdmins":
        return result
    return result + [dom.name for dom in Domain.objects.get_for_admin(admin)]


@events.observe("AccountImported")
def import_account_mailbox(user, account, row):
    """Handle extra fields when an account is imported.

    Expected fields:

    email address; quota; [domain; ...]

    :param User user: user importing the account
    :param User account: account being imported
    :param list rom: list of fields (strings)
    """
    account.email = row[0].strip()
    if account.email:
        account.save()
        mailbox, domname = split_mailbox(account.email)
        try:
            domain = Domain.objects.get(name=domname)
        except Domain.DoesNotExist:
            raise BadRequest(
                _("Account import failed (%s): domain does not exist"
                  % account.username)
            )
        if not user.can_access(domain):
            raise PermDeniedException
        try:
            mb = Mailbox.objects.get(address=mailbox, domain=domain)
        except Mailbox.DoesNotExist:
            pass
        else:
            raise Conflict(_("Mailbox %s already exists" % account.email))
        if len(row) == 1:
            quota = None
        else:
            try:
                quota = int(row[1].strip())
            except ValueError:
                raise BadRequest(
                    _("Account import failed (%s): wrong quota value"
                      % account.username)
                )
        use_domain_quota = True if not quota else False
        mb = Mailbox(address=mailbox, domain=domain,
                     user=account, use_domain_quota=use_domain_quota)
        mb.set_quota(
            quota, override_rules=user.has_perm("modoboa_admin.change_domain")
        )
        mb.save(creator=user)
    if account.group == "DomainAdmins":
        for domname in row[2:]:
            try:
                dom = Domain.objects.get(name=domname.strip())
            except Domain.DoesNotExist:
                continue
            dom.add_admin(account)


@events.observe("AccountAutoCreated")
def account_auto_created(user):
    from modoboa.core.models import User
    from modoboa.lib.permissions import grant_access_to_object
    from .lib import check_if_domain_exists

    if parameters.get_admin("AUTO_CREATE_DOMAIN_AND_MAILBOX") == "no":
        return
    localpart, domname = split_mailbox(user.username)
    if user.group != 'SimpleUsers' and domname is None:
        return
    sadmins = User.objects.filter(is_superuser=True)
    try:
        domain = Domain.objects.get(name=domname)
    except Domain.DoesNotExist:
        label = check_if_domain_exists(
            domname, [(DomainAlias, _('domain alias'))])
        if label is not None:
            return
        domain = Domain(name=domname, enabled=True, quota=0)
        domain.save(creator=sadmins[0])
        for su in sadmins[1:]:
            grant_access_to_object(su, domain)
    try:
        mb = Mailbox.objects.get(domain=domain, address=localpart)
    except Mailbox.DoesNotExist:
        mb = Mailbox(
            address=localpart, domain=domain, user=user, use_domain_quota=True
        )
        mb.set_quota(override_rules=True)
        mb.save(creator=sadmins[0])
        for su in sadmins[1:]:
            grant_access_to_object(su, mb)


@events.observe("UserLogin")
def user_logged_in(request, username, password):
    from modoboa.lib.cryptutils import encrypt

    if hasattr(request.user, "mailbox"):
        request.session["password"] = encrypt(password)


@events.observe("AccountDeleted")
def account_deleted(account, byuser, **kwargs):
    """'AccountDeleted' listener.

    When an account is deleted, we also need to remove its mailbox (if
    any).
    """
    if not hasattr(account, "mailbox"):
        return
    mb = account.mailbox
    if not byuser.can_access(mb):
        raise PermDeniedException
    keep_mb_dir = kwargs.get("keep_mb_dir", True)
    mb.delete(keepdir=keep_mb_dir)
