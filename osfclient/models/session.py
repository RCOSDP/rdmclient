import httpx

from ..exceptions import UnauthorizedException


class OSFSession(httpx.AsyncClient):
    auth = None

    def __init__(self):
        """Handle HTTP session related work."""
        super(OSFSession, self).__init__()
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

    def basic_auth(self, username, password):
        self.auth = (username, password)
        if 'Authorization' in self.headers:
            self.headers.pop('Authorization')

    def token_auth(self, token):
        self.headers['Authorization'] = 'Bearer ' + token

    def build_url(self, *args):
        base_url = str(self.base_url)
        base_url = base_url[:-1] if base_url.endswith('/') else base_url
        parts = [base_url]
        parts.extend(args)
        # canonical OSF URLs end with a slash
        return '/'.join(parts) + '/'

    async def put(self, url, *args, **kwargs):
        response = await super(OSFSession, self).put(url, *args, **kwargs)
        if response.status_code == 401:
            raise UnauthorizedException()
        return response

    async def get(self, url, *args, **kwargs):
        response = await super(OSFSession, self).get(url, *args, **kwargs)
        if response.status_code == 401:
            raise UnauthorizedException()
        return response
