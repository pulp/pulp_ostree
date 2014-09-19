from unittest import TestCase

from mock import patch, Mock

from pulp_ostree.plugins import lib


class TestLoad(TestCase):

    def test_loading(self):
        self.assertEqual(lib.GLib, None)
        self.assertEqual(lib.Gio, None)
        self.assertEqual(lib.OSTree, None)