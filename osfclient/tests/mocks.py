import asyncio
from mock import MagicMock, PropertyMock
from ..utils import norm_remote_path, is_path_matched


def FutureWrapper(value=None):
    f = asyncio.Future()
    f.set_result(value)
    return f


# When using a PropertyMock store it as an attribute
# of the mock it belongs to so that later on a caller
# can assert whether or not it has been accessed
def MockFile(name):
    mock = MagicMock(name='File-%s' % name, path=name)
    path = PropertyMock(return_value=name)
    type(mock).path = path
    mock._path_mock = path
    hashes_dict = dict(md5='0' * 32, sha256='0' * 64)
    hashes = PropertyMock(return_value=hashes_dict)
    type(mock).hashes = hashes
    mock._hashes_mock = hashes
    mock.write_to = MagicMock(return_value=FutureWrapper())
    mock.move_to = MagicMock(return_value=FutureWrapper())
    mock.remove = MagicMock(return_value=FutureWrapper())
    return mock


def MockFolder(name):
    mock = MagicMock(name='Folder-%s' % name, path=name)
    path = PropertyMock(return_value=name)
    type(mock).path = path
    mock._path_mock = path
    name = PropertyMock(return_value=name)
    type(mock).name = name
    mock._name_mock = name
    mock.move_to = MagicMock(return_value=FutureWrapper())
    mock.create_file = MagicMock(return_value=FutureWrapper())
    mock.create_folder = MagicMock(side_effect=lambda name: FutureWrapper(mock))
    mock.remove = MagicMock(return_value=FutureWrapper())
    return mock


def MockStorage(name):
    def make_matched_files(mock):
        def make_raw_file(file):
            return {'attributes': {'materialized_path': '/' + norm_remote_path(file._path_mock.return_value)}}
        async def matched_files(target_filter):
            for f in mock.files:
                if not target_filter(make_raw_file(f)):
                    continue
                yield f
        return matched_files

    mock = MagicMock(name='Storage-%s' % name,
                     files=[MockFile('/a/a/a'), MockFile('b/b/b')],
                     folders=[MockFolder('/a'), MockFolder('/a/a'),
                              MockFolder('/c'), MockFolder('/c/c')])
    name = PropertyMock(return_value=name)
    type(mock).name = name
    mock._name_mock = name
    matched_files = MagicMock(side_effect=make_matched_files(mock))
    type(mock).matched_files = matched_files
    mock._matched_files_mock = matched_files
    mock.create_file = MagicMock(return_value=FutureWrapper())
    mock.create_folder = MagicMock(side_effect=lambda name: FutureWrapper(MockFolder(name)))
    return mock


def FutureMockStorage(name):
    f = asyncio.Future()
    f.set_result(MockStorage(name))
    return f


def MockProject(name):
    mock = MagicMock(name='Project-%s' % name,
                     storages=[MockStorage('osfstorage'), MockStorage('gh')])
    storage = MagicMock(name='Project-%s-storage' % name,
                        return_value=FutureMockStorage('osfstorage'))
    type(mock).storage = storage
    mock._storage_mock = storage

    return mock


def MockArgs(username=None, password=None, output=None, project=None,
             source=None, destination=None, local=None, remote=None,
             target=None, force=False, update=False, recursive=False,
             base_url=None, long_format=False, base_path=None):
    args = MagicMock(spec=['username', 'password', 'output', 'project',
                           'source', 'destination', 'target', 'force',
                           'recursive', 'base_url', 'long_format',
                           'base_path'])
    args._username_mock = PropertyMock(return_value=username)
    type(args).username = args._username_mock
    args._password_mock = PropertyMock(return_value=password)
    type(args).password = args._password_mock

    args._output_mock = PropertyMock(return_value=output)
    type(args).output = args._output_mock
    args._project_mock = PropertyMock(return_value=project)
    type(args).project = args._project_mock
    args._base_url_mock = PropertyMock(return_value=base_url)
    type(args).base_url = args._base_url_mock
    args._base_path_mock = PropertyMock(return_value=base_path)
    type(args).base_path = args._base_path_mock

    args._source_mock = PropertyMock(return_value=source)
    type(args).source = args._source_mock
    args._destination_mock = PropertyMock(return_value=destination)
    type(args).destination = args._destination_mock

    args._target_mock = PropertyMock(return_value=target)
    type(args).target = args._target_mock

    args._remote_mock = PropertyMock(return_value=remote)
    type(args).remote = args._remote_mock
    args._local_mock = PropertyMock(return_value=local)
    type(args).local = args._local_mock

    args._long_format_mock = PropertyMock(return_value=long_format)
    type(args).long_format = args._long_format_mock

    args._force_mock = PropertyMock(return_value=force)
    type(args).force = args._force_mock
    args._update_mock = PropertyMock(return_value=update)
    type(args).update = args._update_mock

    args._recursive_mock = PropertyMock(return_value=recursive)
    type(args).recursive = args._recursive_mock

    return args


class FakeResponse:
    def __init__(self, status_code, json):
        self.status_code = status_code
        self._json = json

    def json(self):
        return self._json


def FutureFakeResponse(status_code, json):
    return FutureWrapper(FakeResponse(status_code, json))


class AsyncIterator:
    def __init__(self, seq):
        self.iter = iter(seq)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration


class FutureStreamResponse(MagicMock):
    def __init__(self, response):
        super(FutureStreamResponse, self).__init__()
        resp = MagicMock()
        resp.status_code = response.status_code
        resp.aiter_bytes = lambda: AsyncIterator([response.raw])
        self.__aenter__ = MagicMock(return_value=FutureWrapper(resp))
