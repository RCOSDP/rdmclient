from mock import call, patch
import pytest

from osfclient import OSF
from osfclient.exceptions import OSFException
from osfclient.models import OSFSession
from osfclient.models import OSFCore
from osfclient.models import Project

from osfclient.tests import fake_responses
from osfclient.tests.mocks import FakeResponse


@patch.object(OSFSession, 'token_auth')
def test_login_by_token(session_token_auth):
    osf = OSF()
    assert not session_token_auth.called

    osf.login_by_token('0123456789abcd')
    session_token_auth.assert_called_with('0123456789abcd')


def test_has_auth():
    osf = OSF()
    assert not osf.has_auth

    osf = OSF(token='0123456789abcd')
    assert osf.has_auth


@patch.object(OSFSession, 'set_endpoint')
def test_endpoint(session_set_endpoint):
    osf = OSF()
    assert not session_set_endpoint.called

    osf = OSF(base_url='https://api.test.osf.io/v2/')
    session_set_endpoint.assert_called_with('https://api.test.osf.io/v2/')


@pytest.mark.asyncio
@patch.object(OSFCore, '_get')
async def test_addons(OSFCore_get):
    osf = OSF(base_url='https://api.test.osf.io/v2/')
    first_url = 'https://api.test.osf.io/v2/addons/'
    next_url = first_url + '?page=2'
    first = fake_responses.addons(['s3', 'github'])
    first['links']['next'] = next_url
    second = fake_responses.addons(['binderhub'], categories=['other'])
    OSFCore_get.side_effect = [FakeResponse(200, first),
                               FakeResponse(200, second)]

    addons = [addon async for addon in osf.addons]

    assert [addon.id for addon in addons] == ['s3', 'github', 'binderhub']
    assert [addon.categories for addon in addons] == [
        ['storage'], ['storage'], ['other']]
    assert all(addon.session is osf.session for addon in addons)
    assert OSFCore_get.call_args_list == [call(first_url), call(next_url)]


@pytest.mark.asyncio
@patch.object(OSFCore, '_get', return_value=FakeResponse(403, {}))
async def test_addons_propagates_api_error(OSFCore_get):
    osf = OSF()

    with pytest.raises(RuntimeError, match='403'):
        async for _ in osf.addons:
            pass
