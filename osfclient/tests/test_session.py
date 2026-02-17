import asyncio
from mock import patch, MagicMock, AsyncMock

import pytest

from osfclient.models import OSFSession
from osfclient.exceptions import UnauthorizedException


def test_token_auth():
    session = OSFSession()
    session.token_auth('0123456789abcd')
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


# Tests for stream method with redirect handling

@pytest.mark.asyncio
@patch('osfclient.models.session.httpx.AsyncClient.stream')
async def test_stream_no_redirect(mock_stream):
    """When response is 200 OK, yield response directly without redirect handling."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}

    mock_stream.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream.return_value.__aexit__ = AsyncMock(return_value=None)

    session = OSFSession()
    async with session.stream('GET', 'http://localhost:7777/download') as response:
        assert response.status_code == 200
        assert response is mock_response


@pytest.mark.asyncio
@patch('osfclient.models.session.httpx.AsyncClient')
@patch('osfclient.models.session.httpx.AsyncClient.stream')
async def test_stream_redirect(mock_parent_stream, mock_client_class):
    """When response is a redirect, follow with clean headers."""
    # Mock the initial response (302 redirect)
    mock_initial_response = MagicMock()
    mock_initial_response.status_code = 302
    mock_initial_response.headers = {'location': 'https://s3.amazonaws.com/bucket/file?Signature=xxx'}

    mock_parent_stream.return_value.__aenter__ = AsyncMock(return_value=mock_initial_response)
    mock_parent_stream.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock the redirect response (200 OK with content)
    mock_redirect_response = MagicMock()
    mock_redirect_response.status_code = 200

    mock_redirect_stream = MagicMock()
    mock_redirect_stream.return_value.__aenter__ = AsyncMock(return_value=mock_redirect_response)
    mock_redirect_stream.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_client_instance = MagicMock()
    mock_client_instance.stream = mock_redirect_stream
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    mock_client_class.return_value = mock_client_instance

    session = OSFSession()
    async with session.stream('GET', 'http://localhost:7777/download') as response:
        assert response.status_code == 200
        assert response is mock_redirect_response

    # Verify clean headers are used (no Content-Type, no Accept)
    call_args = mock_redirect_stream.call_args
    headers = call_args.kwargs.get('headers', {})
    assert 'User-Agent' in headers
    assert 'Accept-Charset' in headers
    assert 'Content-Type' not in headers
    assert 'Accept' not in headers


@pytest.mark.asyncio
@patch('osfclient.models.session.httpx.AsyncClient')
@patch('osfclient.models.session.httpx.AsyncClient.stream')
async def test_stream_redirect_headers_not_forwarded(mock_parent_stream, mock_client_class):
    """Verify that API-specific headers (Content-Type, Accept, Authorization) are NOT forwarded on redirect."""
    # Mock the initial response (302 redirect)
    mock_initial_response = MagicMock()
    mock_initial_response.status_code = 302
    mock_initial_response.headers = {'location': 'https://s3.amazonaws.com/bucket/file'}

    mock_parent_stream.return_value.__aenter__ = AsyncMock(return_value=mock_initial_response)
    mock_parent_stream.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock the redirect response (200 OK)
    mock_redirect_response = MagicMock()
    mock_redirect_response.status_code = 200

    mock_redirect_stream = MagicMock()
    mock_redirect_stream.return_value.__aenter__ = AsyncMock(return_value=mock_redirect_response)
    mock_redirect_stream.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_client_instance = MagicMock()
    mock_client_instance.stream = mock_redirect_stream
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    mock_client_class.return_value = mock_client_instance

    session = OSFSession()
    # Add Authorization header
    session.token_auth('test-token')

    async with session.stream('GET', 'http://localhost:7777/download') as response:
        pass

    # Verify headers passed to redirect request
    call_args = mock_redirect_stream.call_args
    headers = call_args.kwargs.get('headers', {})

    # Verify headers that SHOULD be present
    assert 'User-Agent' in headers
    assert headers['User-Agent'] == 'osfclient v0.0.1'
    assert 'Accept-Charset' in headers

    # Verify headers that MUST NOT be present (API-specific headers)
    assert 'Content-Type' not in headers
    assert 'Accept' not in headers
    assert 'Authorization' not in headers
