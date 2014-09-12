
from mock import Mock


from pulp.common.plugins import importer_constants

from pulp_ostree.common import constants
from pulp_ostree.plugins.importers import web

PATH = '/tmp/jeff'
REMOTE_NAME = 'jeff'
REMOTE_URL = 'http://rpm-ostree.cloud.fedoraproject.org/repo'
TREE = 'fedora-atomic/f21/x86_64/docker-host'

cfg = {
    constants.IMPORTER_CONFIG_KEY_BRANCHES: [TREE],
    importer_constants.KEY_FEED: 'http://rpm-ostree.cloud.fedoraproject.org/repo',
}

web.STORAGE_DIR = PATH

step = web.MainStep(
    repo=Mock(),
    conduit=Mock(),
    config=cfg,
    working_dir='/tmp/working')

step.process_lifecycle()


