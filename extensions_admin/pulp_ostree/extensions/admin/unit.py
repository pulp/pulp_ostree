from gettext import gettext as _

from pulp.client.commands import options
from pulp.client.commands.unit import UnitCopyCommand, UnitRemoveCommand
from pulp.client.commands.criteria import DisplayUnitAssociationsCommand


def format_unit(unit_key):
    """
    Get a short string representation of an ostree unit key.
    :param unit_key: An ostree unit key.
    :type unit_key: dict
    :return: A string representation.
    :rtype: str
    :see: pulp_ostree.common.model.Repository
    """
    return 'remote_id:%(remote_id)s branch:%(branch)s commit:%(commit)s' % unit_key


class CopyCommand(UnitCopyCommand):
    """
    Copy unit command.
    """

    def get_formatter_for_type(self, type_id):
        """
        Get a formatter for the specified type ID.
        :param type_id: A unit type ID.
        :type type_id: str
        :return: The requested formatter.
        :rtype: callable
        """
        return format_unit


class RemoveCommand(UnitRemoveCommand):
    """
    Remove unit command.
    """

    def get_formatter_for_type(self, type_id):
        """
        Get a formatter for the specified type ID.
        :param type_id: A unit type ID.
        :type type_id: str
        :return: The requested formatter.
        :rtype: callable
        """
        return format_unit


class SearchCommand(DisplayUnitAssociationsCommand):

    TITLE = _('Content Units')

    ORDER = [
        'id',
        'created',
        'updated',
        'remote_id',
        'branch',
        'commit',
        'version'
    ]

    @staticmethod
    def transform(unit):
        """
        Transform the specified unit into document to be displayed.
        :param unit: A content unit to be transformed.
        :type unit: dict
        :return: A document.
        :rtype: dict
        """
        metadata = unit['metadata']
        document = {
            'id': unit['unit_id'],
            'created': unit['created'],
            'updated': unit['updated'],
            'remote_id': metadata['remote_id'],
            'branch': metadata['branch'],
            'commit': metadata['commit'],
            'version': metadata['metadata'].get('version')
        }
        return document

    def __init__(self, context):
        """
        :param context: A command context.
        :type context: pulp.client.extensions.core.ClientContext
        """
        super(SearchCommand, self).__init__(self.run)
        self.context = context

    def run(self, **kwargs):
        """
        Run the command
        :param kwargs: Keyword arguments.
        :type kwargs: dict
        """
        self.context.prompt.render_title(self.TITLE)
        repo_id = kwargs.pop(options.OPTION_REPO_ID.keyword)
        units = self.context.server.repo_unit.search(repo_id, **kwargs).response_body
        documents = [self.transform(u) for u in units]
        self.context.prompt.render_document_list(documents, order=self.ORDER)
