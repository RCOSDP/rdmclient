"""Utility functions

Helpers and other assorted functions.
"""

import hashlib
import os
import six
import aiofiles


KNOWN_PROVIDERS = [
    'osfstorage', 'github', 'figshare', 'googledrive',
    'azureblobstorage', 'bitbucket', 'box', 'dataverse', 'dropbox',
    'gitlab', 'iqbrims', 'nextcloud', 'nextcloudinstitutions',
    'ociinstitutions', 'owncloud', 'onedrivebusiness', 's3', 's3compat',
    's3compatb3', 's3compatinstitutions', 'swift', 'weko'
]


def norm_remote_path(path: str) -> str:
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


async def file_empty(fp):
    """Determine if a file is empty or not."""
    if not hasattr(fp, 'seek'):
        # If a Reader does not support seek, it is not considered empty
        return False
    await fp.seek(0, os.SEEK_END)
    pos = await fp.tell()
    await fp.seek(0)
    return pos == 0


async def checksum_path(file_path, hash_type='md5', block_size=65536):
    """Returns either the md5 or sha256 hash of a file at `file_path`.

    md5 is the default hash_type as it is faster than sha256

    The default block size is 64 kb, which appears to be one of a few command
    choices according to https://stackoverflow.com/a/44873382/2680. The code
    below is an extension of the example presented in that post.
    """
    async with aiofiles.open(file_path, 'rb') as f:
        return await checksum_fp(f, hash_type, block_size)


async def checksum_fp(fp, hash_type='md5', block_size=65536):
    """Returns either the md5 or sha256 hash of a file indicated by file pointer `fp`.

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

    await fp.seek(0)
    async for block in fp:
        hash_.update(block)
    return hash_.hexdigest()


def get_local_file_size(fp):
    """Get file size from file pointer"""
    # one-liner to get file size from file pointer explained at
    # https://stackoverflow.com/a/283719/2680824
    return os.fstat(fp.fileno()).st_size


def _is_path_matched(target_file_path, file_path):
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


def is_folder(file_or_folder):
    return hasattr(file_or_folder, 'files')


async def flatten(store):
    async for file_ in store.children:
        yield file_
        if not is_folder(file_):
            continue
        async for child in flatten(file_):
            yield child


async def find_ancestral_folder(store, target_file_path):
    file_path_segs = target_file_path.split('/')
    if(len(file_path_segs) <= 1):
        return None
    folder = store
    path = ''
    i = 0
    is_found = False
    for i in range(len(file_path_segs) - 1):
        path += file_path_segs[i]
        is_found = False
        async for folder_ in folder.folders:
            if norm_remote_path(folder_.path) == path:
                folder = folder_
                is_found = True
                break
        if not is_found:
            break
        path += '/'
    return folder if i > 0 or is_found else None


async def find_by_path(store, target_file_path):
    if target_file_path is None:
        return None
    file_path_segs = target_file_path.split('/')
    if(len(file_path_segs) == 1):
        async for file_ in store.children:
            if norm_remote_path(file_.path) == target_file_path:
                return file_
        return None
    else:
        parent_target_file_path = '/'.join(file_path_segs[:-1])
        parent_result = await find_by_path(store, parent_target_file_path)
        if parent_result is None:
            return None
        else:
            if is_folder(parent_result):
                async for file_ in parent_result.children:
                    if norm_remote_path(file_.path) == target_file_path:
                        return file_
            return None


async def filter_by_path_pattern(store, target_file_path):
    async for file_ in _filter_by_path_pattern(store, target_file_path, 0):
        yield file_


async def _filter_by_path_pattern(store, target_file_path, depth):
    if target_file_path is None or target_file_path == '/':
        async for file_ in flatten(store):
            yield file_
        return
    file_path_segs = target_file_path.split('/')
    if file_path_segs[0] == '':
        file_path_segs = file_path_segs[1:]
    if file_path_segs[-1] == '':
        file_path_segs = file_path_segs[:-1]
    if(len(file_path_segs) == 1):
        async for file_ in store.children:
            if not _is_path_matched(target_file_path, file_.path):
                continue
            yield file_
            if not is_folder(file_):
                continue
            if depth > 0:
                continue
            async for child in flatten(file_):
                yield child
    else:
        parent_target_file_path = '/' + '/'.join(file_path_segs[:-1]) + '/'
        async for rf_ in _filter_by_path_pattern(store, parent_target_file_path, depth + 1):
            if not is_folder(rf_):
                continue
            async for file_ in rf_.files:
                if _is_path_matched(target_file_path, file_.path):
                    continue
                yield file_
                if not is_folder(file_):
                    continue
                if depth > 0:
                    continue
                async for child in flatten(file_):
                    yield child
