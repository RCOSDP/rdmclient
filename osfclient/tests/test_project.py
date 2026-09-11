from mock import patch
import pytest

from osfclient import OSF
from osfclient.models import OSFCore
from osfclient.models import Project
from osfclient.models import Storage
from osfclient.utils import split_storage

from osfclient.tests import fake_responses
from osfclient.tests.mocks import FakeResponse


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_invalid_storage(OSFCore_get):
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2/nodes/f3szh/files/'

    response = FakeResponse(200, fake_responses.storage_node('f3szh'))
    OSFCore_get.return_value = response

    with pytest.raises(RuntimeError):
        await project.storage('does-not-exist')

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2/nodes/f3szh/files/')


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_valid_storage(OSFCore_get):
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2/nodes/f3szh/files/'

    response = FakeResponse(200, fake_responses.storage_node('f3szh'))
    OSFCore_get.return_value = response

    storage = await project.storage('osfstorage')

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2/nodes/f3szh/files/')
    assert isinstance(storage, Storage)


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_iterate_storages(OSFCore_get):
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2/nodes/f3szh/files/'

    store_json = fake_responses.storage_node('f3szh',
                                             ['osfstorage', 'github'])
    response = FakeResponse(200, store_json)
    OSFCore_get.return_value = response

    stores = []
    async for s in project.storages:
        stores.append(s)

    assert len(stores) == 2
    for store in stores:
        assert isinstance(store, Storage)

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2/nodes/f3szh/files/')


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_pass_down_session_to_storage(OSFCore_get):
    # check that `self.session` is passed to newly created OSFCore instances
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2/nodes/f3szh/files/'

    store_json = fake_responses.storage_node('f3szh')
    response = FakeResponse(200, store_json)
    OSFCore_get.return_value = response

    store = await project.storage()

    assert store.session == project.session


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_pass_down_session_to_storages(OSFCore_get):
    # as previous test but for multiple storages
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2/nodes/f3szh/files/'

    store_json = fake_responses.storage_node('f3szh')
    response = FakeResponse(200, store_json)
    OSFCore_get.return_value = response

    async for store in project.storages:
        assert store.session == project.session


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_resolve_storage_on_later_page(OSFCore_get):
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2/nodes/f3szh/files/'
    next_url = project._storages_url + '?page=2'
    first = fake_responses.storage_node('f3szh', ['osfstorage'])
    first['links']['next'] = next_url
    second = fake_responses.storage_node('f3szh', ['new-provider'])
    second['data'][0]['attributes']['name'] = 'A display name'
    OSFCore_get.side_effect = [FakeResponse(200, first), FakeResponse(200, second)]

    store, path = await split_storage('/new-provider/folder/file.txt', OSF(), project)

    assert store.provider == 'new-provider'
    assert store.name == 'A display name'
    assert store.session is project.session
    assert path == 'folder/file.txt'
    assert [c.args[0] for c in OSFCore_get.call_args_list] == [
        project._storages_url, next_url]


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_resolve_storage_propagates_api_error(OSFCore_get):
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2/nodes/f3szh/files/'
    first = fake_responses.storage_node('f3szh', ['osfstorage'])
    first['links']['next'] = project._storages_url + '?page=2'
    OSFCore_get.side_effect = [FakeResponse(200, first), FakeResponse(403, {})]

    with pytest.raises(RuntimeError, match='403'):
        await split_storage('new-provider/file.txt', OSF(), project)


@pytest.mark.asyncio
@pytest.mark.parametrize('missing_field', ['links', 'next'])
@patch.object(OSFCore, '_get')
async def test_resolve_storage_rejects_missing_pagination(OSFCore_get,
                                                        missing_field):
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2/nodes/f3szh/files/'
    response = fake_responses.storage_node('f3szh', ['osfstorage'])
    if missing_field == 'links':
        del response['links']
    else:
        del response['links']['next']
    OSFCore_get.return_value = FakeResponse(200, response)

    with pytest.raises(KeyError, match=missing_field):
        await split_storage('folder/file.txt', OSF(), project)
