"""Test `osf fetch` command."""

import pytest

import mock
from mock import call, patch, mock_open

from osfclient import OSF
from osfclient.cli import fetch
from osfclient.models import Storage
from osfclient.utils import find_by_path

from osfclient.tests.mocks import (
    MockProject, MockArgs, is_folder_mock, mock_async_open, MockStream,
)


async def _pick_element_by_index(iterable, index):
    count = 0
    async for element in iterable:
        if count == index:
            return element
        count += 1


@pytest.mark.asyncio
@patch('osfclient.cli.makedirs')
@patch('osfclient.cli.os.path.exists', return_value=False)
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_fetch_file(OSF_project, os_path_exists, os_makedirs):
    # check that `osf fetch` opens the right files with the right name and mode
    args = MockArgs(project='1234', remote='osfstorage/a/a/a')

    mock_open_func = mock_async_open()

    with patch('osfclient.cli.aiofiles.open', mock_open_func):
        with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
            await fetch(args)

    OSF_project.assert_called_once_with('1234')
    # check that the project and the files have been accessed
    store = await _pick_element_by_index(OSF_project.return_value.storages, 0)
    assert store._name_mock.return_value == 'osfstorage'

    # should create a file in the same directory when no local
    # filename is specified
    assert mock.call('a', 'wb') in mock_open_func.mock_calls


@pytest.mark.asyncio
@patch('osfclient.cli.makedirs')
@patch('osfclient.cli.os.path.exists', return_value=False)
@patch('osfclient.cli.OSF.project', return_value=MockProject('1234'))
async def test_fetch_file_local_name_specified(OSF_project, os_path_exists,
                                         os_makedirs):
    # check that `osf fetch` opens the right files with the right name
    # and mode when specifying a local filename
    args = MockArgs(project='1234', remote='osfstorage/a/a/a',
                    local='foobar.txt')

    mock_stream = MockStream('foobar.txt', 'wb')
    mock_open_func = mock_async_open(stream=mock_stream)

    with patch('osfclient.cli.aiofiles.open', mock_open_func):
        with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
            await fetch(args)

    OSF_project.assert_called_once_with('1234')

    # check that the project and the files have been accessed
    project = OSF_project.return_value
    store = await project._storage_mock.return_value
    assert store._name_mock.return_value == 'osfstorage'

    expected = [call._path_mock(), call.write_to(mock_stream), call._path_mock()]
    file = await find_by_path(store, 'a/a/a')
    assert expected == file.mock_calls
    # second file should not have been looked at
    file = await find_by_path(store, 'b/b/b')
    assert [call._path_mock()] == file.mock_calls

    # should create a file in the same directory when no local
    # filename is specified
    assert mock.call('foobar.txt', 'wb') in mock_open_func.mock_calls
    assert not os_makedirs.called


@pytest.mark.asyncio
@patch('osfclient.cli.makedirs')
@patch('osfclient.cli.os.path.exists', return_value=False)
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_fetch_file_local_dir_specified(OSF_project, os_path_exists,
                                        os_makedirs):
    # check that `osf fetch` opens the right files with the right name
    # and mode when specifying a local filename
    args = MockArgs(project='1234', remote='osfstorage/a/a/a',
                    local='subdir/foobar.txt')

    mock_open_func = mock_async_open()

    with patch('osfclient.cli.aiofiles.open', mock_open_func):
        with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
            await fetch(args)

    OSF_project.assert_called_once_with('1234')
    # check that the project and the files have been accessed
    store = await _pick_element_by_index(OSF_project.return_value.storages, 0)
    assert store._name_mock.return_value == 'osfstorage'

    assert (mock.call('subdir/foobar.txt', 'wb') in
            mock_open_func.mock_calls)
    assert mock.call('subdir', exist_ok=True) in os_makedirs.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_fetch_local_file_exists(OSF_project):
    # check that `osf fetch` opens the right files with the right name
    # and mode when specifying a local filename
    args = MockArgs(project='1234', remote='osfstorage/a/a/a',
                    local='subdir/foobar.txt')

    def exists(path):
        if path == ".osfcli.config":
            return False
        else:
            return True

    with patch('osfclient.cli.os.path.exists', side_effect=exists):
        with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
            with pytest.raises(SystemExit) as e:
                await fetch(args)

    assert 'already exists, not overwriting' in e.value.args[0]


@pytest.mark.asyncio
@patch('osfclient.cli.makedirs')
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_fetch_local_file_exists_force(OSF_project, os_makedirs):
    # check that `osf fetch --force` overwrites the local files if it exists
    args = MockArgs(project='1234', remote='osfstorage/a/a/a', force=True)

    def exists(path):
        if path == ".osfcli.config":
            return False
        else:
            return True

    mock_open_func = mock_async_open()

    with patch('osfclient.cli.aiofiles.open', mock_open_func):
        with patch('osfclient.cli.os.path.exists', side_effect=exists):
            with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
                await fetch(args)

    OSF_project.assert_called_once_with('1234')
    # check that the project and the files have been accessed
    store = await _pick_element_by_index(OSF_project.return_value.storages, 0)
    assert store._name_mock.return_value == 'osfstorage'

    # should create a file in the same directory when no local
    # filename is specified
    assert mock.call('a', 'wb') in mock_open_func.mock_calls


@pytest.mark.asyncio
@patch('osfclient.cli.makedirs')
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_fetch_local_file_exists_update_files_differ(OSF_project, os_makedirs):
    # check that `osf fetch --update` overwrites an existing local file if it
    # differs from the remote
    args = MockArgs(project='1234', remote='osfstorage/a/a/a', update=True)

    def exists(path):
        if path == ".osfcli.config":
            return False
        else:
            return True

    async def simple_checksum_path(file_path):
        return '1' * 32

    mock_open_func = mock_async_open()

    with patch('osfclient.cli.aiofiles.open', mock_open_func):
        with patch('osfclient.cli.os.path.exists', side_effect=exists):
            with patch('osfclient.cli.checksum_path', side_effect=simple_checksum_path):
                with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
                    await fetch(args)

    OSF_project.assert_called_once_with('1234')
    # check that the project and the files have been accessed
    store = await _pick_element_by_index(OSF_project.return_value.storages, 0)
    assert store._name_mock.return_value == 'osfstorage'

    # should create a file in the same directory when no local
    # filename is specified
    assert mock.call('a', 'wb') in mock_open_func.mock_calls


@pytest.mark.asyncio
@patch('osfclient.cli.makedirs')
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_fetch_local_file_exists_update_files_match(OSF_project, os_makedirs):
    # check that `osf fetch --update` does not overwrite local file if it
    # matches the remote
    args = MockArgs(project='1234', remote='osfstorage/a/a/a', update=True)

    def exists(path):
        if path == ".osfcli.config":
            return False
        else:
            return True

    async def simple_checksum_path(file_path):
        return '0' * 32

    mock_open_func = mock_async_open()

    with patch('osfclient.cli.aiofiles.open', mock_open_func):
        with patch('osfclient.cli.os.path.exists', side_effect=exists):
            with patch('osfclient.cli.checksum_path', side_effect=simple_checksum_path):
                with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
                    await fetch(args)

    OSF_project.assert_called_once_with('1234')
    # check that the project and the files have been accessed
    store = await _pick_element_by_index(OSF_project.return_value.storages, 0)
    assert store._name_mock.return_value == 'osfstorage'

    # should create a file in the same directory when no local
    # filename is specified
    assert mock.call('a', 'wb') not in mock_open_func.mock_calls


@pytest.mark.asyncio
@patch('osfclient.cli.makedirs')
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_fetch_local_file_exists_force_overrides_update(OSF_project, os_makedirs):
    # check that `osf fetch --force --update` overwrites the local file even if
    # it matches the remote file (force overrides update)
    args = MockArgs(project='1234', remote='osfstorage/a/a/a', force=True,
                    update=True)

    def exists(path):
        if path == ".osfcli.config":
            return False
        else:
            return True

    async def simple_checksum_path(file_path):
        return '0' * 32

    mock_open_func = mock_async_open()

    with patch('osfclient.cli.aiofiles.open', mock_open_func):
        with patch('osfclient.cli.os.path.exists', side_effect=exists):
            with patch('osfclient.cli.checksum_path', side_effect=simple_checksum_path):
                with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
                    await fetch(args)

    OSF_project.assert_called_once_with('1234')
    # check that the project and the files have been accessed
    store = await _pick_element_by_index(OSF_project.return_value.storages, 0)
    assert store._name_mock.return_value == 'osfstorage'

    # should create a file in the same directory when no local
    # filename is specified.
    # file should be created even though local matches remote and update is
    # True, because force overrides update
    assert mock.call('a', 'wb') in mock_open_func.mock_calls


@pytest.mark.asyncio
@patch('osfclient.cli.makedirs')
@patch('osfclient.cli.os.path.exists', return_value=False)
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_fetch_last_file(OSF_project, os_path_exists, os_makedirs):
    # check that `osf fetch` opens the right files with the right name and mode
    args = MockArgs(project='1234', remote='osfstorage/b/b/b')

    mock_open_func = mock_async_open()

    with patch('osfclient.cli.aiofiles.open', mock_open_func):
        with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
            await fetch(args)

    OSF_project.assert_called_once_with('1234')
    # check that the project and the files have been accessed
    store = await OSF_project.return_value._storage_mock.return_value
    assert store._name_mock.return_value == 'osfstorage'

    # should create a file in the same directory when no local
    # filename is specified
    assert mock.call('b', 'wb') in mock_open_func.mock_calls
    for f in store.files:
        assert f._path_mock.called


@pytest.mark.asyncio
@patch('osfclient.cli.makedirs')
@patch('osfclient.cli.os.path.exists', return_value=False)
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_fetch_file_with_base_path(OSF_project, os_path_exists, os_makedirs):
    # check that `osf fetch` opens the right files with the right name and mode
    args = MockArgs(project='1234', remote='osfstorage/b/b/b',
                    base_path='osfstorage/b/b/')

    mock_open_func = mock_async_open()

    with patch('osfclient.cli.aiofiles.open', mock_open_func):
        with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
            await fetch(args)

    OSF_project.assert_called_once_with('1234')
    # check that the project and the files have been accessed
    store = await OSF_project.return_value._storage_mock.return_value
    assert store._name_mock.return_value == 'osfstorage'

    # should create a file in the same directory when no local
    # filename is specified
    assert mock.call('b', 'wb') in mock_open_func.mock_calls
    for f in store.files[:-1]:
        assert not f._path_mock.called
    for f in store.files[-1:]:
        assert f._path_mock.called
