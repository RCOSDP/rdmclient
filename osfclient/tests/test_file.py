import asyncio
import io
from mock import call
from mock import patch
from mock import MagicMock
from mock import PropertyMock

import pytest

from osfclient.models import OSFCore
from osfclient.models import File
from osfclient.models import Folder
from osfclient.exceptions import FolderExistsException, UnauthorizedException
from osfclient.models.file import _WaterButlerFolder

from osfclient.tests import fake_responses
from osfclient.tests.mocks import (
    FutureFakeResponse, FutureStreamResponse, FakeResponse,
    MockFolder, AsyncIterator,
)

_files_url = 'https://api.osf.io/v2/nodes/f3szh/files/osfstorage/foo123'


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_iterate_files(OSFCore_get):
    store = Folder({})
    store._files_url = _files_url

    json = fake_responses.files_node('f3szh', 'osfstorage',
                                     ['foo/hello.txt', 'foo/bye.txt'])
    response = FakeResponse(200, json)
    OSFCore_get.return_value = response

    files = []
    async for f in store.files:
        files.append(f)

    assert len(files) == 2
    for file_ in files:
        assert isinstance(file_, File)
        assert file_.session == store.session

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2/nodes/f3szh/files/osfstorage/foo123')


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_iterate_folders(OSFCore_get):
    store = Folder({})
    store._files_url = _files_url

    json = fake_responses.files_node('f3szh', 'osfstorage',
                                     folder_names=['foo/bar', 'foo/baz'])
    response = FakeResponse(200, json)
    OSFCore_get.return_value = response

    folders = []
    async for f in store.folders:
        folders.append(f)

    assert len(folders) == 2
    for folder in folders:
        assert isinstance(folder, Folder)
        assert folder.session == store.session
        assert folder.name in ('foo/bar', 'foo/baz')

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2/nodes/f3szh/files/osfstorage/foo123')


@pytest.mark.asyncio
async def test_iterate_files_and_folders():
    # check we do not attempt to recurse into the subfolders
    store = Folder({})
    store._files_url = _files_url

    json = fake_responses.files_node('f3szh', 'osfstorage',
                                     file_names=['hello.txt', 'bye.txt'],
                                     folder_names=['bar'])
    top_level_response = FakeResponse(200, json)

    async def simple_OSFCore_get(url):
        if url == store._files_url:
            return top_level_response
        else:
            print(url)
            raise ValueError()

    with patch.object(OSFCore, '_get',
                      side_effect=simple_OSFCore_get) as mock_osf_get:
        files = []
        async for f in store.files:
            files.append(f)

    assert len(files) == 2
    for file_ in files:
        assert isinstance(file_, File)
        assert file_.session == store.session
        assert file_.name in ('hello.txt', 'bye.txt')

    # check we did not try to recurse into subfolders
    expected = [((_files_url,),)]
    assert mock_osf_get.call_args_list == expected


@pytest.mark.asyncio
async def test_create_existing_folder():
    folder = Folder({})
    new_folder_url = ('https://files.osf.io/v1/resources/9zpcy/providers/' +
                      'osfstorage/foo123/?kind=folder')
    folder._new_folder_url = new_folder_url
    folder._put = MagicMock(return_value=FutureFakeResponse(409, None))

    with pytest.raises(FolderExistsException):
        await folder.create_folder('foobar')

    folder._put.assert_called_once_with(new_folder_url,
                                        params={'name': 'foobar'})


@pytest.mark.asyncio
async def test_create_existing_folder_exist_ok():
    folder = Folder({})
    new_folder_url = ('https://files.osf.io/v1/resources/9zpcy/providers/' +
                      'osfstorage/foo123/?kind=folder')
    folder._new_folder_url = new_folder_url
    folder._put = MagicMock(return_value=FutureFakeResponse(409, None))

    with patch.object(Folder, 'folders',
                      new_callable=PropertyMock) as mock_folder:
        mock_folder.return_value = AsyncIterator([MockFolder('foobar'), MockFolder('fudge')])
        existing_folder = await folder.create_folder('foobar', exist_ok=True)

    assert existing_folder.name == 'foobar'

    folder._put.assert_called_once_with(new_folder_url,
                                        params={'name': 'foobar'})


@pytest.mark.asyncio
async def test_create_new_folder():
    folder = Folder({})
    new_folder_url = ('https://files.osf.io/v1/resources/9zpcy/providers/' +
                      'osfstorage/foo123/?kind=folder')
    folder._new_folder_url = new_folder_url
    # use an empty response as we won't do anything with the returned instance
    folder._put = MagicMock(return_value=FutureFakeResponse(201, {'data': {}}))

    new_folder = await folder.create_folder('foobar')

    assert isinstance(new_folder, _WaterButlerFolder)

    folder._put.assert_called_once_with(new_folder_url,
                                        params={'name': 'foobar'})


@pytest.mark.asyncio
async def test_remove_folder():
    folder = Folder({})
    folder._delete_url = 'http://delete.me/uri'
    folder._delete = MagicMock(return_value=FutureFakeResponse(204, {'data': {}}))

    await folder.remove()

    assert folder._delete.called


@pytest.mark.asyncio
async def test_remove_folder_failed():
    folder = Folder({})
    folder.path = 'some/path'
    folder._delete_url = 'http://delete.me/uri'
    folder._delete = MagicMock(return_value=FutureFakeResponse(404, {'data': {}}))

    with pytest.raises(RuntimeError) as e:
        await folder.remove()

    assert folder._delete.called

    assert 'Could not delete' in e.value.args[0]


@pytest.mark.asyncio
async def test_move_folder_to_dir():
    f = Folder({})
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(201, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    await f.move_to('osfclient', folder)

    f._post.assert_called_once_with('http://move.me/uri',
                                    json={'action': 'move', 'path': 'sample/'})


@pytest.mark.asyncio
async def test_move_folder_to_specified_dir_and_name():
    f = Folder({})
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(201, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    await f.move_to('osfclient', folder, to_foldername='newname')

    f._post.assert_called_once_with('http://move.me/uri',
                                    json={'action': 'move', 'path': 'sample/',
                                          'rename': 'newname'})


@pytest.mark.asyncio
async def test_move_folder_to_specified_name():
    f = Folder({})
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(201, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    await f.move_to('osfclient', folder, to_foldername='newname')

    f._post.assert_called_once_with('http://move.me/uri',
                                    json={'action': 'move', 'path': 'sample/',
                                          'rename': 'newname'})


@pytest.mark.asyncio
async def test_force_move_folder():
    f = Folder({})
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(201, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    await f.move_to('osfclient', folder, force=True)

    f._post.assert_called_once_with('http://move.me/uri',
                                    json={'action': 'move', 'path': 'sample/',
                                          'conflict': 'replace'})


@pytest.mark.asyncio
async def test_move_folder_failed():
    f = Folder({})
    f.path = 'some/path'
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(204, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    with pytest.raises(RuntimeError) as e:
        await f.move_to('osfclient', folder)

    assert f._post.called

    assert 'Could not move' in e.value.args[0]


@pytest.mark.asyncio
async def test_remove_file():
    f = File({})
    f._delete_url = 'http://delete.me/uri'
    f._delete = MagicMock(return_value=FutureFakeResponse(204, {'data': {}}))

    await f.remove()

    assert f._delete.called


@pytest.mark.asyncio
async def test_file_uses_streaming_request():
    # check we use streaming mode to fetch files
    fp = io.BytesIO(b"")
    fp.mode = "b"
    file_content = b"hello world"

    def fake_stream(method, url):
        res = FakeResponse(200, {})
        res.raw = file_content
        return FutureStreamResponse(res)

    with patch.object(File, "_stream", side_effect=fake_stream) as mock_stream:
        f = File({})
        f._download_url = "http://example.com/download_url/"
        await f.write_to(fp)

    fp.seek(0)
    assert file_content == fp.read()
    expected = call('GET', 'http://example.com/download_url/')
    assert expected in mock_stream.mock_calls


@pytest.mark.asyncio
async def test_file_uses_streaming_request_without_content_length():
    # check we use streaming mode to fetch files
    fp = io.BytesIO(b"")
    fp.mode = "b"
    file_content = b"hello world"

    def fake_stream(method, url):
        res = FakeResponse(200, {})
        res.raw = file_content
        return FutureStreamResponse(res)

    with patch.object(File, "_stream", side_effect=fake_stream) as mock_stream:
        f = File({})
        f._download_url = "http://example.com/download_url/"
        await f.write_to(fp)

    fp.seek(0)
    assert file_content == fp.read()
    expected = call('GET', 'http://example.com/download_url/')
    assert expected in mock_stream.mock_calls


@pytest.mark.asyncio
async def test_file_with_new_api():
    # check we use streaming mode to fetch files
    fp = io.BytesIO(b"")
    fp.mode = "b"
    file_content = b"hello world"

    web_url = "http://example.com/download_url/"
    api_url = "http://example.com/upload_url/"

    def fake_stream(method, url):
        if url == web_url:
            raise UnauthorizedException()
        else:
            res = FakeResponse(200, {})
        res.raw = file_content
        return FutureStreamResponse(res)

    with patch.object(File, "_stream", side_effect=fake_stream) as mock_stream:
        f = File({})
        f._download_url = web_url
        f._upload_url = api_url
        await f.write_to(fp)

    fp.seek(0)
    assert file_content == fp.read()
    expected = call('GET', 'http://example.com/download_url/')
    assert expected in mock_stream.mock_calls


@pytest.mark.asyncio
async def test_remove_file_failed():
    f = File({})
    f.path = 'some/path'
    f._delete_url = 'http://delete.me/uri'
    f._delete = MagicMock(return_value=FutureFakeResponse(404, {'data': {}}))

    with pytest.raises(RuntimeError) as e:
        await f.remove()

    assert f._delete.called

    assert 'Could not delete' in e.value.args[0]


@pytest.mark.asyncio
async def test_move_file_to_dir():
    f = File({})
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(201, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    await f.move_to('osfclient', folder)

    f._post.assert_called_once_with('http://move.me/uri',
                                    json={'action': 'move', 'path': 'sample/'})


@pytest.mark.asyncio
async def test_move_file_to_specified_dir_and_file():
    f = File({})
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(201, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    await f.move_to('osfclient', folder, to_filename='newname')

    f._post.assert_called_once_with('http://move.me/uri',
                                    json={'action': 'move', 'path': 'sample/',
                                          'rename': 'newname'})


@pytest.mark.asyncio
async def test_move_file_to_specified_file():
    f = File({})
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(201, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    await f.move_to('osfclient', folder, to_filename='newname')

    f._post.assert_called_once_with('http://move.me/uri',
                                    json={'action': 'move', 'path': 'sample/',
                                          'rename': 'newname'})


@pytest.mark.asyncio
async def test_force_move_file():
    f = File({})
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(201, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    await f.move_to('osfclient', folder, force=True)

    f._post.assert_called_once_with('http://move.me/uri',
                                    json={'action': 'move', 'path': 'sample/',
                                          'conflict': 'replace'})


@pytest.mark.asyncio
async def test_move_file_failed():
    f = File({})
    f.path = 'some/path'
    f._move_url = 'http://move.me/uri'
    f._post = MagicMock(return_value=FutureFakeResponse(204, {'data': {}}))

    folder = Folder({})
    folder.path = 'sample/'

    with pytest.raises(RuntimeError) as e:
        await f.move_to('osfclient', folder)

    assert f._post.called

    assert 'Could not move' in e.value.args[0]
