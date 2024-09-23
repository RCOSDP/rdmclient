import asyncio
from mock import patch
from mock import MagicMock

import pytest

from osfclient.models import OSFSession
from osfclient.exceptions import UnauthorizedException


def test_basic_auth():
    session = OSFSession()
    session.basic_auth('joe@example.com', 'secret_password')
    assert session.auth == ('joe@example.com', 'secret_password')
    assert 'Authorization' not in session.headers


def test_token_auth():
    session = OSFSession()
    session.token_auth('0123456789abcd')
    assert session.auth is None
    assert session.headers['Authorization'] == 'Bearer 0123456789abcd'


def test_basic_build_url():
    session = OSFSession()
    url = session.build_url("some", "path")
    assert url.startswith(str(session.base_url))
    assert url.endswith("/some/path/")


@pytest.mark.asyncio
@patch('osfclient.models.session.httpx.AsyncClient.put')
async def test_unauthorized_put(mock_put):
    mock_response = MagicMock()
    mock_response.status_code = 401

    mock_put.return_value = mock_response

    url = 'http://example.com/foo'

    session = OSFSession()

    with pytest.raises(UnauthorizedException):
        await session.put(url)

    mock_put.assert_called_once_with(url, follow_redirects=True)


@pytest.mark.asyncio
@patch('osfclient.models.session.httpx.AsyncClient.get')
async def test_unauthorized_get(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 401

    mock_get.return_value = mock_response

    url = 'http://example.com/foo'

    session = OSFSession()

    with pytest.raises(UnauthorizedException):
        await session.get(url)

    mock_get.assert_called_once_with(url, follow_redirects=True)


@pytest.mark.asyncio
@patch('osfclient.models.session.httpx.AsyncClient.put')
async def test_put(mock_put):
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_put.return_value = mock_response

    url = 'http://example.com/foo'

    session = OSFSession()

    response = await session.put(url)

    assert response == mock_response
    mock_put.assert_called_once_with(url, follow_redirects=True)


@pytest.mark.asyncio
@patch('osfclient.models.session.httpx.AsyncClient.get')
async def test_get(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_get.return_value = mock_response

    url = 'http://example.com/foo'

    session = OSFSession()

    response = await session.get(url)

    assert response == mock_response
    mock_get.assert_called_once_with(url, follow_redirects=True)
