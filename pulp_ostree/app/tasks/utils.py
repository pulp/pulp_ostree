import os

from pulp_ostree.app.models import OstreeObjectType


def get_checksum_filepath(checksum, obj_type):
    """Return an object's relative filepath within a repository based on its checksum and type."""
    extension = get_file_extension(obj_type)
    return os.path.join("objects/", checksum[:2], f"{checksum[2:]}.{extension}")


def get_file_extension(obj_type):
    """Return a file extension based on the type of the object."""
    if obj_type == OstreeObjectType.OSTREE_OBJECT_TYPE_FILE:
        return "filez"
    elif obj_type == OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT:
        return "commit"
    elif obj_type == OstreeObjectType.OSTREE_OBJECT_TYPE_DIR_META:
        return "dirmeta"
    elif obj_type == OstreeObjectType.OSTREE_OBJECT_TYPE_DIR_TREE:
        return "dirtree"


def bytes_to_checksum(int_bytes):
    """Convert bytes to hexadecimal digits representing a checksum."""
    return "".join(["%02x" % v for v in int_bytes])
