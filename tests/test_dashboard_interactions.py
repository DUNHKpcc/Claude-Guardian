"""Offline helper-boundary tests; Chrome interaction runs separately in CI only."""
from copy import deepcopy
import importlib.util
import json
import io
import re
from contextlib import redirect_stderr
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('dashboard_interactions', ROOT / 'tools/check_dashboard_interactions.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def result():
    return dict(schema_version='guardian-dashboard-interaction/0.1', record_kind='synthetic_example',
                browser_version='Chrome/synthetic-test', evidence_kind='ci_real_chrome_keyboard_and_layout',
                network_isolation_verified=False,
                viewports=[dict(width=w, height=h, summary_count=12, page_document_requests=1,
                                page_subresource_requests=0, **{flag: True for flag in m.FLAGS})
                           for w,h in m.preview.VIEWPORTS.values()])


class DashboardInteractionTests(unittest.TestCase):
    def test_valid_report_and_exact_fields(self):
        self.assertEqual(m.validate_result(result()), result())
        for key in result():
            data=result(); data.pop(key)
            with self.assertRaises(m.preview.PreviewError): m.validate_result(data)
        for extra in ('raw_path', 'stderr', 'secret'):
            data=result(); data[extra]='private'
            with self.assertRaises(m.preview.PreviewError): m.validate_result(data)

    def test_nonpassing_or_coerced_results_are_rejected(self):
        for flag in m.FLAGS:
            for value in (False, 1, 'true', None):
                data=result(); data['viewports'][0][flag]=value
                with self.assertRaises(m.preview.PreviewError): m.validate_result(data)
        for field,value in [('width',391),('height',True),('summary_count',11),
                            ('page_document_requests',0),('page_subresource_requests',True)]:
            data=result(); data['viewports'][0][field]=value
            with self.assertRaises(m.preview.PreviewError): m.validate_result(data)
        data=result(); data['network_isolation_verified']=True
        with self.assertRaises(m.preview.PreviewError): m.validate_result(data)

    def test_ci_gate_precedes_browser_or_files(self):
        with patch.object(m.preview,'require_ci',side_effect=m.preview.PreviewError('blocked')), \
                patch.object(m.preview,'find_browser') as browser, patch.object(Path,'mkdir') as mkdir:
            with self.assertRaises(m.preview.PreviewError): m.check('unused')
            browser.assert_not_called(); mkdir.assert_not_called()

    def run_mock(self, output, failure=None, payload=None, diagnostic=None):
        def run(command, **options):
            self.assertEqual(options['timeout'],90)
            self.assertEqual(Path(command[1]).name,'check_dashboard_interactions.cjs')
            self.assertEqual(command[2],'owned-chrome')
            page=Path(command[3]); profile=Path(command[4]); raw=Path(command[5])
            self.assertTrue(profile.is_dir())
            m.preview.validate_html(page.read_text(encoding='utf-8'))
            if failure:
                if diagnostic is not None:
                    Path(command[6]).write_text(diagnostic, encoding='utf-8')
                raise failure
            raw.write_text(json.dumps(result()) if payload is None else payload, encoding='utf-8')
        with patch.object(m.preview,'require_ci'), patch.object(m.preview,'find_browser',return_value='owned-chrome'), \
                patch.object(m.shutil,'which',return_value='owned-node'), \
                patch.object(m.preview,'cjk_fonts',return_value=['Synthetic']), \
                patch.object(m.preview,'run_browser',side_effect=run):
            return m.check(output)

    def test_artifact_is_only_validated_synthetic_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'artifact'
            self.run_mock(output)
            self.assertEqual([p.name for p in output.iterdir()],['interaction.json'])
            saved=json.loads((output/'interaction.json').read_text())
            self.assertFalse(saved['network_isolation_verified'])
            self.assertIn('no actual diagnostic',saved['scope'])
            self.assertNotIn(tmp,json.dumps(saved))
            self.assertEqual(len(saved['html_sha256']),64)

    def test_browser_failure_and_bad_result_never_publish_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i,failure in enumerate((subprocess.TimeoutExpired('owned-node',90), subprocess.CalledProcessError(2,'owned-node'))):
                output=Path(tmp)/str(i)
                with self.assertRaises((subprocess.SubprocessError, m.InteractionFailure)): self.run_mock(output,failure=failure)
                self.assertEqual(list(output.iterdir()),[])
            for i,payload in enumerate(('{bad json',json.dumps({'private':'sentinel'}),'x'*16385)):
                output=Path(tmp)/('bad'+str(i))
                with self.assertRaises(m.preview.PreviewError): self.run_mock(output,payload=payload)
                self.assertEqual(list(output.iterdir()),[])

    def test_existing_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'artifact'; output.mkdir()
            sentinel=output/'keep'; sentinel.write_text('keep')
            with self.assertRaises(FileExistsError): self.run_mock(output)
            self.assertEqual(sentinel.read_text(),'keep')

    def test_allowlisted_diagnostic_survives_nonzero_without_acceptance_artifact(self):
        record=dict(schema_version='guardian-interaction-failure/0.1',
                    code='INTERACTION_COMMAND_FAILED',stage='DOM.querySelectorAll')
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'artifact'
            with self.assertRaises(m.InteractionFailure) as caught:
                self.run_mock(output, failure=subprocess.CalledProcessError(2, 'owned'), diagnostic=json.dumps(record))
            self.assertEqual(caught.exception.code,record['code'])
            self.assertEqual(caught.exception.stage,record['stage'])
            self.assertEqual(list(output.iterdir()),[])
            stream=io.StringIO()
            with patch.object(m,'check',side_effect=caught.exception), redirect_stderr(stream):
                self.assertEqual(m.main(['--output','unused']),2)
            self.assertEqual(stream.getvalue(), 'INTERACTION_FAILED: code=INTERACTION_COMMAND_FAILED stage=DOM.querySelectorAll; no acceptance result published\n')

    def test_private_malformed_or_forged_diagnostic_is_suppressed(self):
        good=dict(schema_version='guardian-interaction-failure/0.1',
                  code='INTERACTION_COMMAND_FAILED',stage='DOM.querySelectorAll')
        values=['bad JSON', 'x'*1025, json.dumps({**good,'private':'secret-sentinel'}),
                json.dumps({**good,'code':'secret-sentinel'}),json.dumps({**good,'stage':'/private/path'}),
                json.dumps({**good,'code':[]}),json.dumps({**good,'stage':{}}),
                '{"code":"secret-sentinel","code":"INTERACTION_FAILED","stage":"unknown","schema_version":"guardian-interaction-failure/0.1"}']
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'failure.json'
            self.assertEqual(str(m.read_failure(path)), 'code=INTERACTION_FAILED stage=unknown')
            for value in values:
                path.write_text(value)
                self.assertEqual(str(m.read_failure(path)), 'code=INTERACTION_FAILED stage=unknown')

    def test_diagnostic_allowlists_match_node_and_cannot_be_coerced(self):
        code=(ROOT/'tools/check_dashboard_interactions.cjs').read_text()
        for name,allowed in [('FAILURE_CODES',m.FAILURE_CODES),('FAILURE_STAGES',m.FAILURE_STAGES)]:
            values=json.loads(re.search(r'const '+name+r' = new Set\((\[.*?\])\);',code).group(1))
            self.assertEqual(set(values),allowed)
        self.assertEqual(str(m.InteractionFailure([],{})), 'code=INTERACTION_FAILED stage=unknown')

    def test_protocol_uses_no_page_scripts_or_security_bypass(self):
        code=(ROOT/'tools/check_dashboard_interactions.cjs').read_text()
        for forbidden in ('--no-sandbox','--disable-web-security','--remote-debugging-port',
                          'Runtime.evaluate','Page.setBypassCSP','DOM.setAttributeValue','DOM.focus'):
            self.assertNotIn(forbidden,code)
        self.assertIn("'--remote-debugging-pipe'",code)
        self.assertIn("stdio: ['ignore', 'ignore', 'ignore', 'pipe', 'pipe']",code)
        self.assertIn("process.getuid() !== 0",code)

    @unittest.skipUnless(shutil.which('node'), 'Node missing; synthetic protocol harness not run')
    def test_synthetic_protocol_harness(self):
        run=subprocess.run([shutil.which('node'),str(ROOT/'tests/dashboard-interaction-protocol.cjs')],
                           capture_output=True,encoding='utf-8',timeout=60)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertIn('no browser executed',run.stdout)


if __name__ == '__main__': unittest.main()
