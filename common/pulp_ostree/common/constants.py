# Content
OSTREE_TYPE_ID = 'ostree'


# Platform
CONTENT_DIR = 'content'
LINKS_DIR = 'links'
SHARED_STORAGE = '/var/lib/pulp/content/shared/%s' % OSTREE_TYPE_ID


# Notes
REPO_NOTE_OSTREE = 'OSTREE'


# Plugins
WEB_IMPORTER_TYPE_ID = 'ostree_web_importer'
WEB_DISTRIBUTOR_TYPE_ID = 'ostree_web_distributor'
CLI_WEB_DISTRIBUTOR_ID = 'ostree_web_distributor_name_cli'


# Configuration
IMPORTER_CONFIG_KEY_BRANCHES = 'branches'
IMPORTER_CONFIG_FILE_PATH = 'server/plugins.conf.d/ostree_importer.json'
DISTRIBUTOR_CONFIG_KEY_PUBLISH_DIRECTORY = 'ostree_publish_directory'
DISTRIBUTOR_CONFIG_VALUE_PUBLISH_DIRECTORY = '/var/lib/pulp/published/ostree'
DISTRIBUTOR_CONFIG_FILE_PATH = 'server/plugins.conf.d/ostree_distributor.json'


# Steps
IMPORT_STEP_MAIN = 'import_main'
IMPORT_STEP_CREATE_REPOSITORY = 'import_create_repository'
IMPORT_STEP_PULL = 'import_pull'
IMPORT_STEP_ADD_UNITS = 'import_add_unit'

PUBLISH_STEP_WEB_PUBLISHER = 'ostree_publish_step_web'
PUBLISH_STEP_MAIN = 'ostree_publish_main'
PUBLISH_STEP_OVER_HTTP = 'ostree_publish_over_http'
