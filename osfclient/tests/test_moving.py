"""Test `osf move` command"""

import pytest

from mock import call
from mock import patch

from osfclient import OSF
from osfclient.cli import move

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
            await move(args)

    expected = 'move a file you need to provide a token'
    assert expected in e.value.args[0]


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_file_to_dir(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a/a',
                    target='osfstorage/c/')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        mock_calls = list(f.mock_calls)
        if f._path_mock.return_value == '/a/a/a':
            assert call.move_to('osfstorage',
                                [f for f in MockStorage.folders
                                 if f.path == '/c'][0],
                                to_filename=None,
                                force=False) in mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_file_to_sub_dir(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a/a',
                    target='osfstorage/c/c/')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        mock_calls = list(f.mock_calls)
        if f._path_mock.return_value == '/a/a/a':
            assert call.move_to('osfstorage',
                                [f for f in MockStorage.folders
                                 if f.path == '/c/c'][0],
                                to_filename=None,
                                force=False) in mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_file_to_file(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a/a',
                    target='osfstorage/c/newfile')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        mock_calls = list(f.mock_calls)
        if f._path_mock.return_value == '/a/a/a':
            assert call.move_to('osfstorage',
                                [f for f in MockStorage.folders
                                 if f.path == '/c'][0],
                                to_filename='newfile',
                                force=False) in mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_file_to_root(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a/a',
                    target='osfstorage/')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        if f._path_mock.return_value == '/a/a/a':
            assert call.move_to('osfstorage',
                                MockStorage,
                                to_filename=None,
                                force=False) in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_file_to_file_on_root(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a/a',
                    target='osfstorage/newfile')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        if f._path_mock.return_value == '/a/a/a':
            assert call.move_to('osfstorage',
                                MockStorage,
                                to_filename='newfile',
                                force=False) in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_folder_to_dir(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a',
                    target='osfstorage/c/')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.folders:
        mock_calls = list(f.mock_calls)
        if f._path_mock.return_value == '/a/a':
            assert call.move_to('osfstorage',
                                [f for f in MockStorage.folders
                                 if f.path == '/c'][0],
                                to_foldername=None,
                                force=False) in mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_folder_to_sub_dir(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a',
                    target='osfstorage/c/c/')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.folders:
        mock_calls = list(f.mock_calls)
        if f._path_mock.return_value == '/a/a':
            assert call.move_to('osfstorage',
                                [f for f in MockStorage.folders
                                 if f.path == '/c/c'][0],
                                to_foldername=None,
                                force=False) in mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_folder_to_newfolder(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a',
                    target='osfstorage/c/newfolder')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.folders:
        mock_calls = list(f.mock_calls)
        if f._path_mock.return_value == '/a/a':
            assert call.move_to('osfstorage',
                                [f for f in MockStorage.folders
                                 if f.path == '/c'][0],
                                to_foldername='newfolder',
                                force=False) in mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_folder_to_sub_newfolder(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a',
                    target='osfstorage/c/c/newfolder')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.folders:
        mock_calls = list(f.mock_calls)
        if f._path_mock.return_value == '/a/a':
            assert call.move_to('osfstorage',
                                [f for f in MockStorage.folders
                                 if f.path == '/c/c'][0],
                                to_foldername='newfolder',
                                force=False) in mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_folder_to_root(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a',
                    target='osfstorage/')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.folders:
        if f._path_mock.return_value == '/a/a':
            assert call.move_to('osfstorage',
                                MockStorage,
                                to_foldername=None,
                                force=False) in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_move_folder_to_folder_on_root(OSF_project):
    args = MockArgs(project='1234', source='osfstorage/a/a',
                    target='osfstorage/newfolder')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
        await move(args)

    OSF_project.assert_called_once_with('1234')

    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.folders:
        if f._path_mock.return_value == '/a/a':
            assert call.move_to('osfstorage',
                                MockStorage,
                                to_foldername='newfolder',
                                force=False) in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_wrong_storage_name(OSF_project):
    args = MockArgs(project='1234',
                    source='DOESNTEXIST/a/a/a', target='osfstorage/c/')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with pytest.raises(SystemExit) as e:
        with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
            await move(args)

    expected = 'No files found to move.'
    assert expected in e.value.args[0]

    OSF_project.assert_called_once_with('1234')

    # the mock storage is called osfstorage, so we should not call remove()
    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        if f._path_mock.return_value == '/a/a/a':
            assert call.move_to('osfstorage',
                                'c/',
                                force=False) not in f.mock_calls


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_non_existant_file(OSF_project):
    args = MockArgs(project='1234',
                    source='osfstorage/DOESNTEXIST/a', target='osfstorage/c/')

    def simple_getenv(key, default=None):
        if key == 'OSF_TOKEN':
            return 'secret'
        return default

    with pytest.raises(SystemExit) as e:
        with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
            await move(args)

    expected = 'No files found to move.'
    assert expected in e.value.args[0]

    OSF_project.assert_called_once_with('1234')

    # check that all files in osfstorage are visited but non get deleted
    MockProject = OSF_project.return_value
    MockStorage = await MockProject._storage_mock.return_value
    for f in MockStorage.files:
        assert f._path_mock.called
        assert call.move_to('osfstorage',
                            'c/',
                            force=False) not in f.mock_calls
