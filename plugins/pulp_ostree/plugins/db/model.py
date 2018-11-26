from hashlib import sha256

from mongoengine import StringField, DictField
from pulp.server.db.model import SharedContentUnit

from pulp_ostree.common import constants


def generate_remote_id(url):
    """
    Generate a remote_id based on the url.

    :param url: The remote URL.
    :type url: basestring
    :return: The generated ID.
    :rtype:str
    """
    h = sha256()
    h.update(url)
    return h.hexdigest()


class MetadataField(DictField):
    """
    Commit metadata.
    """

    def to_mongo(self, value):
        """
        Replace '.' with '-' within keys.

        :param value: The original value.
        :type value: dict
        :return: The updated dictionary.
        :rtype: dict
        """
        return dict([(k.replace('.', '-'), v) for k, v in value.items()])

    def validate(self, value):
        """
        Converts dict keys pre-validation. Otherwise validation will fail.

        :param value: The original value.
        :type value: dict
        """
        # borrowed from mongoengine. Without this, the error when a non-dict value is assigned
        # would be a mysterious AttributeError from the above to_mongo() method.
        if not isinstance(value, dict):
            self.error('Only dictionaries may be used in a DictField')

        converted = self.to_mongo(value)
        super(MetadataField, self).validate(converted)


class Branch(SharedContentUnit):
    """
    A branch content unit.

    :cvar remote_id: Uniquely identifies a *remote* OSTree repository.
    :type remote_id: str
    :cvar branch: The branch path.
    :type branch: str
    :cvar commit: A commit ID.
    :type commit: str
    :cvar metadata: The commit metadata.
    :type metadata: dict
    """

    # key
    remote_id = StringField(required=True)
    branch = StringField(required=True)
    commit = StringField(required=True)
    # other
    metadata = MetadataField()

    unit_key_fields = (
        'remote_id',
        'branch',
        'commit'
    )

    meta = {
        'allow_inheritance': False,
        'collection': 'units_ostree',
        'indexes': []
    }

    # backward compatibility
    _ns = StringField(required=True, default=meta['collection'])
    _content_type_id = StringField(
        required=True,
        default=constants.OSTREE_TYPE_ID)

    @property
    def storage_provider(self):
        """
        The storage provider.
        This defines the storage mechanism and qualifies the storage_id.

        :return: The storage provider.
        :rtype: str
        """
        return constants.STORAGE_PROVIDER

    @property
    def storage_id(self):
        """
        The identifier for the shared storage location.
        :return: An identifier for shared storage.
        :rtype: str
        """
        return self.remote_id
