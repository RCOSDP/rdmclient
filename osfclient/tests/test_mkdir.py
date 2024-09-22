"""Test `osf remove` command"""

import pytest

from mock import call
from mock import patch

from osfclient import OSF
from osfclient.cli import makefolder

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
            await makefolder(args)

    expected = 'create a folder you need to provide a token'
    assert expected in e.value.args[0]


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_make_sub_folder(OSF_project):
    args = MockArgs(project='1234', target='osfstorage/a/new')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await makefolder(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.folders:
        if f._path_mock.return_value == '/a':
            assert call.create_folder('new') in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_make_root_folder(OSF_project):
    args = MockArgs(project='1234', target='osfstorage/new')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await makefolder(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    assert call.create_folder('new') in MockStorage.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_make_recursive_sub_folder(OSF_project):
    args = MockArgs(project='1234', target='osfstorage/a/new1/new2')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await makefolder(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.folders:
        if f._path_mock.return_value == '/a':
            assert call.create_folder('new1') in f.mock_calls
            assert call.create_folder('new2') in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_make_recursive_root_folder(OSF_project):
    args = MockArgs(project='1234', target='osfstorage/new1/new2')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await makefolder(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    assert call.create_folder('new1') in MockStorage.mock_calls
    assert call.create_folder('new1') in MockStorage.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_wrong_storage_name(OSF_project):
    args = MockArgs(project='1234', target='DOESNTEXIST/a/a/a')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await makefolder(args)

    OSF_project.assert_called_once_with('1234')

    # the mock storage is called osfstorage, so we should not call remove()
    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        if f._path_mock.return_value == '/a/a/a':
            assert call.remove() not in f.mock_calls
    for f in MockStorage.folders:
        assert call.remove() not in f.mock_calls
