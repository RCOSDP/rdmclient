import numbers
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

from .session import OSFSession


# Base class for all models and the user facing API object
class OSFCore(object):
    def __init__(self, json, session=None):
        if session is None:
            self.session = OSFSession()
        else:
            self.session = session

        self._update_attributes(json)

    def _update_attributes(self, json):
        pass

    def _build_url(self, *args):
        return self.session.build_url(*args)

    async def _get(self, url, *args, **kwargs):
        return await self.session.get(url, *args, **kwargs)

    def _stream(self, method, url, *args, **kwargs):
        return self.session.stream(method, url, *args, **kwargs)

    async def _put(self, url, *args, **kwargs):
        return await self.session.put(url, *args, **kwargs)

    async def _post(self, url, *args, **kwargs):
        return await self.session.post(url, *args, **kwargs)

    async def _delete(self, url, *args, **kwargs):
        return await self.session.delete(url, *args, **kwargs)

    def _get_attribute(self, json, *keys, **kwargs):
        # pick value out of a (nested) dictionary/JSON
        # `keys` is a list of keys
        # XXX what should happen if a key doesn't match half way down
        # XXX traversing the list of keys?
        value = json
        try:
            for key in keys:
                value = value[key]

        except KeyError:
            default = kwargs.get('default')
            if default is not None:
                return default
            else:
                raise

        return value

    def _json(self, response, status_code):
        """Extract JSON from response if `status_code` matches."""
        if isinstance(status_code, numbers.Integral):
            status_code = (status_code,)

        if response.status_code in status_code:
            return response.json()
        else:
            raise RuntimeError("Response has status "
                               "code {} not {}".format(response.status_code,
                                                       status_code))

    async def _follow_next(self, url):
        """Follow the 'next' link on paginated results."""
        response = self._json(await self._get(url), 200)
        yield response['data']

        next_token = response.get('next_token', None)
        while next_token is not None:
            next_url = self._ensure_query_string(url, next_token=next_token)
            response = self._json(await self._get(next_url), 200)
            yield response['data']
            next_token = response.get('next_token', None)

    def _ensure_query_string(self, url: str, **kwargs) -> str:
        """Ensure that the URL has the query string parameters."""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query.update(kwargs)
        new_query = urlencode(query, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
