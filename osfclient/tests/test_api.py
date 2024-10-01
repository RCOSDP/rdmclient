from mock import call, patch
import pytest

from osfclient import OSF
from osfclient.exceptions import OSFException
from osfclient.models import OSFSession
from osfclient.models import OSFCore
from osfclient.models import Project

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
