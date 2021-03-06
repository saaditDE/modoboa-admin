"""Forms related to aliases management."""

from collections import OrderedDict

from django import forms
from django.http import QueryDict
from django.utils.translation import ugettext as _, ugettext_lazy

from modoboa.lib.email_utils import split_mailbox
from modoboa.lib.form_utils import (
    DynamicForm
)

from ..models import Domain, Alias
from .base import EmailField


class AliasForm(forms.ModelForm, DynamicForm):

    """A form to create/modify an alias."""

    address = EmailField(
        label=ugettext_lazy("Email address"),
        help_text=ugettext_lazy(
            "The alias address. To create a catchall alias, just enter the "
            "domain name (@domain.tld)."
        ),
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    recipients = EmailField(
        label=ugettext_lazy("Recipients"), required=False,
        help_text=ugettext_lazy(
            "Addresses this alias will point to. Indicate only one address "
            "per input, press ENTER to add a new input."
        ),
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = Alias
        fields = ("address", "enabled", )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(AliasForm, self).__init__(*args, **kwargs)
        self.fields = OrderedDict(
            (key, self.fields[key]) for key in
            ['address', 'recipients', 'enabled']
        )

        if len(args) and isinstance(args[0], QueryDict):
            if "instance" in kwargs:
                if not kwargs["instance"].domain.enabled:
                    del self.fields["enabled"]
            self._load_from_qdict(args[0], "recipients", forms.EmailField)
        elif "instance" in kwargs:
            alias = kwargs["instance"]
            if not alias.domain.enabled:
                self.fields["enabled"].widget.attrs["disabled"] = "disabled"
            cpt = 1
            for rcpt in alias.aliasrecipient_set.filter(alias__internal=False):
                name = "recipients_%d" % cpt
                self._create_field(forms.EmailField, name, rcpt.address, 2)
                cpt += 1

    def clean_address(self):
        """Check if address points to a local domain."""
        localpart, domname = split_mailbox(self.cleaned_data["address"])
        try:
            domain = Domain.objects.get(name=domname)
        except Domain.DoesNotExist:
            raise forms.ValidationError(_("Domain does not exist"))
        if not self.user.can_access(domain):
            raise forms.ValidationError(
                _("You don't have access to this domain")
            )
        return self.cleaned_data["address"].lower()

    def clean(self):
        """Check it there is at least one recipient."""
        super(AliasForm, self).clean()
        for field, value in self.cleaned_data.items():
            if field.startswith("recipients") and value:
                return self.cleaned_data
        self.add_error("recipients", _("No recipient defined"))
        return self.cleaned_data

    def save(self, commit=True):
        """Custom save method."""
        alias = super(AliasForm, self).save(commit=False)
        local_part, domname = split_mailbox(self.cleaned_data["address"])
        alias.domain = Domain.objects.get(name=domname)
        if commit:
            alias.save()
            address_list = [
                value for field, value in self.cleaned_data.items()
                if field.startswith("recipients") and value
            ]
            alias.set_recipients(address_list)
        return alias
