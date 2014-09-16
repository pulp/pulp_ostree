
REPOSITORY_TYPE_ID = 'ostree_repository'
REPO_NOTE_OSTREE = 'OSTREE'

WEB_IMPORTER_TYPE_ID = 'ostree_web_importer'
WEB_DISTRIBUTOR_TYPE_ID = 'ostree_web_distributor'

CLI_WEB_DISTRIBUTOR_ID = 'ostree_web_distributor_name_cli'

IMPORTER_CONFIG_KEY_BRANCHES = 'branches'

DISTRIBUTOR_CONFIG_FILE_NAME = 'server/plugins.conf.d/ostree_distributor.json'

# Config keys for the distributor plugin conf
CONFIG_KEY_OSTREE_PUBLISH_DIRECTORY = 'ostree_publish_directory'
CONFIG_VALUE_OSTREE_PUBLISH_DIRECTORY = '/var/lib/pulp/published/ostree'

# STEP_ID
PUBLISH_STEP_WEB_PUBLISHER = 'ostree_publish_step_web'
PUBLISH_STEP_CONTENT = 'ostree_publish_content'
PUBLISH_STEP_METADATA = 'ostree_publish_metadata'
PUBLISH_STEP_OVER_HTTP = 'ostree_publish_over_http'
