import os
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
        kwargs_ = self.modify_kwargs(kwargs)
        return super(OSFSession, self).stream(method, url, *args, **kwargs_)

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
