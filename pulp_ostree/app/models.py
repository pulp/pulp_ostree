"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    http://docs.pulpproject.org/en/3.0/nightly/plugins/plugin-writer/index.html
"""

from logging import getLogger

from django.db import models

from pulpcore.plugin.models import (
    Content,
    ContentArtifact,
    Remote,
    Repository,
    Publication,
    Distribution,
)

logger = getLogger(__name__)


class OstreeContent(Content):
    """
    The "ostree" content type.

    Define fields you need for your new content type and
    specify uniqueness constraint to identify unit of this type.

    For example::

        field1 = models.TextField()
        field2 = models.IntegerField()
        field3 = models.CharField()

        class Meta:
            default_related_name = "%(app_label)s_%(model_name)s"
            unique_together = (field1, field2)
    """

    TYPE = "ostree"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class OstreePublication(Publication):
    """
    A Publication for OstreeContent.

    Define any additional fields for your new publication if needed.
    """

    TYPE = "ostree"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class OstreeRemote(Remote):
    """
    A Remote for OstreeContent.

    Define any additional fields for your new remote if needed.
    """

    TYPE = "ostree"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class OstreeRepository(Repository):
    """
    A Repository for OstreeContent.

    Define any additional fields for your new repository if needed.
    """

    TYPE = "ostree"

    CONTENT_TYPES = [OstreeContent]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class OstreeDistribution(Distribution):
    """
    A Distribution for OstreeContent.

    Define any additional fields for your new distribution if needed.
    """

    TYPE = "ostree"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
