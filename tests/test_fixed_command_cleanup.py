"""Owned offline child lifecycle checks; never launch a native collector."""
import importlib.util
from pathlib import Path
import subprocess
import os
import ctypes
from types import SimpleNamespace
import sys
import threading
import time
import unittest
from unittest.mock import patch, Mock

SPEC = importlib.util.spec_from_file_location('cleanup_guardian', Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/guardian.py')
g = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(g)


class FixedCommandCleanupTests(unittest.TestCase):
    def run_owned(self, script, expected=None, wait_error=None, start_error=None,
                  timeout=1, retained_writer=False, constructor_error=None,
                  cleanup_error=None, expected_cause=None):
        children, readers, writers = [], [], []
        real_popen, real_thread = subprocess.Popen, threading.Thread

        def launch(*args, **kwargs):
            # The production command is never run, even if its policy regresses.
            child = real_popen([sys.executable, '-c', script], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               bufsize=0)
            children.append(child)
            if retained_writer:
                # Emulate stdout inherited by another process, without launching
                # an unowned descendant or performing any system/network query.
                read_fd, write_fd = os.pipe()
                writers.append(write_fd)
                child.stdout.close()
                child.stdout = os.fdopen(read_fd, 'rb', buffering=0)
            if wait_error:
                original = child.wait
                first = True
                def wait(*args, **kwargs):
                    nonlocal first
                    if first:
                        first = False
                        raise wait_error
                    result = original(*args, **kwargs)
                    if cleanup_error:
                        raise cleanup_error
                    return result
                child.wait = wait
            return child

        def reader(*args, **kwargs):
            if constructor_error:
                raise constructor_error
            thread = real_thread(*args, **kwargs)
            readers.append(thread)
            return thread

        started = time.monotonic()
        try:
            with patch.object(g, 'fixed_command', return_value=((sys.executable,), {})), \
                    patch('subprocess.Popen', side_effect=launch), \
                    patch('threading.Thread', side_effect=reader), \
                    patch.object(g, 'COMMAND_TIMEOUT', timeout):
                from contextlib import ExitStack
                with ExitStack() as stack:
                    if start_error:
                        stack.enter_context(patch.object(real_thread, 'start', side_effect=start_error))
                    if expected:
                        with self.assertRaises(expected[0]) as caught:
                            g.run_fixed('mac-version')
                        self.assertEqual(str(caught.exception), expected[1])
                        if expected_cause:
                            self.assertIsInstance(caught.exception.__cause__, g.GuardianError)
                            self.assertEqual(str(caught.exception.__cause__), expected_cause)
                    else:
                        self.assertEqual(g.run_fixed('mac-version'), 'owned-ok')
            self.assertLess(time.monotonic() - started, 4)
            self.assertIsNotNone(children[0].returncode, 'owned child was not reaped')
            self.assertTrue(children[0].stdout.closed, 'stdout was not closed')
            self.assertTrue(all(not thread.is_alive() for thread in readers))
        finally:
            # A failing old implementation must not leak the test's owned child.
            for fd in writers:
                os.close(fd)
            for child in children:
                if child.poll() is None:
                    child.kill()
                real_popen.wait(child, timeout=2)
                child.stdout.close()
            for thread in readers:
                if thread.ident is not None:
                    thread.join(timeout=2)

    def test_success(self):
        self.run_owned("print('owned-ok')")

    def test_interrupt_reaps_and_closes(self):
        self.run_owned('import time; time.sleep(30)', (KeyboardInterrupt, ''),
                       wait_error=KeyboardInterrupt())

    def test_timeout_cleanup_failure_is_observable_and_sanitized(self):
        self.run_owned('import time; time.sleep(30)', (g.GuardianError, 'OS_QUERY_FAILED'),
                       wait_error=subprocess.TimeoutExpired('secret-command', 1),
                       cleanup_error=OSError('secret-cleanup-details'))

    def test_interrupt_cleanup_failure_keeps_interrupt_with_sanitized_cause(self):
        self.run_owned('import time; time.sleep(30)', (KeyboardInterrupt, ''),
                       wait_error=KeyboardInterrupt(), cleanup_error=OSError('secret-cleanup-details'),
                       expected_cause='OS_QUERY_FAILED')

    def test_interrupt_during_cleanup_wait_still_joins_and_closes(self):
        self.run_owned('import time; time.sleep(30)', (KeyboardInterrupt, ''),
                       wait_error=subprocess.TimeoutExpired('secret-command', 1),
                       cleanup_error=KeyboardInterrupt())

    def test_reader_start_failure_reaps_and_sanitizes(self):
        self.run_owned('import time; time.sleep(30)', (g.GuardianError, 'OS_QUERY_FAILED'),
                       start_error=RuntimeError('secret-start-details'))

    def test_wait_error_reaps_and_sanitizes(self):
        self.run_owned('import time; time.sleep(30)', (g.GuardianError, 'OS_QUERY_FAILED'),
                       wait_error=OSError('secret-wait-details'))

    def test_timeout_reaps_and_closes(self):
        self.run_owned('import time; time.sleep(30)', (g.GuardianError, 'BUDGET_EXCEEDED'), timeout=.05)

    def test_overflow_reaps_and_closes(self):
        self.run_owned("import os,time; os.write(1,b'x'*100000); time.sleep(30)",
                       (g.GuardianError, 'BUDGET_EXCEEDED'))

    def test_nonzero_sanitized(self):
        self.run_owned("import sys; print('secret-output'); sys.exit(4)",
                       (g.GuardianError, 'OS_QUERY_FAILED'))

    def test_system_exit_reaps_and_closes(self):
        self.run_owned('import time; time.sleep(30)', (SystemExit, '2'),
                       wait_error=SystemExit(2))

    def test_reader_constructor_failure_reaps(self):
        self.run_owned('import time; time.sleep(30)', (g.GuardianError, 'OS_QUERY_FAILED'),
                       constructor_error=RuntimeError('secret-constructor'))

    def test_reader_start_interruption_reaps(self):
        self.run_owned('import time; time.sleep(30)', (KeyboardInterrupt, ''),
                       start_error=KeyboardInterrupt())

    def test_reader_failure_reaps_and_sanitizes(self):
        # Patch readiness, not os.read globally: Popen itself also uses os.read.
        with patch.object(g, '_fixed_pipe_ready', side_effect=OSError('secret-read-details')):
            self.run_owned('import time; time.sleep(30)', (g.GuardianError, 'OS_QUERY_FAILED'))

    def test_retained_writer_cannot_hold_reader_open(self):
        self.run_owned('pass', (g.GuardianError, 'BUDGET_EXCEEDED'), retained_writer=True)

    def test_invalid_encoding_closes(self):
        self.run_owned("import os; os.write(1,b'\\xff')",
                       (g.GuardianError, 'INPUT_OR_RESPONSE_INVALID'))


class PipeReadinessTests(unittest.TestCase):
    def test_windows_peek_data_empty_eof_and_failure(self):
        # Exercise Windows branch without pretending Linux is native acceptance.
        peek = Mock()
        kernel = SimpleNamespace(PeekNamedPipe=peek)
        stream = Mock()
        stream.fileno.return_value = 17
        with patch.object(g.sys, 'platform', 'win32'), \
                patch.dict(sys.modules, {'msvcrt': SimpleNamespace(get_osfhandle=lambda fd: 99)}), \
                patch.object(ctypes, 'WinDLL', return_value=kernel, create=True), \
                patch.object(ctypes, 'get_last_error', return_value=109, create=True) as last_error:
            def data(*args):
                args[4]._obj.value = 2
                return True
            peek.side_effect = data
            self.assertTrue(g._fixed_pipe_ready(stream))
            peek.side_effect = None
            peek.return_value = True
            self.assertFalse(g._fixed_pipe_ready(stream))
            peek.return_value = False
            self.assertTrue(g._fixed_pipe_ready(stream))
            last_error.return_value = 5
            with self.assertRaises(OSError):
                g._fixed_pipe_ready(stream)


if __name__ == '__main__':
    unittest.main()
