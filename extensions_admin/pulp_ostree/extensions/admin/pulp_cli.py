from pulp.client.extensions.decorator import priority


@priority()
def initialize(context):
    """
    Create the ostree CLI section and add it to the root

    :param context: the CLI context.
    :type context: pulp.client.extensions.core.ClientContext
    """
