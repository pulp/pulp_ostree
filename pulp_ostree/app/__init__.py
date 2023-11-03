from pulpcore.plugin import PulpPluginAppConfig


class PulpOstreePluginAppConfig(PulpPluginAppConfig):
    """Entry point for the ostree plugin."""

    name = "pulp_ostree.app"
    label = "ostree"
    version = "2.2.0"
    python_package_name = "pulp-ostree"
