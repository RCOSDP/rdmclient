"""Test `osf upload` command"""

import mock
from mock import call
from mock import patch
from mock import mock_open

import pytest

from osfclient import OSF
from osfclient.cli import upload

from osfclient.tests.mocks import MockArgs
from osfclient.tests.mocks import MockProject
from osfclient.tests.mocks import mock_async_open, MockStream


@pytest.mark.asyncio
async def test_anonymous_doesnt_work():
    args = MockArgs(project='1234')
    def simple_getenv(key, default=None):
        return default

    with pytest.raises(SystemExit) as e:
        with patch('osfclient.cli.os.getenv',
                   side_effect=simple_getenv) as mock_getenv:
            await upload(args)

    expected = 'upload a file you need to provide a username and password'
    assert expected in e.value.args[0]


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_select_project(OSF_project):
    args = MockArgs(username='joe@example.com',
                    project='1234',
                    source='foo/bar.txt',
                    destination='bar/bar/foo.txt')

    def simple_getenv(key, default=None):
        if key == 'OSF_PASSWORD':
            return 'secret'
        return default

    fake_stream = MockStream('foo/bar.txt', 'rb')
    fake_open = mock_async_open(fake_stream)

    with patch('osfclient.cli.aiofiles.open', fake_open):
        with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
            await upload(args)

    assert call('foo/bar.txt', 'rb') in fake_open.mock_calls

    # the mock project created by calling OSF().project()
    fake_project = OSF_project.return_value
    expected = [call('osfstorage')]
    assert fake_project._storage_mock.mock_calls == expected
    # assert fake_project.mock_calls == expected

    expected = [call.create_file('bar/bar/foo.txt', fake_stream,
                                 force=False, update=False)]
    # we should call the create_file method on the return
    # value of _storage_mock
    fake_storage = await fake_project._storage_mock.return_value
    assert fake_storage.mock_calls == expected


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_recursive_requires_directory(OSF_project):
    # test that we check if source is a directory when using recursive mode
    args = MockArgs(username='joe@example.com',
                    project='1234',
                    source='foo/bar.txt',
                    recursive=True,
                    destination='bar/bar/foo.txt')

    def simple_getenv(key, default=None):
        if key == 'OSF_PASSWORD':
            return 'secret'
        return default

    with pytest.raises(RuntimeError) as e:
        with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
            with patch('osfclient.cli.os.path.isdir', return_value=False):
                await upload(args)

    assert 'recursive' in str(e.value)
    assert 'Expected source (foo/bar.txt)' in str(e.value)


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_recursive_upload(OSF_project):
    # test that we check if source is a directory when using recursive mode
    args = MockArgs(username='joe@example.com',
                    project='1234',
                    source='foobar/',
                    recursive=True,
                    destination='BAR/')

    def simple_getenv(key, default=None):
        if key == 'OSF_PASSWORD':
            return 'secret'
        return default

    fake_open = mock_async_open()
    fake_storage = await OSF_project.return_value.storage.return_value

    # it is important we use foobar/ and not foobar to match with args.source
    # to mimick the behaviour of os.walk()
    dir_contents = [('foobar/', None, ['bar.txt', 'abc.txt']),
                    ('foobar/baz', None, ['bar.txt', 'abc.txt'])
                    ]

    with patch('osfclient.cli.aiofiles.open', fake_open):
        with patch('os.walk', return_value=iter(dir_contents)):
            with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
                with patch('osfclient.cli.os.path.isdir', return_value=True):
                    await upload(args)

    assert call('foobar/bar.txt', 'rb') in fake_open.mock_calls
    assert call('foobar/abc.txt', 'rb') in fake_open.mock_calls
    assert call('foobar/baz/bar.txt', 'rb') in fake_open.mock_calls
    assert call('foobar/baz/abc.txt', 'rb') in fake_open.mock_calls
    # two directories with two files each -> four calls
    assert len(fake_open.mock_calls) == 4

    fake_storage.assert_has_calls([
        call.create_file('BAR/./bar.txt', mock.ANY, force=False, update=False),
        call.create_file('BAR/./abc.txt', mock.ANY, force=False, update=False),
        call.create_file('BAR/baz/bar.txt', mock.ANY, force=False, update=False),
        call.create_file('BAR/baz/abc.txt', mock.ANY, force=False, update=False)
        ])
    # two directories with two files each -> four calls
    assert len(fake_storage.mock_calls) == 4


@pytest.mark.asyncio
@patch.object(OSF, 'project', return_value=MockProject('1234'))
async def test_recursive_upload_with_subdir(OSF_project):
    # test that an extra level of subdirectory is created on the remote side
    # this is because args.source does not end in a /
    args = MockArgs(username='joe@example.com',
                    project='1234',
                    source='foobar',
                    recursive=True,
                    destination='BAR/')

    def simple_getenv(key, default=None):
        if key == 'OSF_PASSWORD':
            return 'secret'
        return default

    fake_open = mock_async_open()
    fake_storage = await OSF_project.return_value.storage.return_value

    # it is important we use foobar and not foobar/ to match with args.source
    # to mimick the behaviour of os.walk()
    dir_contents = [('foobar', None, ['bar.txt', 'abc.txt']),
                    ('foobar/baz', None, ['bar.txt', 'abc.txt'])
                    ]

    with patch('osfclient.cli.aiofiles.open', fake_open):
        with patch('os.walk', return_value=iter(dir_contents)):
            with patch('osfclient.cli.os.getenv', side_effect=simple_getenv):
                with patch('osfclient.cli.os.path.isdir', return_value=True):
                    await upload(args)

    assert call('foobar/bar.txt', 'rb') in fake_open.mock_calls
    assert call('foobar/abc.txt', 'rb') in fake_open.mock_calls
    assert call('foobar/baz/bar.txt', 'rb') in fake_open.mock_calls
    assert call('foobar/baz/abc.txt', 'rb') in fake_open.mock_calls
    # two directories with two files each -> four calls
    assert len(fake_open.mock_calls) == 4

    fake_storage.assert_has_calls([
        call.create_file('BAR/foobar/./bar.txt', mock.ANY,
                         update=False, force=False),
        call.create_file('BAR/foobar/./abc.txt', mock.ANY,
                         update=False, force=False),
        call.create_file('BAR/foobar/baz/bar.txt', mock.ANY,
                         update=False, force=False),
        call.create_file('BAR/foobar/baz/abc.txt', mock.ANY,
                         update=False, force=False)
        ])
    # two directories with two files each -> four calls
    assert len(fake_storage.mock_calls) == 4
