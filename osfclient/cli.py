"""Command line interface to the OSF

These functions implement the functionality of the command-line interface.
"""
from __future__ import print_function

from functools import wraps
import os
import sys

import aiofiles
from six.moves import configparser
from six.moves import input

from tqdm import tqdm
import dateutil.parser
from tzlocal import get_localzone

from .api import OSF
from .exceptions import UnauthorizedException
from .utils import (
    norm_remote_path, split_storage, makedirs, checksum_path,
    is_folder, flatten, find_ancestral_folder, find_by_path, filter_by_path_pattern,
)


def config_from_file():
    if os.path.exists(".osfcli.config"):
        config_ = configparser.ConfigParser()
        config_.read(".osfcli.config")

        # for python2 compatibility
        config = dict(config_.items('osf'))

    else:
        config = {}

    return config


def config_from_env(config):
    username = os.getenv("OSF_USERNAME")
    if username is not None:
        config['username'] = username

    project = os.getenv("OSF_PROJECT")
    if project is not None:
        config['project'] = project

    return config


def _get_base_url(args, config):
    if args.base_url is None:
        base_url = config.get('base_url')
    else:
        base_url = args.base_url
    return base_url


def _get_token():
    return os.getenv('OSF_TOKEN')


def _setup_osf(args):
    # Command line options have precedence over environment variables,
    # which have precedence over the config file.
    config = config_from_env(config_from_file())

    project = config.get('project')
    if args.project is None:
        args.project = project
    # still None? We are in trouble
    if args.project is None:
        sys.exit('You have to specify a project ID via the command line,'
                 ' configuration file or environment variable.')

    base_url = _get_base_url(args, config)
    token = _get_token()

    return OSF(token=token, base_url=base_url)


def might_need_auth(f):
    """Decorate a CLI function that might require authentication.

    Catches any UnauthorizedException raised, prints a helpful message and
    then exits.
    """
    @wraps(f)
    def wrapper(cli_args):
        try:
            return_value = f(cli_args)
        except UnauthorizedException as e:
            token = _get_token()

            if token is None:
                sys.exit("Please set a token "
                         "(run `osf -h` for details).")
            else:
                sys.exit("You are not authorized to access this project.")

        return return_value

    return wrapper


def init(args):
    """Initialize or edit an existing .osfcli.config file."""
    # reading existing config file, convert to configparser object
    config = config_from_file()
    config_ = configparser.ConfigParser()
    config_.add_section('osf')
    if 'username' not in config.keys():
        config_.set('osf', 'username', '')
    else:
        config_.set('osf', 'username', config['username'])
    if 'project' not in config.keys():
        config_.set('osf', 'project', '')
    else:
        config_.set('osf', 'project', config['project'])

    # now we can start asking for new values
    print('Provide a username for the config file [current username: {}]:'.format(
          config_.get('osf', 'username')))
    username = input()
    if username:
        config_.set('osf', 'username', username)

    print('Provide a project for the config file [current project: {}]:'.format(
          config_.get('osf', 'project')))
    project = input()
    if project:
        config_.set('osf', 'project', project)

    cfgfile = open(".osfcli.config", "w")
    config_.write(cfgfile)
    cfgfile.close()


@might_need_auth
async def clone(args):
    """Copy all files from all storages of a project.

    The output directory defaults to the current directory.

    If the project is private you need to specify a username or token.

    If args.update is True, overwrite any existing local files only if local and
    remote files differ.
    """
    osf = _setup_osf(args)
    project = await osf.project(args.project)
    output_dir = args.project
    if args.output is not None:
        output_dir = args.output

    with tqdm(unit='files') as pbar:
        async for store in project.storages:
            prefix = os.path.join(output_dir, store.name)

            async for file_ in flatten(store):
                if is_folder(file_):
                    continue
                path = file_.path
                if path.startswith('/'):
                    path = path[1:]

                path = os.path.join(prefix, path)
                if os.path.exists(path) and args.update:
                    if await checksum_path(path) == file_.hashes.get('md5'):
                        continue
                directory, _ = os.path.split(path)
                makedirs(directory, exist_ok=True)

                async with aiofiles.open(path, "wb") as f:
                    await file_.write_to(f)

                pbar.update()


@might_need_auth
async def fetch(args):
    """Fetch an individual file from a project.

    The first part of the remote path is interpreted as the name of the
    storage provider. If there is no match the default (osfstorage) is
    used.

    The local path defaults to the name of the remote file.

    If the project is private you need to specify a username or token.

    If args.force is True, write local file even if that file already exists.
    If args.force is False but args.update is True, overwrite an existing local
    file only if local and remote files differ.
    """
    storage, remote_path = split_storage(args.remote)

    local_path = args.local
    if local_path is None:
        _, local_path = os.path.split(remote_path)

    local_path_exists = os.path.exists(local_path)
    if local_path_exists and not args.force and not args.update:
        sys.exit("Local file %s already exists, not overwriting." % local_path)

    directory, _ = os.path.split(local_path)
    if directory:
        makedirs(directory, exist_ok=True)

    osf = _setup_osf(args)
    project = await osf.project(args.project)

    store = await project.storage(storage)
    # only fetching one file so we are done
    file_ = await find_by_path(store, remote_path)
    if file_ is None or is_folder(file_):
        return
    if local_path_exists and not args.force and args.update:
        if file_.hashes.get('md5') == await checksum_path(local_path):
            print("Local file %s already matches remote." % local_path)
            return
    async with aiofiles.open(local_path, 'wb') as fp:
        await file_.write_to(fp)


@might_need_auth
async def list_(args):
    """List all files from all storages for project.

    If the project is private you need to specify a username or token.
    """
    osf = _setup_osf(args)

    project = await osf.project(args.project)
    base_file_path = None
    base_provider = None
    if args.base_path is not None:
        base_path = args.base_path
        if base_path.startswith('/'):
            base_path = base_path[1:]
        base_file_path = base_path[base_path.index('/'):]
        if not base_file_path.endswith('/'):
            base_file_path = base_file_path + '/'
        base_provider = base_path.split('/')[0]

    async for store in project.storages:
        prefix = store.name
        if base_provider is not None and base_provider != prefix:
            continue
        files = filter_by_path_pattern(store, base_file_path)
        async for file_ in files:
            if is_folder(file_):
                continue
            path = file_.path
            if path.startswith('/'):
                path = path[1:]
            full_path = os.path.join(prefix, path)
            if args.long_format:
                if file_.date_modified is not None:
                    modified = dateutil.parser.parse(file_.date_modified)
                    modified = modified.astimezone(get_localzone())
                    smodified = modified.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    smodified = '- -'
                if file_.size is not None:
                    sfsize = str(file_.size)
                else:
                    sfsize = '-'
                print('%s %s %s' % (smodified, sfsize, full_path))
            else:
                print(full_path)
    await osf.aclose()


@might_need_auth
async def upload(args):
    """Upload a new file to an existing project.

    The first part of the remote path is interpreted as the name of the
    storage provider. If there is no match the default (osfstorage) is
    used.

    If the project is private you need to specify a username or token.

    To upload a whole directory (and all its sub-directories) use the `-r`
    command-line option. If your source directory name ends in a / then
    files will be created directly in the remote directory. If it does not
    end in a slash an extra sub-directory with the name of the local directory
    will be created.

    To place contents of local directory `foo` in remote directory `bar/foo`:
    $ osf upload -r foo bar
    To place contents of local directory `foo` in remote directory `bar`:
    $ osf upload -r foo/ bar
    """
    osf = _setup_osf(args)
    if not osf.has_auth:
        sys.exit('To upload a file you need to provide a token.')

    project = await osf.project(args.project)
    storage, remote_path = split_storage(args.destination)

    store = await project.storage(storage)
    if args.recursive:
        if not os.path.isdir(args.source):
            raise RuntimeError("Expected source ({}) to be a directory when "
                               "using recursive mode.".format(args.source))

        # local name of the directory that is being uploaded
        _, dir_name = os.path.split(args.source)

        for root, _, files in os.walk(args.source):
            subdir_path = os.path.relpath(root, args.source)
            for fname in files:
                local_path = os.path.join(root, fname)
                async with aiofiles.open(local_path, 'rb') as fp:
                    # build the remote path + fname
                    name = os.path.join(remote_path, dir_name, subdir_path,
                                        fname)
                    await store.create_file(name, fp, force=args.force,
                                            update=args.update)

    else:
        async with aiofiles.open(args.source, 'rb') as fp:
            await store.create_file(remote_path, fp, force=args.force,
                                    update=args.update)


@might_need_auth
async def makefolder(args):
    """Create a new folder in an existing project.

    The first part of the remote path is interpreted as the name of the
    storage provider. If there is no match the default (osfstorage) is
    used.
    """
    osf = _setup_osf(args)
    if not osf.has_auth:
        sys.exit('To create a folder you need to provide a token.')

    project = await osf.project(args.project)

    storage, remote_path = split_storage(args.target)

    store = await project.storage(storage)
    f = await find_ancestral_folder(store, remote_path)
    if f is None:
        parent = store
        parent_path_segments = []
    else:
        parent = f
        parent_path_segments = norm_remote_path(parent.path).split(os.path.sep)
    remote_path_segments = remote_path.split(os.path.sep)
    for foldername in remote_path_segments[len(parent_path_segments):]:
        parent = await parent.create_folder(foldername)


@might_need_auth
async def remove(args):
    """Remove a file from the project's storage.

    The first part of the remote path is interpreted as the name of the
    storage provider. If there is no match the default (osfstorage) is
    used.
    """
    osf = _setup_osf(args)
    if not osf.has_auth:
        sys.exit('To remove a file you need to provide a token.')

    project = await osf.project(args.project)

    storage, remote_path = split_storage(args.target)

    store = await project.storage(storage)
    f = await find_by_path(store, remote_path)
    if f is None:
        sys.exit('No files found to remove.')
    await f.remove()


@might_need_auth
async def move(args):
    """Move a file to specified location on the project's storage.

    The first part of the paths is interpreted as the name of the
    storage provider. If there is no match the default (osfstorage) is
    used.
    """
    osf = _setup_osf(args)
    if not osf.has_auth:
        sys.exit('To move a file you need to provide a token.')

    project = await osf.project(args.project)

    target_storage, target_path = split_storage(args.target, normalize=False)

    if target_path.endswith('/'):
        target_folder_path = target_path[:-1]
        target_filename = None
    elif '/' in target_path:
        sep = target_path.rindex('/')
        target_folder_path = target_path[:sep]
        target_filename = target_path[sep + 1:]
    elif target_path == '':
        target_folder_path = None
        target_filename = None
    else:
        target_folder_path = None
        target_filename = target_path
    target_store = await project.storage(target_storage)
    if target_folder_path is None:
        target_folder = target_store
    else:
        target_folder = await _ensure_folder(target_store, target_folder_path)

    # Move a file
    storage, remote_path = split_storage(args.source)

    store = await project.storage(storage)
    f = await find_by_path(store, remote_path)
    if f is None:
        sys.exit('No files found to move.')
    if is_folder(f):
        await f.move_to(target_storage, target_folder,
                        to_foldername=target_filename, force=args.force)
    else:
        await f.move_to(target_storage, target_folder,
                        to_filename=target_filename, force=args.force)


async def _ensure_folder(store, path):
    folder = await find_by_path(store, path)
    if folder is not None:
        return folder
    if '/' in path:
        parent = await _ensure_folder(store, path[:path.index('/')])
        return await parent.create_folder(path[path.index('/') + 1:])
    else:
        return await store.create_folder(path)
