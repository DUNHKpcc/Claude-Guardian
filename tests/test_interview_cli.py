import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/'skills/claude-guardian/scripts/interview_cli.py'

class InterviewCLITests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,str(CLI),*args],capture_output=True,encoding='utf-8',timeout=10)

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
