"""Utility functions

Helpers and other assorted functions.
"""

import hashlib
import os
import six

KNOWN_PROVIDERS = ['osfstorage', 'github', 'figshare', 'googledrive']


async def _async_generator(l):
    for elem in l:
        yield elem

def norm_remote_path(path):
    """Normalize `path`.

    All remote paths are absolute.
    """
    path = os.path.normpath(path)
    if path.startswith(os.path.sep):
        return path[1:]
    else:
        return path


def split_storage(path, default='osfstorage', normalize=True):
    """Extract storage name from file path.

    If a path begins with a known storage provider the name is removed
    from the path. Otherwise the `default` storage provider is returned
    and the path is not modified.
    """
    if normalize:
        path = norm_remote_path(path)
    env_known_providers = os.getenv('KNOWN_PROVIDERS')
    if env_known_providers is not None:
        known_providers = env_known_providers.split(',')
    else:
        known_providers = KNOWN_PROVIDERS

    for provider in known_providers:
        if path.startswith(provider + '/'):
            if six.PY3:
                return path.split('/', maxsplit=1)
            else:
                return path.split('/', 1)

    return (default, path)


def makedirs(path, mode=511, exist_ok=False):
    # mode 0777 is 511 in decimal
    if six.PY3:
        return os.makedirs(path, mode, exist_ok)
    else:
        if os.path.exists(path) and exist_ok:
            return None
        else:
            return os.makedirs(path, mode)


def file_empty(fp):
    """Determine if a file is empty or not."""
    if not hasattr(fp, 'peek'):
        # If a Reader does not support peek, it is not considered empty
        return False
    # for python 2 we need to use a homemade peek()
    if six.PY2:
        contents = fp.read()
        fp.seek(0)
        return not bool(contents)
    else:
        return not fp.peek()


def checksum(file_path, hash_type='md5', block_size=65536):
    """Returns either the md5 or sha256 hash of a file at `file_path`.

    md5 is the default hash_type as it is faster than sha256

    The default block size is 64 kb, which appears to be one of a few command
    choices according to https://stackoverflow.com/a/44873382/2680. The code
    below is an extension of the example presented in that post.
    """
    if hash_type == 'md5':
        hash_ = hashlib.md5()
    elif hash_type == 'sha256':
        hash_ = hashlib.sha256()
    else:
        raise ValueError(
            "{} is an invalid hash_type. Expected 'md5' or 'sha256'."
            .format(hash_type)
        )

    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            hash_.update(block)
    return hash_.hexdigest()


def get_local_file_size(fp):
    """Get file size from file pointer"""
    # one-liner to get file size from file pointer explained at
    # https://stackoverflow.com/a/283719/2680824
    return os.fstat(fp.fileno()).st_size


def is_path_matched(target_file_path, fileobj):
    file_path = fileobj['attributes']['materialized_path']
    if target_file_path is None:
        return True
    file_path_segs = file_path.split('/')
    target_file_path_segs = target_file_path.split('/')
    if file_path_segs[-1] == '':
        file_path_segs = file_path_segs[:-1]
    if target_file_path_segs[-1] == '':
        target_file_path_segs = target_file_path_segs[:-1]
    for target_file_path_seg, file_path_seg in zip(target_file_path_segs,
                                                   file_path_segs):
        if target_file_path_seg.startswith('%') and \
           target_file_path_seg.endswith('%'):
            if target_file_path_seg[1:-1] not in file_path_seg:
                return False
        elif target_file_path_seg.startswith('%'):
            if not file_path_seg.endswith(target_file_path_seg[1:]):
                return False
        elif target_file_path_seg.endswith('%'):
            if not file_path_seg.startswith(target_file_path_seg[:-1]):
                return False
        else:
            if file_path_seg != target_file_path_seg:
                return False
    return True


def ensure_async_generator(g):
    if hasattr(g, '__aiter__'):
        return g
    return _async_generator(g)
