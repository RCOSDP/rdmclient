"""Test `osf remove` command"""

import pytest

from mock import call
from mock import patch

from osfclient import OSF
from osfclient.cli import remove

from osfclient.tests.mocks import MockArgs
from osfclient.tests.mocks import MockProject


@pytest.mark.asyncio
async def test_anonymous_doesnt_work():
    args = MockArgs(project='1234')
    def simple_getenv(key, default=None):
        return default

    with pytest.raises(SystemExit) as e:
        with patch('osfclient.cli.os.getenv',
                   side_effect=simple_getenv) as mock_getenv:
            await remove(args)

    expected = 'remove a file you need to provide a token'
    assert expected in e.value.args[0]


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_remove_file(OSF_project):
    args = MockArgs(project='1234', target='osfstorage/a/a/a')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await remove(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        if f._path_mock.return_value == '/a/a/a':
            assert call.remove() in f.mock_calls
    for f in MockStorage.folders:
        assert call.remove() not in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_wrong_storage_name(OSF_project):
    args = MockArgs(project='1234', target='DOESNTEXIST/a/a/a')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with pytest.raises(SystemExit) as e:
        with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
            await remove(args)

    expected = 'No files found to remove.'
    assert expected in e.value.args[0]

    OSF_project.assert_called_once_with('1234')

    # the mock storage is called osfstorage, so we should not call remove()
    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        if f._path_mock.return_value == '/a/a/a':
            assert call.remove() not in f.mock_calls
    for f in MockStorage.folders:
        assert call.remove() not in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_non_existant_file(OSF_project):
    args = MockArgs(project='1234',
                    target='osfstorage/DOESNTEXIST/a')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with pytest.raises(SystemExit) as e:
        with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
            await remove(args)

    expected = 'No files found to remove.'
    assert expected in e.value.args[0]

    OSF_project.assert_called_once_with('1234')

    # check that all files in osfstorage are visited but non get deleted
    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        assert f._path_mock.called
        assert call.remove() not in f.mock_calls
    for f in MockStorage.folders:
        assert f._path_mock.called
        assert call.remove() not in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_remove_folder(OSF_project):
    args = MockArgs(project='1234', target='osfstorage/a/a')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await remove(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        assert call.remove() not in f.mock_calls
    for f in MockStorage.folders:
        if f._path_mock.return_value == '/a/a':
            assert call.remove() in f.mock_calls
        else:
            assert call.remove() not in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_remove_folder_with_slash(OSF_project):
    args = MockArgs(project='1234', target='osfstorage/a/a/')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await remove(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        assert call.remove() not in f.mock_calls
    for f in MockStorage.folders:
        if f._path_mock.return_value == '/a/a':
            assert call.remove() in f.mock_calls
        else:
            assert call.remove() not in f.mock_calls
