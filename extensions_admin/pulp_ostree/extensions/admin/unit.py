from pulp.client.commands.unit import UnitCopyCommand, UnitRemoveCommand


def format_unit(unit_key):
    """
    Get a short string representation of an ostree unit key.
    :param unit_key: An ostree unit key.
    :type unit_key: dict
    :return: A string representation.
    :rtype: str
    :see: pulp_ostree.common.model.Repository
    """
    return 'remote_id: %(remote_id)s digest: %(digest)s' % unit_key


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
