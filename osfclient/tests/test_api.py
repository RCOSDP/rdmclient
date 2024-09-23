from mock import call, patch
import pytest

from osfclient import OSF
from osfclient.exceptions import OSFException
from osfclient.models import OSFSession
from osfclient.models import OSFCore
from osfclient.models import Project

from osfclient.tests.fake_responses import project_node, registration_node, fake_node
from osfclient.tests.mocks import FakeResponse


@patch.object(OSFSession, 'basic_auth')
def test_basic_auth(session_basic_auth):
    OSF('joe@example.com', 'secret_password')
    session_basic_auth.assert_called_with('joe@example.com', 'secret_password')


@patch.object(OSFSession, 'basic_auth')
def test_login(session_basic_auth):
    osf = OSF()
    assert not session_basic_auth.called

    osf.login('joe@example.com', 'secret_password')
    session_basic_auth.assert_called_with('joe@example.com', 'secret_password')


@patch.object(OSFSession, 'token_auth')
def test_login_by_token(session_token_auth):
    osf = OSF()
    assert not session_token_auth.called

    osf.login_by_token('0123456789abcd')
    session_token_auth.assert_called_with('0123456789abcd')


def test_has_auth():
    osf = OSF()
    assert not osf.has_auth

    osf = OSF(username='joe@example.com', password='secret_password')
    assert osf.has_auth

    osf = OSF(token='0123456789abcd')
    assert osf.has_auth


@patch.object(OSFSession, 'set_endpoint')
def test_endpoint(session_set_endpoint):
    osf = OSF()
    assert not session_set_endpoint.called

    osf = OSF(base_url='https://api.test.osf.io/v2/')
    session_set_endpoint.assert_called_with('https://api.test.osf.io/v2/')


@pytest.mark.asyncio
@patch.object(OSFCore, '_get', return_value=FakeResponse(200, project_node))
async def test_get_project(OSFCore_get):
    osf = OSF()
    project = await osf.project('f3szh')

    calls = [call('https://api.osf.io/v2/guids/f3szh/'), call('https://api.osf.io/v2/nodes/f3szh/')]
    OSFCore_get.assert_has_calls(calls)
    assert isinstance(project, Project)


@pytest.mark.asyncio
@patch.object(OSFCore, '_get', return_value=FakeResponse(200, registration_node))
async def test_get_registration(OSFCore_get):
    osf = OSF()
    project = await osf.project('f3szh')

    calls = [call('https://api.osf.io/v2/guids/f3szh/'), call('https://api.osf.io/v2/registrations/f3szh/')]
    OSFCore_get.assert_has_calls(calls)
    assert isinstance(project, Project)


@pytest.mark.asyncio
@patch.object(OSFCore, '_get', return_value=FakeResponse(200, fake_node))
async def test_get_fake(OSFCore_get):
    osf = OSF()
    with pytest.raises(OSFException) as exc:
        await osf.project('f3szh')

    assert exc.value.args[0] == 'f3szh is unrecognized type fakes. Clone supports projects and registrations'
    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2/guids/f3szh/'
        )


@pytest.mark.asyncio
@patch.object(OSFCore, '_get', return_value=FakeResponse(404, project_node))
async def test_failed_get_project(OSFCore_get):
    osf = OSF()
    with pytest.raises(RuntimeError):
        await osf.project('f3szh')

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2/guids/f3szh/'
        )


@pytest.mark.asyncio
@patch.object(OSFCore, '_get', return_value=FakeResponse(200, project_node))
async def test_get_project_with_endpoint(OSFCore_get):
    osf = OSF(base_url='https://api.test.osf.io/v2/')
    project = await osf.project('f3szh')

    calls = [call('https://api.test.osf.io/v2/guids/f3szh/'), call('https://api.test.osf.io/v2/nodes/f3szh/')]
    OSFCore_get.assert_has_calls(calls)
    assert isinstance(project, Project)
