"""Synthetic API time validation; no listeners, native probes, or subprocesses."""
from contextlib import ExitStack
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import serve_webrtc as webrtc


INVALID_TIMES = (True, False, None, '1', float('nan'), float('inf'),
                 -float('inf'), 10 ** 1000, -(10 ** 1000))


class SyntheticOnlyTests(unittest.TestCase):
    def setUp(self):
        self.no_io = ExitStack()
        self.addCleanup(self.no_io.close)
        self.no_io.enter_context(patch('socket.socket', side_effect=AssertionError('No network I/O')))
        self.no_io.enter_context(patch('subprocess.Popen', side_effect=AssertionError('No native probes')))


class WebRtcDurationTests(SyntheticOnlyTests):
    def test_invalid_duration_rejected_before_server_state_or_io(self):
        # An uninitialized target proves validation needs no instance state or I/O.
        for value in INVALID_TIMES + (0, -1, 901):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,
                        '^Duration must be greater than zero and at most 900 seconds$'):
                    webrtc.LocalProbeServer.serve(object(), duration_seconds=value)


if __name__ == '__main__':
    unittest.main()
