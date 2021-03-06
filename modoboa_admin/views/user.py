
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _

import reversion

from modoboa.lib.web_utils import (
    render_to_json_response, _render_to_string
)

from ..forms import ForwardForm
from ..lib import needs_mailbox
from ..models import Alias


@login_required
@needs_mailbox()
@reversion.create_revision()
def forward(request, tplname="modoboa_admin/forward.html"):
    mb = request.user.mailbox
    al = Alias.objects.filter(address=mb.full_address, internal=False).first()
    if request.method == "POST":
        form = ForwardForm(request.POST)
        if form.is_valid():
            if al is None:
                al = Alias.objects.create(
                    address=mb.full_address, domain=mb.domain,
                    enabled=mb.user.is_active)
            recipients = form.get_recipients()
            if form.cleaned_data["keepcopies"]:
                recipients.append(mb.full_address)
            al.set_recipients(recipients)
            al.post_create(request.user)
            return render_to_json_response(_("Forward updated"))

        return render_to_json_response(
            {'form_errors': form.errors}, status=400
        )

    form = ForwardForm()
    if al is not None:
        form.fields["dest"].initial = al.recipients
        if al.aliasrecipient_set.filter(mailbox=mb.id).exists():
            form.fields["keepcopies"].initial = True
    return render_to_json_response({
        "content": _render_to_string(request, tplname, {
            "form": form
        })
    })
