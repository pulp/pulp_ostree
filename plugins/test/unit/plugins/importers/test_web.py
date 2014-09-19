from mock import patch, Mock

from pulp.common.plugins import importer_constants

from pulp_ostree.common import constants

#
# TODO: REWRITE BEFORE FINAL MERGE
#


PATH = '/opt/content/ostree/jeff2'
REMOTE_NAME = 'jeff2'
REMOTE_URL = 'http://localhost/content/ostree/jeff/'
TREE = 'fedora-atomic/f21/x86_64/docker-host'

cfg = {
    constants.IMPORTER_CONFIG_KEY_BRANCHES: [TREE],
    importer_constants.KEY_FEED: REMOTE_URL,
}


@patch('pulp_ostree.plugins.importers.steps.STORAGE_DIR', PATH)
def test():
    from pulp_ostree.plugins.importers import web
    step = web.Main(
        repo=Mock(),
        conduit=Mock(),
        config=cfg,
        working_dir='/tmp/working')
    step.process_lifecycle()


if __name__ == '__main__':
    test()
