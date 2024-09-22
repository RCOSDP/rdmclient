import json


# Use this to fake a response when asking for a project's files/storages
# e.g. project.storages or project.storage()
def storage_node(project_id, storages=['osfstorage']):
    storage = """
    {
        "relationships": {
            "files": {
                "links": {
                    "related": {
                        "href": "https://api.osf.io/v2/nodes/%(project_id)s/files/%(name)s/",
                        "meta": {}
                    }
                }
            }
        },
        "links": {
            "storage_addons": "https://api.osf.io/v2/addons/?filter%%5Bcategories%%5D=storage",
            "upload": "https://files.osf.io/v1/resources/%(project_id)s/providers/%(name)s/",
            "new_folder": "https://files.osf.io/v1/resources/%(project_id)s/providers/%(name)s/?kind=folder"
        },
        "attributes": {
            "node": "%(project_id)s",
            "path": "/",
            "kind": "folder",
            "name": "%(name)s",
            "provider": "%(name)s"
        },
        "type": "files",
        "id": "%(project_id)s:%(name)s"
    }"""
    used_storages = []
    for store in storages:
        used_storages.append(json.loads(storage % {'project_id': project_id,
                                                   'name': store}))

    files = """{
    "data": %(storages)s,
    "links": {
        "first": null,
        "last": null,
        "prev": null,
        "next": null,
        "meta": {
            "total": %(n_storages)s,
            "per_page": 10
        }
    }
    }"""
    return json.loads(files % {'storages': json.dumps(used_storages),
                               'n_storages': len(used_storages)})


def _folder(osf_id, name, storage='osfstorage'):
    template = """{
        "relationships": {
            "files": {
                "links": {
                    "related": {
                        "href": "https://api.osf.io/v2/nodes/9zpcy/files/%(storage)s/%(osf_id)s/",
                        "meta": {}
                    }
                }
            },
            "node": {
                "links": {
                    "related": {
                        "href": "https://api.osf.io/v2/nodes/9zpcy/",
                        "meta": {}
                    }
                }
            }
        },
        "links": {
            "info": "https://api.osf.io/v2/files/%(osf_id)s/",
            "new_folder": "https://files.osf.io/v1/resources/9zpcy/providers/%(storage)s/%(osf_id)s/?kind=folder",
            "self": "https://api.osf.io/v2/files/%(osf_id)s/",
            "move": "https://files.osf.io/v1/resources/9zpcy/providers/%(storage)s/%(osf_id)s/",
            "upload": "https://files.osf.io/v1/resources/9zpcy/providers/%(storage)s/%(osf_id)s/",
            "delete": "https://files.osf.io/v1/resources/9zpcy/providers/%(storage)s/%(osf_id)s/"
        },
        "attributes": {
            "extra": {
                "hashes": {
                    "sha256": null,
                    "md5": null
                }
            },
            "kind": "folder",
            "name": "%(name)s",
            "last_touched": null,
            "materialized": "/%(name)s/",
            "date_modified": null,
            "current_version": 1,
            "delete_allowed": true,
            "date_created": null,
            "provider": "%(storage)s",
            "path": "/%(osf_id)s/",
            "current_user_can_comment": true,
            "guid": null,
            "checkout": null,
            "tags": [],
            "size": null
        },
        "type": "files",
        "id": "%(osf_id)s"
    }"""
    return json.loads(template % dict(osf_id=osf_id, name=name,
                                      storage=storage))


def files_node(project_id, storage, file_names=['hello.txt'],
               file_sizes=None, file_dates_modified=None,
               folder_names=None):
    a_file = """{
    "relationships": {
        "node": {
            "links": {
                "related": {
                    "href": "https://api.osf.io/v2/nodes/%(project_id)s/",
                    "meta": {}
                }
            }
        },
        "versions": {
            "links": {
                "related": {
                    "href": "https://api.osf.io/v2/files/58becc229ad5a101f98293a3/versions/",
                    "meta": {}
                }
            }
        }
    },
    "links": {
        "info": "https://api.osf.io/v2/files/58becc229ad5a101f98293a3/",
        "self": "https://api.osf.io/v2/files/58becc229ad5a101f98293a3/",
        "move": "https://files.osf.io/v1/resources/%(project_id)s/providers/%(storage)s/%(fname)s",
        "upload": "https://files.osf.io/v1/resources/%(project_id)s/providers/%(storage)s/%(fname)s",
        "download": "https://files.osf.io/v1/resources/%(project_id)s/providers/%(storage)s/%(fname)s",
        "delete": "https://files.osf.io/v1/resources/%(project_id)s/providers/%(storage)s/%(fname)s"
    },
    "attributes": {
        "extra": {
            "hashes": {
                "sha256": null,
                "md5": null
            }
        },
        "kind": "file",
        "name": "%(fname)s",
        "last_touched": "2017-03-20T16:24:57.417044",
        "materialized": "/%(fname)s",
        "modified_utc": %(date_modified)s,
        "current_version": 1,
        "created_utc": null,
        "provider": "%(storage)s",
        "path": "/%(fname)s",
        "current_user_can_comment": true,
        "guid": null,
        "checkout": null,
        "tags": [],
        "size": %(fsize)s
    },
    "type": "files",
    "id": "58becc229ad5a101f98293a3"
}"""
    files = []
    if file_dates_modified is None:
        file_dates_modified = ['null' for fname in file_names]
    if file_sizes is None:
        file_sizes = ['null' for fname in file_names]
    for fname, fsize, date_modified in zip(file_names, file_sizes,
                                           file_dates_modified):
        files.append(json.loads(a_file % dict(storage=storage,
                                              fname=fname,
                                              fsize=fsize,
                                              date_modified=date_modified,
                                              project_id=project_id)))

    if folder_names is not None:
        for folder in folder_names:
            files.append(_folder(folder + '123', folder, storage))

    wrapper = """{
    "data": %(files)s,
    "links": {
        "first": null,
        "last": null,
        "prev": null,
        "next": null,
        "meta": {
            "total": %(n_files)s,
            "per_page": %(n_files)s
        }
    }
    }"""
    return json.loads(wrapper % {'files': json.dumps(files),
                                 'n_files': len(files)})
