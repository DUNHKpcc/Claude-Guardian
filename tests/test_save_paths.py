"""Output lexical boundaries: pure Windows cases and owned POSIX temporary files."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import guardian as g


class SavePathTests(unittest.TestCase):
    def test_reserved_devices_and_ads_rejected_in_every_segment(self):
        bad = [r'C:\approved\NUL', r'C:\approved\nul.txt',
               r'C:\approved\session.html:extra', r'C:\approved:stream\session.html',
               r'C:\NUL\session.html', r'C:\COM1.txt\session.html',
               r'C:\approved\COM¹.txt', r'C:\approved\LPT²',
               r'C:\approved\CONOUT$', r'C:\approved\AUX .txt',
               'C:\\approved\\file. ', 'C:\\approved.\\file.html',
               r'\\server\share\file.html', r'\\?\C:\approved\file.html',
               r'\\.\C:\approved\file.html', r'C:approved\file.html',
               r'C:\approved\..\file.html', r'C:/approved/file.html',
               'C:\\approved\\bad\x01name.html']
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaisesRegex(g.GuardianError, 'UNSAFE_OR_OFFLINE_PATH'):
                    g.validate_windows_output_path(value)
        self.assertEqual(g.validate_windows_output_path(r'C:\approved\session.html'),
                         r'C:\approved\session.html')

    def test_windows_save_validates_before_path_or_open(self):
        with patch.object(g.sys, 'platform', 'win32'), \
                patch.object(g, 'Path', side_effect=AssertionError('No path access')), \
                patch.object(g.os, 'open', side_effect=AssertionError('No open')):
            for path in (r'C:\approved\NUL', r'C:\approved\session.html:extra', r'\\server\share\file'):
                with self.assertRaisesRegex(g.GuardianError, 'UNSAFE_OR_OFFLINE_PATH'):
                    g.save_new(path, 'synthetic')

    @unittest.skipUnless(os.name == 'posix', 'Owned POSIX save behavior')
    def test_posix_save_remains_exclusive_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.html'
            g.save_new(path, 'synthetic')
            self.assertEqual(path.read_text(), 'synthetic')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaisesRegex(g.GuardianError, 'OUTPUT_SAVE_FAILED'):
                g.save_new(path, 'replacement')
            self.assertEqual(path.read_text(), 'synthetic')

    @unittest.skipUnless(os.name == 'posix', 'Owned POSIX symlink behavior')
    def test_posix_symlink_ancestor_stays_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'real').mkdir()
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaisesRegex(g.GuardianError, 'UNSAFE_OR_OFFLINE_PATH'):
                g.save_new(root / 'link' / 'report.html', 'synthetic')
            self.assertFalse((root / 'real' / 'report.html').exists())


if __name__ == '__main__':
    unittest.main()
