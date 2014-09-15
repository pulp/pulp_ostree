
from threading import Thread

from mock import patch, Mock


from pulp.common.plugins import importer_constants

from pulp_ostree.common import constants


PATH = '/tmp/jeff'
REMOTE_NAME = 'jeff'
REMOTE_URL = 'http://rpm-ostree.cloud.fedoraproject.org/repo'
TREE = 'fedora-atomic/f21/x86_64/docker-host'

cfg = {
    constants.IMPORTER_CONFIG_KEY_BRANCHES: [TREE],
    importer_constants.KEY_FEED: 'http://rpm-ostree.cloud.fedoraproject.org/repo',
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


thread = Thread(target=test)
thread.setDaemon(True)
thread.start()
thread.join()

print thread.getName()

thread = Thread(target=test)
thread.setDaemon(True)
thread.start()
thread.join()

print thread.getName()
