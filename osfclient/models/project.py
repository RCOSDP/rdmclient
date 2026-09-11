from .core import OSFCore
from .storage import Storage


class Project(OSFCore):
    def _update_attributes(self, project):
        """Update attributes from JSON response.

        For the purpose of speeding up the process, project information is not obtained.
        The following data is received as dummy data.

        {
            'data': {
                'id': 'xxxxx',
                'reltionships': {
                    'files': {
                        'links': {
                            'related': {
                                'href': 'https://api.osf.io/v2/nodes/xxxxx/files/'
                            }
                        }
                    }
                }
            }
        }
        """
        if not project:
            return

        project = project['data']
        self.id = self._get_attribute(project, 'id')

        storages = ['relationships', 'files', 'links', 'related', 'href']
        self._storages_url = self._get_attribute(project, *storages)

    def __str__(self):
        return '<Project [{0}]>'.format(self.id)

    async def storage(self, provider='osfstorage'):
        """Return storage `provider`."""
        async for store in self.storages:
            if store.provider == provider:
                return store

        raise RuntimeError("Project has no storage "
                           "provider '{}'".format(provider))

    @property
    async def storages(self):
        """Iterate over all storages for this projects."""
        url = self._storages_url
        while url:
            response = self._json(await self._get(url), 200)
            for store in response['data']:
                yield Storage(store, self.session)
            url = response['links']['next']
