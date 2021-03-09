from mock import patch
import pytest

from osfclient.models import OSFCore
from osfclient.models import Project
from osfclient.models import Storage

from osfclient.tests import fake_responses
from osfclient.tests.mocks import FakeResponse


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_invalid_storage(OSFCore_get):
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2//nodes/f3szh/files/'

    response = FakeResponse(200, fake_responses.storage_node('f3szh'))
    OSFCore_get.return_value = response

    with pytest.raises(RuntimeError):
        await project.storage('does-not-exist')

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2//nodes/f3szh/files/')


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_valid_storage(OSFCore_get):
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2//nodes/f3szh/files/'

    response = FakeResponse(200, fake_responses.storage_node('f3szh'))
    OSFCore_get.return_value = response

    storage = await project.storage('osfstorage')

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2//nodes/f3szh/files/')
    assert isinstance(storage, Storage)


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_iterate_storages(OSFCore_get):
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2//nodes/f3szh/files/'

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
        'https://api.osf.io/v2//nodes/f3szh/files/')


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_pass_down_session_to_storage(OSFCore_get):
    # check that `self.session` is passed to newly created OSFCore instances
    project = Project({})
    project._storages_url = 'https://api.osf.io/v2//nodes/f3szh/files/'

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
    project._storages_url = 'https://api.osf.io/v2//nodes/f3szh/files/'

    store_json = fake_responses.storage_node('f3szh')
    response = FakeResponse(200, store_json)
    OSFCore_get.return_value = response

    async for store in project.storages:
        assert store.session == project.session
