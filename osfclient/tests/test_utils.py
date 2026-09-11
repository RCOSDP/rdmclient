from types import SimpleNamespace

import pytest
from mock import call, patch, Mock

from osfclient.utils import file_empty
from osfclient.utils import norm_remote_path
from osfclient.utils import makedirs
from osfclient.utils import split_storage
from osfclient.tests.mocks import AsyncIterator, MockAddon, MockStream


@pytest.mark.asyncio
@pytest.mark.parametrize('remote, normalize, provider, path', [
    ('folder/file.txt', True, 'osfstorage', 'folder/file.txt'),
    ('/folder/file.txt', True, 'osfstorage', 'folder/file.txt'),
    ('custom/files/data.txt', True, 'custom', 'files/data.txt'),
    ('/custom/files/data.txt', True, 'custom', 'files/data.txt'),
    ('./custom/files/data.txt', True, 'custom', 'files/data.txt'),
    ('custom/files/../data.txt', True, 'custom', 'data.txt'),
    ('/custom//data.txt', True, 'custom', 'data.txt'),
    ('custom/files/', True, 'custom', 'files'),
    ('/custom/files/', False, 'custom', 'files/'),
    ('custom/', True, 'custom', ''),
    ('custom', True, 'osfstorage', 'custom'),
    ('/custom/', False, 'custom', ''),
    ('osfstorage/custom/file.txt', True, 'osfstorage', 'custom/file.txt'),
    ('github/file.txt', True, 'osfstorage', 'github/file.txt'),
    ('custom-other/file.txt', True, 'osfstorage', 'custom-other/file.txt'),
    ('unconnected', True, 'osfstorage', 'unconnected'),
    ('osfstorage/unconnected/file.txt', True, 'osfstorage',
     'unconnected/file.txt'),
    ('binderhub/notebook.ipynb', True, 'osfstorage', 'binderhub/notebook.ipynb'),
])
async def test_split_storage(remote, normalize, provider, path, monkeypatch):
    # Obsolete environment overrides must not hide connected providers.
    monkeypatch.setenv('KNOWN_PROVIDERS', 'github')
    stores = [SimpleNamespace(provider=name, name='Display name')
              for name in ['osfstorage', 'custom']]
    project = SimpleNamespace(id='1234', storages=AsyncIterator(stores))
    osf = SimpleNamespace(addons=AsyncIterator([
        MockAddon('custom'), MockAddon('unconnected'),
        MockAddon('binderhub', categories=['other'])]))
    store, actual_path = await split_storage(remote, osf, project,
                                             normalize=normalize)
    assert store is stores[['osfstorage', 'custom'].index(provider)]
    assert actual_path == path


@pytest.mark.asyncio
async def test_split_storage_connected_provider_skips_addons():
    stores = [SimpleNamespace(provider=name) for name in ['osfstorage', 'custom']]
    project = SimpleNamespace(id='1234', storages=AsyncIterator(stores))
    osf = SimpleNamespace(addons=AsyncIterator([MockAddon('custom')]))

    store, path = await split_storage('custom/file.txt', osf, project)

    assert store is stores[1]
    assert path == 'file.txt'
    assert not osf.addons.__aiter__.called


@pytest.mark.asyncio
@pytest.mark.parametrize('remote, normalize', [
    ('unconnected/file.txt', True),
    ('/unconnected/file.txt', True),
    ('unconnected/', True),
    ('/unconnected/', False),
])
async def test_split_storage_unconnected_provider(remote, normalize):
    stores = [SimpleNamespace(provider='osfstorage')]
    project = SimpleNamespace(id='1234', storages=AsyncIterator(stores))
    osf = SimpleNamespace(addons=AsyncIterator([
        MockAddon('custom'), MockAddon('unconnected', categories=['citations'])]))

    with pytest.raises(RuntimeError, match=(
            "Storage provider 'unconnected' is not connected to project '1234'")):
        await split_storage(remote, osf, project, normalize=normalize)


@pytest.mark.asyncio
async def test_split_storage_missing_default():
    project = SimpleNamespace(id='1234', storages=AsyncIterator([]))
    osf = SimpleNamespace(addons=AsyncIterator([]))
    with pytest.raises(RuntimeError, match="no storage provider 'osfstorage'"):
        await split_storage('folder/file.txt', osf, project)


def test_norm_remote_path():
    path = 'foo/bar/baz.txt'

    new_path = norm_remote_path(path)
    assert new_path == path

    new_path = norm_remote_path('/' + path)
    assert new_path == path


@patch('osfclient.utils.os.path')
@patch('osfclient.utils.os.makedirs')
def test_makedirs_py2(mock_makedirs, mock_path):
    # pretend to be in python 2 land
    # path already exists, expect to call makedirs and that will raise
    mock_path.exists.return_value = True
    with patch('osfclient.utils.six.PY3', False):
        makedirs('/this/path/exists')

    expected = [call('/this/path/exists', 511)]
    assert expected == mock_makedirs.mock_calls


@patch('osfclient.utils.os.path')
@patch('osfclient.utils.os.makedirs')
def test_makedirs_exist_ok_py2(mock_makedirs, mock_path):
    # pretend to be in python 2 land
    # path already exists, expect NOT to call makedirs as we set exist_ok
    mock_path.exists.return_value = True
    with patch('osfclient.utils.six.PY3', False):
        makedirs('/this/path/exists', exist_ok=True)

    assert not mock_makedirs.called


@patch('osfclient.utils.os.path')
@patch('osfclient.utils.os.makedirs')
def test_makedirs_doesnt_exist_py2(mock_makedirs, mock_path):
    # pretend to be in python 2 land
    mock_path.exists.return_value = False
    with patch('osfclient.utils.six.PY3', False):
        makedirs('/this/path/doesnt/exists')

    expected = [call('/this/path/doesnt/exists', 511)]
    assert expected == mock_makedirs.mock_calls


@patch('osfclient.utils.os.makedirs')
def test_makedirs_py3(mock_makedirs):
    # just check stuff get's forwarded
    with patch('osfclient.utils.six.PY3', True):
        makedirs('/this/path/exists', exist_ok=True)

    expected = [call('/this/path/exists', 511, True)]
    assert expected == mock_makedirs.mock_calls


@pytest.mark.asyncio
async def test_empty_file():
    fake_fp = MockStream('foobar.txt', 'rb', size=1024)
    empty = await file_empty(fake_fp)

    expected = [call.seek(0, 2), call.tell(), call.seek(0)]
    assert expected == fake_fp.mock_calls
    # mocks and calls on mocks always return True, so this should be False
    assert not empty
