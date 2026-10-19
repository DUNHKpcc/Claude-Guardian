"""Exercise the actual CI snippet with a synthetic collector, never native I/O."""
import contextlib
import io
from pathlib import Path
import sys
import subprocess
import json
import textwrap
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
import guardian
import environment_entry


class CIEntryContractTests(unittest.TestCase):
    def test_ci_metadata_smoke_supplies_valid_entry_on_both_platforms(self):
        workflow = (ROOT / '.github/workflows/tests.yml').read_text(encoding='utf-8')
        section = workflow.split('      - name: Native CI metadata smoke', 1)[1]
        block = section.split("          python - <<'PY'\n", 1)[1].split('\n          PY', 1)[0]
        code = compile(textwrap.dedent(block), '<ci-owned-metadata-snippet>', 'exec')
        for platform, expected in [('darwin', 'macos'), ('win32', 'windows')]:
            calls = []
            def collect(args, *, entry_request):
                self.assertEqual(args.target_ref, 'ci-runner')
                self.assertEqual(args.target_os, expected)
                self.assertTrue(args.confirm_target and args.authorize_audit)
                decision = environment_entry.require_entry(entry_request, 'offline_precheck', 'ci-runner')
                self.assertEqual(decision['target_role'], 'local')
                calls.append(args.target_os)
                return {'contact_control': {'gate_state': 'closed'}, 'changes': [], 'facts': []}
            fake = types.SimpleNamespace(parser=guardian.parser, native_check=collect)
            def child_run(command, **kwargs):
                self.assertEqual(command[:2], [sys.executable, '-c'])
                self.assertEqual(kwargs, {'capture_output': True, 'text': True, 'timeout': 60})
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exec(compile(command[2], '<ci-owned-child>', 'exec'), {'__name__': '__ci_child_fixture__'})
                return types.SimpleNamespace(returncode=0, stdout=output.getvalue())
            with self.subTest(platform=platform), patch.object(sys, 'platform', platform), patch.dict(sys.modules, guardian=fake), patch.object(subprocess, 'run', child_run), patch.object(sys, 'path', list(sys.path)), contextlib.redirect_stdout(io.StringIO()):
                exec(code, {'__name__': '__ci_fixture__'})
            self.assertEqual(calls, [expected])


if __name__ == '__main__':
    unittest.main()
