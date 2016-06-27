from gettext import gettext as _
import logging
import os

from pulp_ostree.common import constants

from mongoengine import Q
from pulp.server.db import model

_LOG = logging.getLogger(__name__)


def validate_config(repo, config):
    """
    Validate a configuration

    :param repo: metadata describing the repository to which the configuration applies
    :type  repo: pulp.plugins.model.Repository
    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :return: tuple of (bool, str) to describe the result
    :rtype:  tuple
    """
    repo_obj = repo.repo_obj
    relative_path = get_repo_relative_path(repo_obj, config)
    error_msgs = _check_for_relative_path_conflicts(repo_obj.repo_id, relative_path)

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


def _check_for_relative_path_conflicts(repo_id, relative_path):
    """
    Check that a relative path does not conflict with existing distributors' relative paths.

    :param repo_id: identifier of repository associated with the path to check
    :type  repo_id: basestring
    :param relative_path: relative path of the repository
    :type  relative_path: basestring
    :return error_messages: a list of validation errors
    :rtype: list
    """
    current_url_pieces = [x for x in relative_path.split('/') if x]
    matching_url_list = []
    working_url = ''
    for piece in current_url_pieces:
        working_url = os.path.join(working_url, piece)
        matching_url_list.append(working_url)
        matching_url_list.append('/' + working_url)

    # Search for all the sub urls as well as any url that would fall within the specified url.
    # The regex here basically matches the a url if it starts with (optional preceding slash)
    # the working url. Anything can follow as long as it is separated by a slash.
    rel_url_match = Q(config__relative_path={'$regex': '^/?' + working_url + '(/.*|/?\z)'})
    rel_url_in_list = Q(config__relative_path__in=matching_url_list)

    conflicts = model.Distributor.objects(rel_url_match | rel_url_in_list).only('repo_id', 'config')
    error_messages = []
    for distributor in conflicts:
        conflicting_repo_id = distributor['repo_id']
        conflicting_relative_url = None
        conflicting_relative_url = distributor['config']['relative_path']
        msg = _('Relative path [{relative_path}] for repository [{repo_id}] conflicts with '
                'existing relative path [{conflict_url}] for repository [{conflict_repo}]')
        error_messages.append(msg.format(relative_path=relative_path, repo_id=repo_id,
                                         conflict_url=conflicting_relative_url,
                                         conflict_repo=conflicting_repo_id))
    return error_messages
