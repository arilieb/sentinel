# -*- coding: utf-8 -*-
"""
Unit tests for sentinel.app.cli.commands.start module
"""

import argparse
import unittest

from sentinel.app.cli.commands.start import _read_passcode_file, launch, parser


class TestReadPasscodeFile(unittest.TestCase):
    """Test cases for _read_passcode_file"""

    def test_strips_trailing_newline(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".bran", delete=False) as f:
            f.write("abcdefghijklmnopqrstu\n")
            path = f.name

        try:
            self.assertEqual(_read_passcode_file(path), "abcdefghijklmnopqrstu")
        finally:
            import os

            os.unlink(path)


class TestPasscodeFilePrecedence(unittest.TestCase):
    """Test cases for --passcode-file resolution in launch()"""

    def _make_args(self, **overrides):
        defaults = dict(
            name="test",
            alias="testalias",
            bran=None,
            passcode_file=None,
            base="",
            socket_dir="/tmp",
            local=True,
            uxd=False,
            loglevel="INFO",
            logfile=None,
            export_dir="/usr/local/sentinel",
            registrar_url=None,
            config=None,
        )
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def test_explicit_passcode_wins_over_file(self):
        import tempfile
        import os
        from unittest.mock import patch

        with tempfile.NamedTemporaryFile("w", suffix=".bran", delete=False) as f:
            f.write("file-bran-value\n")
            path = f.name

        try:
            args = self._make_args(bran="explicit-bran", passcode_file=path)
            with patch(
                "sentinel.app.cli.commands.start.run_sentinel"
            ) as mock_run_sentinel:
                launch(args)
            self.assertEqual(args.bran, "explicit-bran")
            mock_run_sentinel.assert_called_once()
        finally:
            os.unlink(path)

    def test_passcode_file_used_when_no_explicit_passcode(self):
        import tempfile
        import os
        from unittest.mock import patch

        with tempfile.NamedTemporaryFile("w", suffix=".bran", delete=False) as f:
            f.write("file-bran-value\n")
            path = f.name

        try:
            args = self._make_args(bran=None, passcode_file=path)
            with patch(
                "sentinel.app.cli.commands.start.run_sentinel"
            ) as mock_run_sentinel:
                launch(args)
            self.assertEqual(args.bran, "file-bran-value")
            mock_run_sentinel.assert_called_once()
        finally:
            os.unlink(path)


class TestParserFlags(unittest.TestCase):
    """Test cases confirming the new CLI flags exist with expected defaults"""

    def test_new_flags_present_with_defaults(self):
        args = parser.parse_args(["--name", "n", "--alias", "a", "--local"])
        self.assertIsNone(args.passcode_file)
        self.assertEqual(args.socket_dir, "/tmp")


if __name__ == "__main__":
    unittest.main()
