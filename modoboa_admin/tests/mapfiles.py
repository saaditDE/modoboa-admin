"""Test map files generation."""

from django.test import TestCase

from modoboa.lib.test_utils import MapFilesTestCaseMixin


class MapFilesTestCase(MapFilesTestCaseMixin, TestCase):

    """Test case for modoboa_admin."""

    extension = "modoboa_admin"

    MAP_FILES = [
        "sql-domains.cf", "sql-domain-aliases.cf", "sql-aliases.cf",
        "sql-maintain.cf"
    ]
