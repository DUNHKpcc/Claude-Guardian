import json
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/'skills/claude-guardian/scripts/interview_cli.py'
sys.path.insert(0, str(CLI.parent))
import interview_cli as cli

class InterviewCLITests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,str(CLI),*args],capture_output=True,encoding='utf-8',timeout=10)

    def test_argument_errors_never_echo_private_arguments_or_save_state(self):
        marker = 'synthetic-private-argument-sentinel'
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'must-not-save.json'
            for args in (['--unknown', marker], ['--unknown=' + marker],
                         ['--' + marker], [marker], ['--help=' + marker],
                         ['--account-ref']):
                with self.subTest(args=args):
                    result = self.run_cli('--output', str(output), *args)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(json.loads(result.stdout), {
                        'status': 'blocked', 'code': 'INVALID_OR_UNAUTHORIZED_INTERVIEW_IO',
                        'action_executed': False})
                    self.assertEqual(result.stderr, '')
                    self.assertNotIn(marker, result.stdout + result.stderr)
                    self.assertFalse(output.exists())

    def test_help_remains_available_without_creating_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'must-not-save.json'
            result = self.run_cli('--output', str(output), '--help')
            self.assertEqual(result.returncode, 0)
            self.assertIn('--answer-file', result.stdout)
            self.assertEqual(result.stderr, '')
            self.assertFalse(output.exists())

    def test_known_token_aliases_are_rejected_before_private_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            for prefix in ('ghp_', 'github_pat_'):
                marker = prefix + 'syntheticPrivateCredential12'
                for flag in ('--target-ref', '--account-ref'):
                    with self.subTest(prefix=prefix, flag=flag):
                        output = Path(tmp).resolve() / (prefix + flag + '.json')
                        result = self.run_cli(flag, marker, '--output', str(output))
                        self.assertEqual(result.returncode, 2)
                        self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
                        self.assertEqual(result.stderr, '')
                        self.assertNotIn(marker, result.stdout)
                        self.assertFalse(output.exists())

    def test_ordinary_private_aliases_are_retained_only_in_requested_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'state.json'
            target, account = 'synthetic-private-device', 'synthetic-private-account'
            result = self.run_cli('--target-ref', target, '--account-ref', account,
                                  '--output', str(output))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for marker in (target, account):
                self.assertNotIn(marker, result.stdout + result.stderr)
            saved = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual((saved['target_alias'], saved['account_alias']), (target, account))

    def test_stdout_failures_return_nonzero_without_raw_error_text(self):
        for method in ('write', 'flush'):
            with self.subTest(method=method):
                output, errors = io.StringIO(), io.StringIO()
                with patch.object(output, method, side_effect=OSError('synthetic-private-output-sentinel')), \
                        patch.object(cli.sys, 'stdout', output), patch.object(cli.sys, 'stderr', errors):
                    self.assertEqual(cli.main([]), 2)
                self.assertEqual(json.loads(errors.getvalue()), {
                    'status': 'blocked', 'code': 'INTERVIEW_OUTPUT_FAILED',
                    'action_executed': False, 'saved': False})
                self.assertNotIn('synthetic-private-output-sentinel', output.getvalue() + errors.getvalue())

    def test_closed_pipe_has_sanitized_error_and_stable_exit(self):
        process = subprocess.Popen([sys.executable, str(CLI)], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        process.stdout.close()
        try:
            _, raw_errors = process.communicate(timeout=10)
            errors = raw_errors.decode('utf-8')
            self.assertEqual(process.returncode, 2)
        finally:
            process.stderr.close()
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
        self.assertEqual(json.loads(errors), {
            'status': 'blocked', 'code': 'INTERVIEW_OUTPUT_FAILED',
            'action_executed': False, 'saved': False})

    def test_help_output_failure_does_not_report_success(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(output, 'write', side_effect=OSError('synthetic-private-help-sentinel')), \
                patch.object(cli.sys, 'stdout', output), patch.object(cli.sys, 'stderr', errors):
            self.assertEqual(cli.main(['--help']), 2)
        self.assertEqual(json.loads(errors.getvalue())['code'], 'INTERVIEW_OUTPUT_FAILED')
        self.assertNotIn('synthetic-private-help-sentinel', errors.getvalue())

    def test_output_failure_after_authorized_save_reports_retained_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp).resolve() / 'state.json'
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(output, 'write', side_effect=OSError('synthetic-private-output-sentinel')), \
                    patch.object(cli.sys, 'stdout', output), patch.object(cli.sys, 'stderr', errors):
                self.assertEqual(cli.main(['--output', str(state)]), 2)
            self.assertTrue(json.loads(errors.getvalue())['saved'])
            self.assertEqual(cli.flow.loads_state(state.read_text(encoding='utf-8'))['target_alias'],
                             'target-unconfirmed')

    def test_stdout_configuration_error_is_sanitized_before_save(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(output, 'reconfigure', create=True,
                          side_effect=OSError('synthetic-private-stream-sentinel')), \
                patch.object(cli.sys, 'stdout', output), patch.object(cli.sys, 'stderr', errors), \
                patch.object(cli.guardian, 'save_new') as save:
            self.assertEqual(cli.main(['--output', 'not-written.json']), 2)
        self.assertEqual(json.loads(output.getvalue())['status'], 'blocked')
        self.assertNotIn('synthetic-private-stream-sentinel', output.getvalue() + errors.getvalue())
        save.assert_not_called()

    def test_failure_reporting_handles_unavailable_output_streams(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(output, 'write', side_effect=OSError('synthetic-private-output-sentinel')), \
                patch.object(errors, 'write', side_effect=OSError('synthetic-private-error-sentinel')), \
                patch.object(cli.sys, 'stdout', output), patch.object(cli.sys, 'stderr', errors):
            self.assertEqual(cli.main(['--unknown']), 2)

    def test_cancellation_during_argument_parsing_returns_sanitized_result(self):
        output = io.StringIO()
        with patch.object(cli.argparse.ArgumentParser, 'parse_args', side_effect=KeyboardInterrupt), \
                patch.object(cli.sys, 'stdout', output), patch.object(cli.guardian, 'save_new') as save:
            self.assertEqual(cli.main([]), 3)
        self.assertEqual(json.loads(output.getvalue()), {'status': 'cancelled', 'action_executed': False})
        save.assert_not_called()

    def test_cancellation_before_save_never_persists_partial_answers(self):
        for module, method in ((cli.guardian, 'load_json'), (cli.flow, 'record_facts'),
                               (cli.flow, 'next_question')):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as tmp:
                answer = Path(tmp).resolve() / 'answer.json'
                answer.write_text(json.dumps({'question_id': 'Q-C04', 'value': 'suspended'}), encoding='utf-8')
                output = io.StringIO()
                with patch.object(module, method, side_effect=KeyboardInterrupt), \
                        patch.object(cli.sys, 'stdout', output), patch.object(cli.guardian, 'save_new') as save:
                    self.assertEqual(cli.main(['--answer-file', str(answer), '--output', str(answer.parent / 'new.json')]), 3)
                self.assertEqual(json.loads(output.getvalue()), {'status': 'cancelled', 'action_executed': False})
                save.assert_not_called()

    def test_multi_answer_turn_saves_all_facts_and_resumes_without_reasking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); answer=root/'answers.json'; state=root/'state.json'
            answers=[{'question_id':qid,'value':value} for qid,value in (
                ('Q-J01','first_subscription'),('Q-C02','macos'),
                ('Q-C05','accepted_default'),('Q-C08','Pro'))]
            answer.write_text(json.dumps({'answers':answers}),encoding='utf-8')
            result=self.run_cli('--answer-file',str(answer),'--target-ref','device-a',
                                '--account-ref','account-a','--output',str(state))
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            output=json.loads(result.stdout)
            self.assertEqual(output['question']['id'],'Q-C01')
            self.assertTrue(output['saved'])
            self.assertFalse(output['action_executed'])
            saved=json.loads(state.read_text(encoding='utf-8'))
            self.assertEqual(saved['context']['route_selection_basis'],'accepted_default')
            self.assertEqual(set(saved['facts']),{x['question_id'] for x in answers})
            self.assertEqual(len({v['observed_at'] for v in saved['facts'].values()}),1)
            resumed=self.run_cli('--input',str(state))
            self.assertEqual(resumed.returncode,0,resumed.stdout)
            output=json.loads(resumed.stdout)
            self.assertEqual(output['question']['id'],'Q-C01')
            self.assertEqual(output['assessment']['G3']['status'],'blocked')
            self.assertFalse(output['saved'])

    def test_multi_answer_without_output_never_saves_or_echoes_private_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); answer=root/'answers.json'
            marker='private-provenance-sentinel'
            answer.write_text(json.dumps({'answers':[
                {'question_id':'Q-J01','value':'first_subscription','source':marker},
                {'question_id':'Q-C02','value':'macos'}]}),encoding='utf-8')
            before=set(root.iterdir())
            result=self.run_cli('--answer-file',str(answer))
            self.assertEqual(result.returncode,0,result.stdout)
            self.assertNotIn(marker,result.stdout+result.stderr)
            self.assertFalse(json.loads(result.stdout)['saved'])
            self.assertEqual(set(root.iterdir()),before)

    def test_invalid_multi_answer_never_writes_partial_state_or_echoes_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); answer=root/'answers.json'; state=root/'must-not-save.json'
            first={'question_id':'Q-J01','value':'first_subscription'}
            for document in (
                {'answers':[first,{'question_id':'Q-C07','value':'owner'}]},
                {'answers':[first,{'question_id':'Q-H03','value':{'password':'private-secret-sentinel'}}]},
                {'answers':[first,{'question_id':'Q-J02','value':'existing_subscriber'}]},
                {'answers':[first,{'question_id':'Q-C11','value':'upgrade'}]},
                {'answers':[{'question_id':'Q-C11','value':'upgrade'},first]},
                {'answers':[first],'authorized':True},
                {'answers':[]}, {'answers':[{'question_id':[]}]}, {'answers':'not a list'}):
                answer.write_text(json.dumps(document),encoding='utf-8')
                result=self.run_cli('--answer-file',str(answer),'--output',str(state))
                self.assertEqual(result.returncode,2,result.stdout+result.stderr)
                self.assertFalse(state.exists())
                self.assertNotIn('private-secret-sentinel',result.stdout+result.stderr)
                self.assertNotIn('Traceback',result.stdout+result.stderr)
                self.assertFalse(json.loads(result.stdout)['action_executed'])

    def test_single_accepted_default_answer_retains_legacy_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); answer=root/'answer.json'
            answer.write_text(json.dumps({'question_id':'Q-C05','value':'accepted_default'}),encoding='utf-8')
            result=self.run_cli('--answer-file',str(answer))
            self.assertEqual(result.returncode,0,result.stdout)
            output=json.loads(result.stdout)
            self.assertEqual(output['question']['id'],'Q-J01')
            self.assertEqual(output['assessment']['route_confirmation'],'confirmed')
            self.assertEqual(output['assessment']['G3']['status'],'blocked')
            self.assertFalse(output['saved'])

    def test_chinese_first_question_without_file_output(self):
        result=self.run_cli()
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertEqual(data['question']['id'],'Q-J01')
        self.assertIn('订阅',data['question']['prompt'])
        self.assertFalse(data['saved'])
        self.assertFalse(data['action_executed'])

    def test_saved_state_consumes_answer_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); state=root/'state.json'; answer=root/'answer.json'; next_state=root/'next.json'
            answer.write_text(json.dumps({'question_id':'Q-J01','value':'first_subscription','source':'user:turn-1'}),encoding='utf-8')
            result=self.run_cli('--target-ref','device-1','--account-ref','account-1','--answer-file',str(answer),'--output',str(state))
            self.assertEqual(result.returncode,0,result.stdout)
            first=json.loads(result.stdout)
            self.assertEqual(first['question']['id'],'Q-C02')
            resumed=self.run_cli('--input',str(state),'--output',str(next_state))
            self.assertEqual(resumed.returncode,0,resumed.stdout)
            self.assertEqual(json.loads(resumed.stdout)['question']['id'],first['question']['id'])
            self.assertNotEqual(self.run_cli('--input',str(state),'--output',str(next_state)).returncode,0)

    def test_retired_question_and_secret_fail_without_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp).resolve()/'answer.json'
            for item in [{'question_id':'Q-C07','value':'owner'}, {'question_id':'Q-H03','value':{'password':'sentinel-secret'}}]:
                path.write_text(json.dumps(item),encoding='utf-8')
                result=self.run_cli('--answer-file',str(path))
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn('sentinel-secret',result.stdout+result.stderr)

    def test_resume_requires_explicit_aliases_to_match_before_answer_or_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); state=root/'state.json'; answer=root/'answer.json'
            self.assertEqual(self.run_cli('--target-ref','device-a','--account-ref','account-a',
                                          '--output',str(state)).returncode,0)
            answer.write_text(json.dumps({'question_id':'Q-J01','value':'existing_subscriber'}),encoding='utf-8')
            for flag,value in [('--target-ref','device-b'),('--account-ref','account-b'),('--target-ref','')]:
                output=root/'must-not-save.json'
                result=self.run_cli('--input',str(state),flag,value,'--answer-file',str(answer),'--output',str(output))
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(output.exists())
                self.assertFalse(json.loads(result.stdout)['action_executed'])
            matched=self.run_cli('--input',str(state),'--target-ref','device-a','--account-ref','account-a')
            self.assertEqual(matched.returncode,0,matched.stdout)

    def test_private_provenance_retained_only_in_explicit_saved_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); answer=root/'answer.json'; state=root/'state.json'
            source='private-person@example.test: confidential-source-sentinel'
            answer.write_text(json.dumps({'question_id':'Q-J01','value':'existing_subscriber','source':source}),encoding='utf-8')
            result=self.run_cli('--answer-file',str(answer),'--output',str(state))
            self.assertEqual(result.returncode,0,result.stdout)
            self.assertNotIn(source,result.stdout+result.stderr)
            self.assertEqual(json.loads(state.read_text())['current_subscription']['source'],source)
            self.assertEqual(json.loads(result.stdout)['assessment']['current_subscription']['source'],'private-source-retained')

    def test_invalid_context_cannot_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp).resolve()/'context.json';path.write_text('{"execute_shell":"anything"}',encoding='utf-8')
            result=self.run_cli('--context-file',str(path))
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(json.loads(result.stdout)['action_executed'])
