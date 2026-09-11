"""Test file transfers using providers discovered from the project."""

import pytest
from mock import patch

from osfclient import OSF
from osfclient.cli import fetch, upload, makefolder, remove, move
from osfclient.tests.mocks import (
    AsyncIterator, MockAddon, MockAddons, MockArgs, MockProject, MockStorage,
    MockStream,
    is_folder_mock, mock_async_open,
)
from osfclient.utils import find_by_path


@pytest.mark.asyncio
@pytest.mark.parametrize('provider', [
    's3compatsigv4', 'dropboxbusiness', 'onedrive', 'future-provider',
])
@pytest.mark.parametrize('leading_slash', ['', '/'])
async def test_upload_connected_provider(provider, leading_slash, monkeypatch):
    monkeypatch.delenv('KNOWN_PROVIDERS', raising=False)
    monkeypatch.setenv('OSF_TOKEN', 'secret')
    project = MockProject('1234')
    store = MockStorage(provider)
    project.storages = AsyncIterator([MockStorage('osfstorage'), store])
    prefix = leading_slash + provider + '/'
    args = MockArgs(project='1234', source='local.txt',
                    destination=prefix + 'folder/remote.txt')
    stream = MockStream('local.txt', 'rb')
    open_mock = mock_async_open(stream)

    with patch.object(OSF, 'project', return_value=project):
        with patch('osfclient.cli.aiofiles.open', open_mock):
            await upload(args)

    open_mock.assert_called_once_with('local.txt', 'rb')
    store.create_file.assert_called_once_with(
        'folder/remote.txt', stream, force=False, update=False)


@pytest.mark.asyncio
@pytest.mark.parametrize('provider', [
    's3compatsigv4', 'dropboxbusiness', 'onedrive', 'future-provider',
])
@pytest.mark.parametrize('leading_slash', ['', '/'])
async def test_fetch_connected_provider(provider, leading_slash, monkeypatch,
                                        tmp_path):
    monkeypatch.delenv('KNOWN_PROVIDERS', raising=False)
    monkeypatch.setenv('OSF_TOKEN', 'secret')
    project = MockProject('1234')
    store = MockStorage(provider)
    project.storages = AsyncIterator([MockStorage('osfstorage'), store])
    prefix = leading_slash + provider + '/'
    local = str(tmp_path / 'download.txt')
    args = MockArgs(project='1234', remote=prefix + 'a/a/a', local=local)
    stream = MockStream(local, 'wb')
    open_mock = mock_async_open(stream)

    with patch.object(OSF, 'project', return_value=project):
        with patch('osfclient.cli.aiofiles.open', open_mock):
            with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
                await fetch(args)

    open_mock.assert_called_once_with(local, 'wb')
    file_ = await find_by_path(store, 'a/a/a')
    file_.write_to.assert_called_once_with(stream)


@pytest.mark.asyncio
@pytest.mark.parametrize('command', [makefolder, remove])
async def test_modify_connected_provider(command, monkeypatch):
    monkeypatch.setenv('OSF_TOKEN', 'secret')
    project = MockProject('1234')
    default_store = MockStorage('osfstorage')
    store = MockStorage('future-provider')
    project.storages = AsyncIterator([default_store, store])
    path = 'new-folder' if command is makefolder else 'a/a/a'
    args = MockArgs(project='1234', target='future-provider/' + path)

    with patch.object(OSF, 'project', return_value=project):
        await command(args)

    if command is makefolder:
        store.create_folder.assert_called_once_with('new-folder')
        default_store.create_folder.assert_not_called()
    else:
        file_ = await find_by_path(store, 'a/a/a')
        file_.remove.assert_called_once_with()
        default_file = await find_by_path(default_store, 'a/a/a')
        default_file.remove.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('target_path, folder_path, filename', [
    ('future-target/', None, None),
    ('/future-target/', None, None),
    ('/future-target/c/', 'c', None),
    ('future-target/renamed.txt', None, 'renamed.txt'),
])
async def test_move_between_connected_providers(target_path, folder_path,
                                               filename, monkeypatch):
    monkeypatch.setenv('OSF_TOKEN', 'secret')
    project = MockProject('1234')
    source = MockStorage('future-source')
    target = MockStorage('future-target')
    project.storages = AsyncIterator([source, target])
    args = MockArgs(project='1234', source='/future-source/a/a/a',
                    target=target_path)

    with patch.object(OSF, 'project', return_value=project):
        with patch('osfclient.cli.is_folder', side_effect=is_folder_mock):
            await move(args)

    folder = target if folder_path is None else await find_by_path(
        target, folder_path)
    file_ = await find_by_path(source, 'a/a/a')
    file_.move_to.assert_called_once_with(
        'future-target', folder, to_filename=filename, force=False)


@pytest.mark.asyncio
@pytest.mark.parametrize('command, path_args', [
    (upload, {'source': 'local.txt', 'destination': None}),
    (fetch, {'remote': None}),
    (makefolder, {'target': None}),
    (remove, {'target': None}),
    (move, {'source': None, 'target': 'osfstorage/c/'}),
])
@patch.object(OSF, 'addons', new=MockAddons([
    MockAddon('binderhub', categories=['other']), MockAddon('s3compatsigv4')]))
async def test_unconnected_provider_is_rejected(command, path_args,
                                                monkeypatch):
    monkeypatch.setenv('OSF_TOKEN', 'secret')
    project = MockProject('1234')
    default_store = MockStorage('osfstorage')
    project.storages = AsyncIterator([default_store])
    path_args = {key: 's3compatsigv4/folder/file.txt' if value is None else value
                 for key, value in path_args.items()}
    args = MockArgs(project='1234', **path_args)

    with patch.object(OSF, 'project', return_value=project):
        with pytest.raises(RuntimeError, match=(
                "Storage provider 's3compatsigv4' is not connected to "
                "project '1234'")):
            await command(args)

    default_store.create_file.assert_not_called()
    default_store.create_folder.assert_not_called()
    file_ = await find_by_path(default_store, 'folder/file.txt')
    assert file_ is None
