from functools import partial
import logging
import os
import six

from httpx import HTTPError

from .core import OSFCore
from .file import ContainerMixin
from .file import File
from .file import Folder
from ..utils import file_empty
from ..utils import get_local_file_size
from ..utils import norm_remote_path
from ..utils import find_by_path
from ..utils import is_folder
from ..utils import checksum_fp
from ..utils import norm_remote_path
from ..utils import find_by_path
from .utils import chunked_bytes_iterator, merge_query_params


logger = logging.getLogger(__name__)


if six.PY2:
    class FileExistsError(OSError):
        """
        Exception raised when a file already exists
        Standard in Python 3
        """


class Storage(OSFCore, ContainerMixin):
    _files_key = ('links', 'upload')

    def _update_attributes(self, storage):
        if not storage:
            return

        self.id = self._get_attribute(storage, 'id')

        self.path = self._get_attribute(storage, 'attributes', 'path')
        self.name = self._get_attribute(storage, 'attributes', 'name')
        self.node = self._get_attribute(storage, 'attributes', 'node')
        self.provider = self._get_attribute(storage, 'attributes', 'provider')

        self._files_url = self._get_attribute(storage, *self._files_key)

        self._new_folder_url = self._get_attribute(storage,
                                                   'links', 'new_folder')
        self._new_file_url = self._get_attribute(storage, 'links', 'upload')

    def __str__(self):
        return '<Storage [{0}]>'.format(self.id)

    @property
    def files(self):
        """Iterate over all files in this storage."""
        return self._iter_children(self._files_url, 'file', File)

    @property
    def folders(self):
        """Iterate over all folders in this storage."""
        return self._iter_children(self._files_url, 'folder', Folder)

    @property
    def children(self):
        """Iterate over all children in this storage."""
        return self._iter_children_for_mixed_types(self._files_url,
                                                   {'file': File, 'folder': Folder})

    async def create_file(self, path: str, fp, force=False, update=False):
        """Store a new file at `path` in this storage.

        The contents of the file descriptor `fp` (opened in 'rb' mode)
        will be uploaded to `path` which is the full path at
        which to store the file.

        To force overwrite of an existing file, set `force=True`.
        To overwrite an existing file only if the files differ, set `update=True`
        """
        if hasattr(fp, 'mode') and 'b' not in fp.mode:
            raise ValueError("File has to be opened in binary mode.")

        # all paths are assumed to be absolute
        path = norm_remote_path(path)

        directory, fname = os.path.split(path)
        directories = directory.split(os.path.sep)
        # navigate to the right parent object for our file
        parent = self
        for directory in directories:
            # skip empty directory names
            if directory:
                parent = await parent.create_folder(directory, exist_ok=True)

        url = parent._new_file_url

        # When uploading a large file (>a few MB) that already exists
        # we sometimes get a HTTPError instead of a status == 409.
        connection_error = False

        # peek at the file to check if it is an empty file which needs special
        # handling in requests. If we pass a file like object to data that
        # turns out to be of length zero then no file is created on the OSF.
        # See: https://github.com/osfclient/osfclient/pull/135
        if await file_empty(fp):
            logger.info("File is empty, uploading zero-length bytes.")
            response = await self._put(
                url,
                params=merge_query_params(url, {'name': fname}),
                content=b''
            )

        else:
            logger.info("Uploading file: %s", path)
            try:
                response = await self._put(
                    url,
                    params=merge_query_params(url, {'name': fname}),
                    content=chunked_bytes_iterator(fp) if hasattr(fp, 'read') else fp,
                )
            except HTTPError:
                connection_error = True
                logger.info("Connection error while uploading file: %s", path)

        if connection_error or response.status_code == 409:
            if not force and not update:
                # one-liner to get file size from file pointer from
                # https://stackoverflow.com/a/283719/2680824
                file_size_bytes = get_local_file_size(fp)
                large_file_cutoff = 2**20 # 1 MB in bytes
                if connection_error and file_size_bytes < large_file_cutoff:
                    msg = (
                        "There was a connection error which might mean {} " +
                        "already exists. Try again with the `--force` flag " +
                        "specified."
                    ).format(path)
                    raise RuntimeError(msg)
                else:
                    # note in case of connection error, we are making an inference here
                    raise FileExistsError(path)
            else:
                # find the upload URL for the file we are trying to update
                file_ = await find_by_path(self, path)
                if file_ is None:
                    raise RuntimeError("Could not create a new file at "
                                    "({}) nor update it.".format(path))
                if is_folder(file_):
                    raise RuntimeError("Cannot update a folder.")
                if not force:
                    if await checksum_fp(fp) == file_.hashes.get('md5'):
                        # If the hashes are equal and force is False,
                        # we're done here
                        logger.info("File already exists and hashes match, "
                                    "skipping upload. local: %s, remote: %s" %
                                    (await checksum_fp(fp), file_.hashes.get('md5')))
                        return
                # in the process of attempting to upload the file we
                # moved through it -> reset read position to beginning
                # of the file
                await fp.seek(0)
                await file_.update(fp)
