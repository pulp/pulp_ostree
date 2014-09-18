from gettext import gettext as _

from pulp.plugins.distributor import Distributor

from pulp_ostree.common import constants


def entry_point():
    """
    Entry point that pulp platform uses to load the distributor
    :return: distributor class and its config
    :rtype:  Distributor, dict
    """
    return WebDistributor, {}


class WebDistributor(Distributor):

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this distributor. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this distributor. Must be unique
          across all distributors. Only letters and underscores are valid.
        * display_name - User-friendly identification of the distributor.
        * types - List of all content type IDs that may be published using this
          distributor.

        :return:    keys and values listed above
        :rtype:     dict
        """
        return {
            'id': constants.WEB_DISTRIBUTOR_TYPE_ID,
            'display_name': _('OSTree Web Distributor'),
            'types': [constants.OSTREE_TYPE_ID]
        }

    def validate_config(self, repo, config, config_conduit):
        return True, ''
