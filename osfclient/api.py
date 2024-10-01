from .exceptions import OSFException
from .models import OSFCore
from .models import Project


class OSF(OSFCore):
    """Interact with the Open Science Framework.

    This is the main point of contact for interactions with the
    OSF. Use the methods of this class to find projects, login
    to the OSF, etc.
    """
    def __init__(self, token=None, base_url=None):
        super(OSF, self).__init__({})
        if base_url is not None:
            self.session.set_endpoint(base_url)
        if token is not None:
            self.login_by_token(token)

    async def aclose(self):
        await self.session.aclose()

    def login_by_token(self, token):
        """Login user for protected API calls using Access Token."""
        self.session.token_auth(token)

    async def project(self, project_id):
        """Fetch project `project_id`.

        GakuNin RDM assumes only node as a project (not including registrations),
        so it does not acquire GUID information.
        """
        url = self._build_url('nodes', project_id, 'files')
        return Project({
            'data': {
                'id': project_id,
                'relationships': {
                    'files': {
                        'links': {
                            'related': {
                                'href': url
                            }
                        }
                    }
                }
            }
        }, self.session)

    @property
    def token(self):
        if 'Authorization' not in self.session.headers:
            return None
        auth = self.session.headers['Authorization']
        if not auth.startswith('Bearer '):
            return None
        return auth.split()[-1]

    @property
    def has_auth(self):
        if self.token is not None:
            return True
        return False
