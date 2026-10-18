"""ENV-T123 partial: cancellation recognized before export creates no file.

These offline cases do not cover interrupts after the shared writer opens a file,
target-platform permission checks, or resume/recollection of stale evidence.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
import guardian as g


class CancelledExportTests(unittest.TestCase):
    def invoke(self, arguments):
        with contextlib.redirect_stdout(io.StringIO()) as outgoing:
            code = g.main(arguments)
        return code, json.loads(outgoing.getvalue())

    def assert_cancelled_without_export(self, arguments, directory, expected_code=0):
        before = sorted(path.name for path in directory.iterdir())
        with patch.object(g, 'save_new', wraps=g.save_new) as save:
            code, report = self.invoke(arguments)
        self.assertEqual(code, expected_code)
        self.assertIn('USER_CANCELLED', [item['code'] for item in report['findings']])
        self.assertEqual(report['contact_control']['gate_state'], 'closed')
        self.assertEqual(report['changes'], [])
        self.assertEqual(sorted(path.name for path in directory.iterdir()), before)
        save.assert_not_called()
        return report

    def test_cancelled_offline_inventory_is_not_exported(self):
        for command in ('analyze', 'plan'):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                request = json.loads((ROOT / 'tests/fixtures/proxy-port-conflict.json').read_text(encoding='utf-8'))
                request['cancelled'] = True
                source = directory / 'input.json'
                source.write_text(json.dumps(request), encoding='utf-8')
                report = self.assert_cancelled_without_export([
                    command, '--target-ref', 'device-1', '--input', str(source),
                    '--output', str(directory / 'report.json')], directory)
                self.assertEqual(report['execution_status'], 'interrupted')
                self.assertEqual(report['facts'], [])
                self.assertNotIn('plan', report)

    def test_cancelled_interview_is_not_exported(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / 'input.json'
            source.write_text(json.dumps({'cancelled': True}), encoding='utf-8')
            report = self.assert_cancelled_without_export([
                'interview', '--input', str(source),
                '--output', str(directory / 'report.json')], directory)
            self.assertEqual(report['execution_status'], 'interrupted')

    def test_reloaded_cancelled_report_does_not_create_another_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / 'input.json'
            source.write_text(json.dumps(g.interview({'cancelled': True})), encoding='utf-8')
            report = self.assert_cancelled_without_export([
                'interview', '--input', str(source),
                '--output', str(directory / 'report.json')], directory, expected_code=3)
            self.assertEqual(report['execution_status'], 'blocked')

    def test_input_read_interrupt_does_not_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with patch.object(g, 'load_json', side_effect=KeyboardInterrupt):
                report = self.assert_cancelled_without_export([
                    'analyze', '--target-ref', 'device-1',
                    '--input', str(directory / 'input.json'),
                    '--output', str(directory / 'report.json')], directory)
            self.assertEqual(report['execution_status'], 'interrupted')

    def test_collection_interrupt_does_not_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with patch.object(g, 'native_check', side_effect=KeyboardInterrupt):
                report = self.assert_cancelled_without_export([
                    'check', '--target-ref', 'device-1', '--target-os', 'macos',
                    '--output', str(directory / 'report.json')], directory)
            self.assertEqual(report['execution_status'], 'interrupted')

    def test_collection_cancel_error_does_not_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with patch.object(g, 'native_check', side_effect=g.GuardianError('USER_CANCELLED', 3)):
                report = self.assert_cancelled_without_export([
                    'check', '--target-ref', 'device-1', '--target-os', 'macos',
                    '--output', str(directory / 'report.json')], directory, expected_code=3)
            self.assertEqual(report['execution_status'], 'blocked')

    def test_cancel_does_not_touch_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = directory / 'existing.json'
            output.write_text('existing user file', encoding='utf-8')
            with patch.object(g, 'interview', return_value=g.interview({'cancelled': True})):
                self.assert_cancelled_without_export([
                    'interview', '--output', str(output)], directory)
            self.assertEqual(output.read_text(encoding='utf-8'), 'existing user file')

    def test_noncancelled_explicit_export_still_works(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'report.json'
            code, report = self.invoke(['interview', '--output', str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8')), report)
            self.assertNotIn('USER_CANCELLED', [item['code'] for item in report['findings']])


if __name__ == '__main__':
    unittest.main()
