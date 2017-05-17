from gettext import gettext as _
import logging
import os

from pulp_ostree.common import constants


_LOG = logging.getLogger(__name__)


def validate_config(repo, config, conduit):
    """
    Validate a configuration

    :param repo: metadata describing the repository to which the configuration applies
    :type  repo: pulp.plugins.model.Repository
    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :param conduit: A configuration conduit.
    :type conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit
    :return: tuple of (bool, str) to describe the result
    :rtype:  tuple
    """
    repo_obj = repo.repo_obj
    relative_path = get_repo_relative_path(repo_obj, config)
    error_msgs = _check_for_relative_path_conflicts(repo_obj.repo_id, relative_path, conduit)

    if error_msgs:
        return False, '\n'.join(error_msgs)

    return True, None


def get_root_publish_directory(config):
    """
    The publish directory for the ostree plugin

    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :return: The publish directory for the ostree plugin
    :rtype: str
    """
    return config.get(constants.DISTRIBUTOR_CONFIG_KEY_PUBLISH_DIRECTORY)


def get_master_publish_dir(repo, config):
    """
    Get the master publishing directory for the given repository.
    This is the directory that links/files are actually published to
    and linked from the directory published by the web server in an atomic action.

    :param repo: repository to get the master publishing directory for
    :type  repo: pulp.server.db.model.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None
    :return: master publishing directory for the given repository
    :rtype:  str
    """
    return os.path.join(get_root_publish_directory(config), 'master', repo.repo_id)


def get_web_publish_dir(repo, config):
    """
    Get the configured HTTP publication directory.
    Returns the global default if not configured.

    :param repo: repository to get relative path for
    :type  repo: pulp.server.db.model.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None

    :return: the HTTP publication directory
    :rtype:  str
    """

    return os.path.join(get_root_publish_directory(config),
                        'web',
                        get_repo_relative_path(repo, config))


def get_repo_relative_path(repo, config):
    """
    Get the configured relative path for the given repository.

    :param repo: repository to get relative path for
    :type  repo: pulp.server.db.model.Repository
    :param config: configuration instance for the repository
    :type  config: pulp.plugins.config.PluginCallConfiguration or dict
    :return: relative path for the repository
    :rtype:  str
    """
    path = config.get(constants.DISTRIBUTOR_CONFIG_KEY_RELATIVE_PATH)
    if path:
        if path.startswith('/'):
            path = path[1:]
    else:
        path = repo.repo_id
    return path


def _check_for_relative_path_conflicts(repo_id, relative_path, conduit):
    """
    Check that a relative path does not conflict with existing distributors' relative paths.

    :param repo_id: identifier of repository associated with the path to check
    :type  repo_id: basestring
    :param relative_path: relative path of the repository
    :type  relative_path: basestring
    :param conduit: A configuration conduit.
    :type conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit
    :return: A list of validation error messages.
    :rtype: list
    """
    messages = []
    distributors = conduit.get_repo_distributors_by_relative_url(relative_path, repo_id)
    for distributor in distributors:
        conflicting_repo_id = distributor['repo_id']
        conflicting_relative_url = distributor['config']['relative_path']
        description = _('Relative path [{relative_path}] for repository [{repo_id}] conflicts '
                        'with relative path [{conflict_url}] for repository [{conflict_repo}]')
        msg = description.format(
            relative_path=relative_path,
            repo_id=repo_id,
            conflict_url=conflicting_relative_url,
            conflict_repo=conflicting_repo_id)
        messages.append(msg)
    return messages
