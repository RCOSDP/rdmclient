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
        stores = self._json(await self._get(self._storages_url), 200)
        stores = stores['data']
        for store in stores:
            provides = self._get_attribute(store, 'attributes', 'provider')
            if provides == provider:
                return Storage(store, self.session)

        raise RuntimeError("Project has no storage "
                           "provider '{}'".format(provider))

    @property
    async def storages(self):
        """Iterate over all storages for this projects."""
        stores = self._json(await self._get(self._storages_url), 200)
        stores = stores['data']
        for store in stores:
            yield Storage(store, self.session)
