import os
from contextlib import asynccontextmanager

import httpx

from ..exceptions import UnauthorizedException


def _parse_timeout(timeout, default):
    timeout = timeout.strip()
    if not timeout:
        return default
    return float(timeout)


# rdmclient needs to support uploading large (>GB) files, so
# the timeout period can be set using the OSF_CLIENT_TIMEOUT environment variable.
DEFAULT_TIMEOUT = httpx.Timeout(
    _parse_timeout(os.environ.get('OSF_CLIENT_TIMEOUT', ''), default=30.0),
    read=None
)


class OSFSession(httpx.AsyncClient):
    def __init__(self, timeout=DEFAULT_TIMEOUT):
        """Handle HTTP session related work."""
        super(OSFSession, self).__init__(timeout=timeout)
        self.headers.update({
            # Only accept JSON responses
            'Accept': 'application/vnd.api+json',
            # Only accept UTF-8 encoded data
            'Accept-Charset': 'utf-8',
            # Always send JSON
            'Content-Type': "application/json",
            # Custom User-Agent string
            'User-Agent': 'osfclient v0.0.1',
            })
        self.base_url = 'https://api.osf.io/v2/'

    def set_endpoint(self, base_url):
        self.base_url = base_url

    def token_auth(self, token: str):
        self.headers['Authorization'] = 'Bearer ' + token

    def build_url(self, *args):
        base_url = str(self.base_url)
        base_url = base_url[:-1] if base_url.endswith('/') else base_url
        parts = [base_url]
        parts.extend(args)
        # canonical OSF URLs end with a slash
        return '/'.join(parts) + '/'

    async def put(self, url, *args, **kwargs):
        kwargs_ = self.modify_kwargs(kwargs)
        response = await super(OSFSession, self).put(url, *args, **kwargs_)
        if response.status_code == 401:
            raise UnauthorizedException()
        return response

    def stream(self, method, url, *args, **kwargs):
        """Stream with safe redirect handling.

        When WaterButler returns a redirect to S3 (or other external storage),
        we must not forward Content-Type and Accept headers because they would
        break S3's presigned URL signature validation.
        """
        return self._stream_with_safe_redirect(method, url, *args, **kwargs)

    @asynccontextmanager
    async def _stream_with_safe_redirect(self, method, url, *args, **kwargs):
        """Stream with redirect handling that strips API headers.

        - 301, 302, 303: Follow as GET with minimal headers
        - 307, 308: Raise error (WB providers never use these status codes)
        """
        kwargs_no_redirect = kwargs.copy()
        kwargs_no_redirect.update(dict(follow_redirects=False))

        redirect_location = None
        async with super(OSFSession, self).stream(
            method, url, *args, **kwargs_no_redirect
        ) as response:
            if response.status_code in (301, 302, 303):
                if response.headers.get('location'):
                    redirect_location = response.headers.get('location')
                else:
                    yield response
                    return
            elif response.status_code in (307, 308):
                raise RuntimeError(
                    f"HTTP {response.status_code} redirect is not supported."
                )
            else:
                yield response
                return

        async with self._follow_redirect(redirect_location) as redirected_response:
            yield redirected_response

    @asynccontextmanager
    async def _follow_redirect(self, url: str):
        """Follow a redirect with minimal headers.

        Only sends headers that won't interfere with presigned URL signatures.
        """
        clean_headers = {
            'User-Agent': self.headers.get('User-Agent', 'osfclient v0.0.1'),
            'Accept-Charset': self.headers.get('Accept-Charset', 'utf-8'),
        }

        async with httpx.AsyncClient(timeout=self._timeout) as clean_client:
            async with clean_client.stream('GET', url, headers=clean_headers) as response:
                yield response

    async def get(self, url, *args, **kwargs):
        kwargs_ = self.modify_kwargs(kwargs)
        response = await super(OSFSession, self).get(url, *args, **kwargs_)
        if response.status_code == 401:
            raise UnauthorizedException()
        return response

    def modify_kwargs(self, kwargs):
        if 'follow_redirects' in kwargs:
            return kwargs
        r = kwargs.copy()
        r.update(dict(follow_redirects=True))
        return r
