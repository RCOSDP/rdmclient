import sys
from mock import patch

import pytest

from osfclient.__main__ import main


@pytest.mark.asyncio
async def test_no_args(capsys):
    test_args = ['osf']
    with patch.object(sys, 'argv', test_args):
        await main()

    out, err = capsys.readouterr()
    assert "osf is a command-line program to up and download" in out
    assert "usage: osf [-h]" in out
    assert not err


@pytest.mark.asyncio
@pytest.mark.parametrize("command",
                         ['clone', 'fetch', 'list', 'upload', 'remove'])
async def test_command_prints_help(command, capsys):
    test_args = ['osf', command]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit):
            await main()

    out, err = capsys.readouterr()
    expected = 'usage: osf %s' % command
    assert expected in err
