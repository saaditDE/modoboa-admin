"""AppConfig for admin."""

from django.apps import AppConfig


class AdminConfig(AppConfig):

    """App configuration."""

    name = "modoboa_admin"
    verbose_name = "Modoboa admin console"

    def ready(self):
        from . import handlers
