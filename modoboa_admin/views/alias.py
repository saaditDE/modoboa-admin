
from django.contrib.auth.decorators import (
    login_required, permission_required
)
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.shortcuts import render
from django.utils.translation import ugettext as _, ungettext

import reversion

from modoboa.lib import events
from modoboa.lib.exceptions import PermDeniedException, Conflict
from modoboa.lib.web_utils import render_to_json_response

from ..forms import AliasForm
from ..models import Alias


def _validate_alias(request, form, successmsg, callback=None):
    """Alias validation

    Common function shared between creation and modification actions.
    """
    if form.is_valid():
        try:
            alias = form.save()
        except IntegrityError:
            raise Conflict(_("Alias with this name already exists"))
        if callback:
            callback(request.user, alias)
        return render_to_json_response(successmsg)

    return render_to_json_response({'form_errors': form.errors}, status=400)


def _new_alias(request, title, action, successmsg,
               tplname="modoboa_admin/aliasform.html"):
    events.raiseEvent("CanCreate", request.user, "mailbox_aliases")
    if request.method == "POST":
        def callback(user, alias):
            alias.post_create(user)

        form = AliasForm(request.user, request.POST)
        return _validate_alias(
            request, form, successmsg, callback
        )

    ctx = {
        "title": title,
        "action": action,
        "formid": "aliasform",
        "action_label": _("Create"),
        "action_classes": "submit",
        "form": AliasForm(request.user)
    }
    return render(request, tplname, ctx)


@login_required
@permission_required("modoboa_admin.add_alias")
@reversion.create_revision()
def newdlist(request):
    return _new_alias(
        request, _("New distribution list"),
        reverse("modoboa_admin:dlist_add"),
        _("Distribution list created")
    )


@login_required
@permission_required("modoboa_admin.add_alias")
@reversion.create_revision()
def newalias(request):
    return _new_alias(
        request, _("New alias"), reverse("modoboa_admin:alias_add"),
        _("Alias created")
    )


@login_required
@permission_required("modoboa_admin.add_alias")
@reversion.create_revision()
def newforward(request):
    return _new_alias(
        request, _("New forward"), reverse("modoboa_admin:forward_add"),
        _("Forward created")
    )


@login_required
@permission_required("modoboa_admin.change_alias")
@reversion.create_revision()
def editalias(request, alid, tplname="modoboa_admin/aliasform.html"):
    alias = Alias.objects.get(pk=alid)
    if not request.user.can_access(alias):
        raise PermDeniedException
    if request.method == "POST":
        altype = alias.type
        if altype == "dlist":
            successmsg = _("Distribution list modified")
        elif altype == "forward":
            successmsg = _("Forward modified")
        else:
            successmsg = _("Alias modified")
        form = AliasForm(request.user, request.POST, instance=alias)
        return _validate_alias(request, form, successmsg)

    ctx = {
        'action': reverse("modoboa_admin:alias_change", args=[alias.id]),
        'formid': 'aliasform',
        'title': alias.address,
        'action_label': _('Update'),
        'action_classes': 'submit',
        'form': AliasForm(request.user, instance=alias)
    }
    return render(request, tplname, ctx)


@login_required
@permission_required("modoboa_admin.delete_alias")
def delalias(request):
    selection = request.GET["selection"].split(",")
    for alid in selection:
        alias = Alias.objects.get(pk=alid)
        if not request.user.can_access(alias):
            raise PermDeniedException
        if alias.type == 'dlist':
            msg = "Distribution list deleted"
            msgs = "Distribution lists deleted"
        elif alias.type == 'forward':
            msg = "Forward deleted"
            msgs = "Forwards deleted"
        else:
            msg = "Alias deleted"
            msgs = "Aliases deleted"
        alias.delete()

    msg = ungettext(msg, msgs, len(selection))
    return render_to_json_response(msg)
