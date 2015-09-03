from datetime import datetime
from hashlib import sha256

from mongoengine import DateTimeField, StringField, DictField
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


class Branch(SharedContentUnit):
    """
    A branch content unit.

    :cvar remote_id: Uniquely identifies a *remote* OSTree repository.
    :type remote_id: str
    :cvar branch: The branch path.
    :type branch: str
    :cvar commit: A commit.
    :type commit: str
    :cvar created: The created (UTC) timestamp.
    :type created: datetime
    :cvar metadata: The commit metadata.
    :type metadata: dict
    """

    # key
    remote_id = StringField(required=True)
    branch = StringField(required=True)
    commit = StringField(required=True)
    # other
    created = DateTimeField(db_field='_created', required=True)
    metadata = MetadataField()

    unit_key_fields = (
        'remote_id',
        'branch',
        'commit'
    )

    meta = {
        'allow_inheritance': False,
        'collection': 'units_ostree',
        'indexes': [
            {
                'fields': unit_key_fields,
                'unique': True
            },
        ]
    }

    # backward compatibility
    _ns = StringField(required=True, default=meta['collection'])
    unit_type_id = StringField(
        required=True,
        db_field='_content_type_id',
        default=constants.OSTREE_TYPE_ID)

    @classmethod
    def pre_save_signal(cls, sender, document, **kwargs):
        """
        The signal that is triggered before a unit is saved.
        Set the storage_path on the document and add the symbolic link.

        :param sender: sender class
        :type sender: object
        :param document: Document that sent the signal
        :type document: SharedContentUnit
        """
        super(Branch, cls).pre_save_signal(sender, document, **kwargs)
        document.created = datetime.utcnow()

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
