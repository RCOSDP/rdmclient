import io
import logging
from typing import Type, AsyncGenerator, TypeVar, Dict, Any
from tqdm import tqdm
from typing import AsyncGenerator, Dict, Type, TypeVar

from .core import OSFCore
from ..exceptions import FolderExistsException, UnauthorizedException
from ..utils import file_empty
from .utils import chunked_bytes_iterator, merge_query_params


logger = logging.getLogger(__name__)
OSFCoreType = TypeVar('OSFCoreType', bound=OSFCore)
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class tqdm_indeterminate(tqdm):
    """Provide indeterminate progress bar
    """
    symbols = r'/-\|'
    bar = 0

    @property
    def format_dict(self):
        d = super(tqdm_indeterminate, self).format_dict
        indeterminate_bar = self.symbols[self.bar]
        self.bar = self.bar + 1 if self.bar + 1 < len(self.symbols) else 0
        d.update(indeterminate_bar=indeterminate_bar)
        return d


async def copyfileobj(fsrc, fdst, total, length=16*1024):
    """Copy data from file-like object fsrc to file-like object fdst

    This is like shutil.copyfileobj but with a progressbar.
    """
    format_ind_loop = '{indeterminate_bar} {elapsed}, {rate_fmt}'
    with (tqdm(unit='bytes', total=total, unit_scale=True)
          if total is not None else
          tqdm_indeterminate(unit='bytes', unit_scale=True,
                             bar_format=format_ind_loop)) as pbar:
        async for buf in fsrc:
            await fdst.write(buf)
            pbar.update(len(buf))


class File(OSFCore):
    def _update_attributes(self, file):
        if not file:
            return

        self.id = self._get_attribute(file, 'id')

        self._download_url = self._get_attribute(file, 'links', 'download')
        self._upload_url = self._get_attribute(file, 'links', 'upload')
        self._delete_url = self._get_attribute(file, 'links', 'delete')
        self._move_url = self._get_attribute(file, 'links', 'move')
        self.osf_path = self._get_attribute(file, 'attributes', 'path')
        self.path = self._get_attribute(file,
                                        'attributes', 'materialized')
        self.name = self._get_attribute(file, 'attributes', 'name')
        self.date_created = self._get_attribute(file,
                                                'attributes', 'created_utc',
                                                default='')
        self.date_modified = self._get_attribute(file,
                                                 'attributes', 'modified_utc',
                                                 default='')
        if not self.date_created:
            self.date_created = self._get_attribute(file,
                                                    'attributes', 'created',
                                                    default='')
        if not self.date_modified:
            self.date_modified = self._get_attribute(file,
                                                     'attributes', 'modified',
                                                     default='')
        if self.date_created == '':
            self.date_created = None
        if self.date_modified == '':
            self.date_modified = None
        self.size = self._get_attribute(file, 'attributes', 'size')
        self.hashes = self._get_attribute(file,
                                          'attributes', 'extra', 'hashes',
                                          default={})

    def __str__(self):
        return '<File [{0}, {1}]>'.format(self.id, self.path)

    async def write_to(self, fp):
        """Write contents of this file to a local file.

        Pass in a filepointer `fp` that has been opened for writing in
        binary mode.
        """
        if hasattr(fp, 'mode') and 'b' not in fp.mode:
            raise ValueError("File has to be opened in binary mode.")

        try:
            await self._write_to(fp, self._download_url)
        except UnauthorizedException:
            await self._write_to(fp, self._upload_url)

    async def _write_to(self, fp, url):
        async with self._stream('GET', url) as response:
            if response.status_code == 401:
                raise UnauthorizedException()
            if response.status_code == 200:
                async for data in response.aiter_bytes():
                    await fp.write(data)
                await fp.flush()
            else:
                raise RuntimeError("Response has status "
                                "code {}.".format(response.status_code))

    async def remove(self):
        """Remove this file from the remote storage."""
        response = await self._delete(self._delete_url)
        if response.status_code != 204:
            raise RuntimeError('Could not delete {}.'.format(self.path))

    async def update(self, fp):
        """Update the remote file from a local file.

        Pass in a filepointer `fp` that has been opened for writing in
        binary mode.
        """
        if hasattr(fp, 'mode') and 'b' not in fp.mode:
            raise ValueError("File has to be opened in binary mode.")

        url = self._upload_url
        # peek at the file to check if it is an ampty file which needs special
        # handling in requests. If we pass a file like object to data that
        # turns out to be of length zero then no file is created on the OSF
        if not await file_empty(fp):
            logger.info("Uploading file: %s", self.path)
            response = await self._put(
                url,
                content=chunked_bytes_iterator(fp) if hasattr(fp, 'read') else fp,
            )
        else:
            logger.info("File is empty, uploading zero-length bytes.")
            response = await self._put(url, content=b'')

        if response.status_code != 200:
            msg = ('Could not update {} (status '
                   'code: {}).'.format(self.path, response.status_code))
            raise RuntimeError(msg)

    async def move_to(self, storage, to_folder, to_filename=None, force=False):
        """Move this file to the remote storage."""
        try:
            path = to_folder.osf_path
        except AttributeError:
            path = to_folder.path
        body = {'action': 'move', 'path': path}
        if to_filename is not None:
            body['rename'] = to_filename
        if force:
            body['conflict'] = 'replace'
        response = await self._post(self._move_url, json=body)
        if response.status_code != 200 and response.status_code != 201:
            raise RuntimeError('Could not move {} (status '
                               'code: {}).'.format(self.path,
                                                   response.status_code))


class ContainerMixin:
    async def _iter_children(
        self, url: str, kind, klass: Type[OSFCoreType], recurse=None, target_filter=None
    ) -> AsyncGenerator[OSFCoreType, None]:
        """Iterate over all children of `kind`

        Yield an instance of `klass` when a child is of type `kind`. Uses
        `recurse` as the path of attributes in the JSON returned from `url`
        to find more children.
        """
        async for children in self._follow_next(url):
            for child in children:
                if target_filter is not None and not target_filter(child):
                    continue
                kind_ = child['attributes']['kind']
                if kind_ == kind:
                    yield klass(child, self.session)
                if kind_ != 'file' and recurse is not None:
                    # recurse into a child and add entries to `children`
                    url = self._get_attribute(child, *recurse)
                    async for entry in self._iter_children(url, kind, klass,
                                                           recurse=recurse,
                                                           target_filter=target_filter):
                        yield entry

    async def _iter_children_for_mixed_types(
        self, url: str, klasses: Dict[str, Type], recurse=None, target_filter=None
    ) -> AsyncGenerator[OSFCore, None]:
        """Iterate over all children

        _iter_children_for_mixed_types is a more general version of _iter_children
        that can handle multiple kinds of children. It takes a dictionary of
        `klasses` that maps kinds to classes.
        """
        async for children in self._follow_next(url):
            for child in children:
                if target_filter is not None and not target_filter(child):
                    continue
                kind = child['attributes']['kind']
                klass = klasses.get(kind)
                if klass is not None:
                    yield klass(child, self.session)
                if kind != 'file' and recurse is not None:
                    # recurse into a child and add entries to `children`
                    url = self._get_attribute(child, *recurse)
                    async for entry in self._iter_children_for_mixed_types(
                        url, klasses, recurse=recurse, target_filter=target_filter
                    ):
                        yield entry

    @property
    def files(self):
        """Iterate over all files in this folder.

        Unlike a `Storage` instance this does not recursively find all files.
        Only lists files in this folder.
        """
        return self._iter_children(self._files_url, 'file', File)

    @property
    def folders(self):
        """Iterate over top-level folders in this folder."""
        return self._iter_children(self._files_url, 'folder', Folder)

    @property
    def children(self):
        """Iterate over all children in this folder."""
        return self._iter_children_for_mixed_types(self._files_url,
                                                   {'file': File, 'folder': Folder})

    async def create_folder(self, name, exist_ok=False):
        url = self._new_folder_url
        # Create a new sub-folder
        response = await self._put(
            url,
            params=merge_query_params(url, {'name': name}),
        )
        if response.status_code == 409 and not exist_ok:
            raise FolderExistsException(name)

        elif response.status_code == 409 and exist_ok:
            async for folder in self.folders:
                if folder.name == name:
                    return folder

        elif response.status_code == 201:
            return Folder(response.json()['data'], self.session)

        else:
            raise RuntimeError("Response has status code {} while creating "
                               "folder {}.".format(response.status_code,
                                                   name))


class Folder(OSFCore, ContainerMixin):
    def _update_attributes(self, file):
        if not file:
            return

        self.id = self._get_attribute(file, 'id')

        self._delete_url = self._get_attribute(file, 'links', 'delete')
        self._new_folder_url = self._get_attribute(file, 'links', 'new_folder')
        self._new_file_url = self._get_attribute(file, 'links', 'upload')
        self._move_url = self._get_attribute(file, 'links', 'move')

        self._files_key = ('links', 'move')
        self._files_url = self._get_attribute(file, *self._files_key)

        self.osf_path = self._get_attribute(file, 'attributes', 'path')
        self.path = self._get_attribute(file,
                                        'attributes', 'materialized')
        self.name = self._get_attribute(file, 'attributes', 'name')
        self.date_created = self._get_attribute(file,
                                                'attributes', 'created_utc',
                                                default='')
        self.date_modified = self._get_attribute(file,
                                                 'attributes', 'modified_utc',
                                                 default='')
        if not self.date_created:
            self.date_created = self._get_attribute(file,
                                                    'attributes', 'created',
                                                    default='')
        if not self.date_modified:
            self.date_modified = self._get_attribute(file,
                                                     'attributes', 'modified',
                                                     default='')
        if self.date_created == '':
            self.date_created = None
        if self.date_modified == '':
            self.date_modified = None

    def __str__(self):
        return '<Folder [{0}, {1}]>'.format(self.id, self.path)

    async def remove(self):
        """Remove this folder from the remote storage."""
        response = await self._delete(self._delete_url)
        if response.status_code != 204:
            raise RuntimeError('Could not delete {}.'.format(self.path))

    async def move_to(self, storage, to_folder, to_foldername=None, force=False):
        """Move this file to the remote storage."""
        try:
            path = to_folder.osf_path
        except AttributeError:
            path = to_folder.path
        body = {'action': 'move', 'path': path}
        if to_foldername is not None:
            body['rename'] = to_foldername
        if force:
            body['conflict'] = 'replace'
        response = await self._post(self._move_url, json=body)
        if response.status_code != 200 and response.status_code != 201:
            raise RuntimeError('Could not move {} (status '
                               'code: {}).'.format(self.path,
                                                   response.status_code))

