from .core import OSFCore


class Addon(OSFCore):
    def _update_attributes(self, addon):
        self.id = self._get_attribute(addon, 'id')
        self.name = self._get_attribute(addon, 'attributes', 'name')
        self.categories = self._get_attribute(addon, 'attributes', 'categories')

    def __str__(self):
        return '<Addon [{0}]>'.format(self.id)
