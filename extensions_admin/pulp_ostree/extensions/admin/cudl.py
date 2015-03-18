from gettext import gettext as _
from urlparse import urlparse

from okaara import parsers as okaara_parsers
from pulp.client import arg_utils
from pulp.client.commands.repo.cudl import CreateAndConfigureRepositoryCommand
from pulp.client.commands.repo.cudl import ListRepositoriesCommand
from pulp.client.commands.repo.cudl import UpdateRepositoryCommand
from pulp.client.commands.repo.importer_config import ImporterConfigMixin
from pulp.common.constants import REPO_NOTE_TYPE_KEY
from pulp.client.extensions.extensions import PulpCliOption

from pulp_ostree.common import constants


description = \
    _('if "true", on each successful sync the repository will automatically be '
      'published; if "false" content will only be available after manually publishing '
      'the repository; defaults to "true"')

OPT_AUTO_PUBLISH = PulpCliOption(
    '--auto-publish', description, required=False, parse_func=okaara_parsers.parse_boolean)

description = _('determines the path component of the published url; defaults to the repo ID')
OPT_RELATIVE_PATH = PulpCliOption('--relative-path', description, required=False)

DESC_FEED = _('URL for the upstream ostree repo')

description = _("a branch to sync from the upstream repository. This option "
                "may be specified multiple times")

OPT_BRANCH = PulpCliOption(
    '--branch', description, aliases=['-b'], required=False, allow_multiple=True)

IMPORTER_CONFIGURATION_FLAGS = dict(
    include_ssl=False,
    include_sync=True,
    include_unit_policy=False,
    include_proxy=False,
    include_throttling=False
)


class CreateOSTreeRepositoryCommand(CreateAndConfigureRepositoryCommand, ImporterConfigMixin):
    default_notes = {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_OSTREE}
    IMPORTER_TYPE_ID = constants.WEB_IMPORTER_TYPE_ID

    def __init__(self, context):
        CreateAndConfigureRepositoryCommand.__init__(self, context)
        ImporterConfigMixin.__init__(self, **IMPORTER_CONFIGURATION_FLAGS)
        self.add_option(OPT_AUTO_PUBLISH)
        self.add_option(OPT_RELATIVE_PATH)
        self.add_option(OPT_BRANCH)
        self.options_bundle.opt_feed.description = DESC_FEED

    def _describe_distributors(self, user_input):
        """
        Subclasses should override this to provide whatever option parsing
        is needed to create distributor configs.

        :param user_input:  dictionary of data passed in by okaara
        :type  user_input:  dict

        :return:    list of dict containing distributor_type_id,
                    repo_plugin_config, auto_publish, and distributor_id (the same
                    that would be passed to the RepoDistributorAPI.create call).
        :rtype:     list of dict
        """
        relative_path = user_input.get(OPT_RELATIVE_PATH.keyword)
        auto_publish = user_input.get(OPT_AUTO_PUBLISH.keyword, True)

        # relative path derived using the path component of the feed url when not specified
        if not relative_path:
            feed_url = user_input.get(self.options_bundle.opt_feed.keyword)
            if feed_url:
                url = urlparse(feed_url)
                relative_path = url.path

        config = {
            constants.DISTRIBUTOR_CONFIG_KEY_RELATIVE_PATH: relative_path
        }

        data = [
            dict(distributor_type_id=constants.WEB_DISTRIBUTOR_TYPE_ID,
                 distributor_config=config,
                 auto_publish=auto_publish,
                 distributor_id=constants.CLI_WEB_DISTRIBUTOR_ID),
        ]

        return data

    def _parse_importer_config(self, user_input):
        """
        Subclasses should override this to provide whatever option parsing
        is needed to create an importer config.

        :param user_input:  dictionary of data passed in by okaara
        :type  user_input:  dict

        :return:    importer config
        :rtype:     dict
        """
        config = self.parse_user_input(user_input)
        value = user_input.pop(OPT_BRANCH.keyword, None)
        if value:
            config[constants.IMPORTER_CONFIG_KEY_BRANCHES] = value
        return config


class UpdateOSTreeRepositoryCommand(UpdateRepositoryCommand, ImporterConfigMixin):

    def __init__(self, context):
        UpdateRepositoryCommand.__init__(self, context)
        ImporterConfigMixin.__init__(self, **IMPORTER_CONFIGURATION_FLAGS)
        self.add_option(OPT_AUTO_PUBLISH)
        self.add_option(OPT_BRANCH)
        self.options_bundle.opt_feed.description = DESC_FEED

    def run(self, **kwargs):
        arg_utils.convert_removed_options(kwargs)

        importer_config = self.parse_user_input(kwargs)

        if OPT_BRANCH.keyword in kwargs:
            value = kwargs.pop(OPT_BRANCH.keyword, None)
            if value == ['']:
                # clear out the specified branches
                value = None
            importer_config[constants.IMPORTER_CONFIG_KEY_BRANCHES] = value

        # Remove importer specific keys
        for key in importer_config.keys():
            kwargs.pop(key, None)

        if importer_config:
            kwargs['importer_config'] = importer_config

        # Update distributor configuration
        web_config = {}

        value = kwargs.pop(OPT_AUTO_PUBLISH.keyword, None)
        if value is not None:
            web_config['auto_publish'] = value

        if web_config:
            kwargs['distributor_configs'] = {}
            kwargs['distributor_configs'][constants.CLI_WEB_DISTRIBUTOR_ID] = web_config

        super(UpdateOSTreeRepositoryCommand, self).run(**kwargs)


class ListOSTreeRepositoriesCommand(ListRepositoriesCommand):

    def __init__(self, context):
        repos_title = _('OSTree Repositories')
        super(ListOSTreeRepositoriesCommand, self).__init__(context, repos_title=repos_title)

        # Both get_repositories and get_other_repositories will act on the full
        # list of repositories. Lazy cache the data here since both will be
        # called in succession, saving the round trip to the server.
        self.all_repos_cache = None

    def get_repositories(self, query_params, **kwargs):
        """
        Get a list of all the ostree repositories that match the specified query params

        :param query_params: query parameters for refining the list of repositories
        :type query_params: dict
        :param kwargs: Any additional parameters passed into the repo list command
        :type kwargs: dict
        :return: List of ostree repositories
        :rtype: list of dict
        """
        all_repos = self._all_repos(query_params, **kwargs)

        ostree_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if REPO_NOTE_TYPE_KEY in notes \
                    and notes[REPO_NOTE_TYPE_KEY] == constants.REPO_NOTE_OSTREE:
                ostree_repos.append(repo)

        return ostree_repos

    def get_other_repositories(self, query_params, **kwargs):
        """
         Get a list of all the non ostree repositories that match the specified query params

        :param query_params: query parameters for refining the list of repositories
        :type query_params: dict
        :param kwargs: Any additional parameters passed into the repo list command
        :type kwargs: dict
        :return: List of non repositories
        :rtype: list of dict
        """

        all_repos = self._all_repos(query_params, **kwargs)

        non_ostree_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if notes.get(REPO_NOTE_TYPE_KEY, None) != constants.REPO_NOTE_OSTREE:
                non_ostree_repos.append(repo)

        return non_ostree_repos

    def _all_repos(self, query_params, **kwargs):
        """
        get all the repositories associated with a repo that match a set of query parameters

        :param query_params: query parameters for refining the list of repositories
        :type query_params: dict
        :param kwargs: Any additional parameters passed into the repo list command
        :type kwargs: dict
        :return: list of repositories
        :rtype: list of dict
        """

        # This is safe from any issues with concurrency due to how the CLI works
        if self.all_repos_cache is None:
            self.all_repos_cache = self.context.server.repo.repositories(query_params).response_body

        return self.all_repos_cache
