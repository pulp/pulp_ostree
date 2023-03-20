import hashlib
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


def compute_hash(filepath):
    """Compute the sha256 hash of a file described by its path."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def copy_to_local_storage(remote_file, local_path):
    """Copy a file from storage to a local file system."""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    with remote_file.open("rb") as remote_f:
        with open(local_path, "wb") as local_f:
            local_f.write(remote_f.read())
            local_f.flush()
