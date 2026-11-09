"""Exercise the real controller at the OS boundary; never touch host firewall state."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import HTTPServer

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'

def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

k = load('killswitch')
u = load('killswitch_ui')


def config():
    return {'version':1, 'target':platform.node(), 'backend':k.BACKENDS.get(platform.system()),
            'protected_processes':['Claude'], 'mac':{'NODE_IPS':'203.0.113.5','NODE_PORTS':'443'},
            'windows':{'enable_rules':['guardian-core'],'disable_rules':[], 'state_path':str(Path(tempfile.gettempdir()).resolve() / 'baseline.json')}}


def result(stdout='', code=0):
    return subprocess.CompletedProcess([],code,stdout,'')


class Controller(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'config.json'
        self.cfg = config()
        self.path.write_text(json.dumps(self.cfg),encoding='utf-8')

    def test_config_binds_host_and_platform_and_rejects_unknown_fields(self):
        self.assertEqual(k.load_config(self.path)['target'],platform.node())
        for key, value in [('target','different-machine'),('backend','unsupported'),('protected_processes',[]),('extra',True)]:
            cfg = dict(self.cfg, **{key:value})
            self.path.write_text(json.dumps(cfg),encoding='utf-8')
            with self.subTest(key=key), self.assertRaises(k.SwitchError):k.load_config(self.path)

    def test_noninteractive_cannot_confirm(self):
        with patch.object(sys,'stdin',io.StringIO('ON '+platform.node())), self.assertRaises(k.SwitchError):
            k.confirm('on',self.cfg)

    def test_rejects_process_left_running_without_killing_it(self):
        text='Claude\n' if platform.system()=='Windows' else '/Applications/Claude.app/Contents/MacOS/Claude\n'
        with patch.object(k,'run',return_value=result(text)) as runner, self.assertRaises(k.SwitchError):
            k.require_apps_closed(self.cfg)
        self.assertEqual(runner.call_count,1)

    def test_mac_off_cancels_persistence_before_runtime_rules(self):
        cfg=dict(self.cfg,backend='mac_pf')
        with patch.object(k,'pf') as native:
            k.off(cfg,self.path)
        self.assertEqual([c.args[1] for c in native.call_args_list],['unpersist','rollback'])

    def test_linux_off_stops_refresh_before_deleting_remaining_table(self):
        calls=[]
        def native(argv,**kwargs):
            calls.append(argv)
            return result(json.dumps({'nftables':[{'table':{'name':'flclash_killswitch','family':'inet'}}]}))
        with patch.object(k,'run',side_effect=native):k.linux_off()
        self.assertEqual(calls[0],['systemctl','stop',k.FUSE+'.timer',k.FUSE+'.service'])
        self.assertEqual(calls[1],['systemctl','disable','--now',*k.UNITS])
        self.assertEqual(calls[2],['systemctl','stop','flclash-killswitch-refresh.service'])
        self.assertEqual(calls[-1],['nft','delete','table','inet','flclash_killswitch'])

    def test_pf_status_requires_enabled_main_hook_and_block_rule(self):
        cfg=dict(self.cfg,backend='mac_pf')
        for main, want in [('anchor "com.apple/*"','on'),('', 'unknown')]:
            with self.subTest(main=main), patch.object(k,'pf',return_value=result('checked')), patch.object(k,'run',side_effect=[result('Status: Enabled'),result('block drop out log quick on en0 all'),result(main),result('',113)]):
                self.assertEqual(k.status(cfg,self.path)['protection'],want)
        with patch.object(k,'run',side_effect=k.SwitchError('denied')), self.assertRaises(k.SwitchError):k.status(cfg,self.path)

    def test_pf_uncovered_interface_is_not_reported_as_protected(self):
        cfg=dict(self.cfg,backend='mac_pf')
        with patch.object(k,'pf',return_value=result('WARN: en9 有 IPv4 地址但不在规则里')), patch.object(k,'run',side_effect=[result('Status: Enabled'),result('block drop out log quick on en0 all'),result('anchor \"com.apple/*\"'),result('',113)]):
            self.assertEqual(k.status(cfg,self.path)['protection'],'unknown')

    def test_on_confirmation_and_persistence_are_separate(self):
        cfg=dict(self.cfg,backend='mac_pf')
        states=[{'protection':'off','startup':False},{'protection':'on','startup':False},{'protection':'on','startup':True}]
        with patch.object(k,'status',side_effect=states), patch.object(k,'pf') as native, patch('builtins.input',return_value='KEEP'), contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(k.on(cfg,self.path)['startup'])
        self.assertEqual([c.args[1] for c in native.call_args_list],['apply','confirm','persist'])

    def test_cancel_or_expired_fuse_restores_without_persisting(self):
        cfg=dict(self.cfg,backend='mac_pf')
        for answer,elapsed in [('cancel',2),('KEEP',170)]:
            with self.subTest(answer=answer,elapsed=elapsed), patch.object(k,'status',return_value={'protection':'off','startup':False}), patch.object(k,'pf') as native, patch('builtins.input',return_value=answer), patch.object(k.time,'monotonic',side_effect=[0,elapsed]), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(k.SwitchError):
                k.on(cfg,self.path)
            self.assertEqual([c.args[1] for c in native.call_args_list],['apply','unpersist','rollback'])

    def test_already_on_is_idempotent_and_mixed_state_is_not_overwritten(self):
        with patch.object(k,'status',return_value={'protection':'on','startup':True}), patch.object(k,'pf') as native:
            self.assertEqual(k.on(dict(self.cfg,backend='mac_pf'),self.path)['protection'],'on')
            native.assert_not_called()
        with patch.object(k,'status',return_value={'protection':'on','startup':False}), self.assertRaises(k.SwitchError):k.on(self.cfg,self.path)

    def test_off_does_not_claim_success_with_unknown_startup(self):
        with patch.object(k,'require_admin'), patch.object(k,'confirm'), patch.object(k,'require_apps_closed'), patch.object(k,'off'), patch.object(k,'status',return_value={'protection':'off','startup':None}), self.assertRaises(k.SwitchError):
            k.execute('off',self.cfg,self.path)

    def test_native_timeout_and_failure_are_not_success(self):
        with patch.object(k.subprocess,'run',side_effect=subprocess.TimeoutExpired('pfctl',30)), self.assertRaises(k.SwitchError):k.run(['pfctl'])
        with patch.object(k.subprocess,'run',return_value=result(code=1)), self.assertRaises(k.SwitchError):k.run(['pfctl'])

    def test_desktop_generation_preserves_spaces_and_refuses_overwrite(self):
        dest=Path(self.tmp.name)/'desktop with spaces'
        with patch.object(u.platform,'system',return_value='Darwin'):
            u.desktop(self.path,dest)
            script=(dest/'Guardian Switch.app/Contents/MacOS/guardian-switch').read_text()
            self.assertIn(' gui --config ',script)
            self.assertTrue((dest/'Guardian Switch.app/Contents/Resources/guardian.icns').is_file())
            with self.assertRaises(FileExistsError):u.desktop(self.path,dest)
        dest=Path(self.tmp.name)/'linux desktop'
        with patch.object(u.platform,'system',return_value='Linux'):
            u.desktop(self.path,dest)
            self.assertIn('Terminal=false',(dest/'guardian-switch.desktop').read_text())

    @unittest.skipUnless(os.name == 'nt', 'Windows shortcut and console encoding')
    def test_windows_desktop_cli_with_legacy_output_encoding(self):
        output=Path(self.tmp.name)/'native desktop'
        env=dict(os.environ,PYTHONIOENCODING='cp1252')
        proc=subprocess.run([sys.executable,str(SCRIPTS/'killswitch.py'),'desktop','--config',str(self.path),'--output',str(output)],env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn('桌面入口已生成',proc.stdout)
        self.assertTrue((output/'Guardian Switch.lnk').is_file())
        command="$s=(New-Object -ComObject WScript.Shell).CreateShortcut("+u.ps_quote(output/'Guardian Switch.lnk')+");$s.TargetPath"
        actual=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,encoding='utf-8',check=True).stdout.strip()
        self.assertTrue(Path(actual).is_file())

    def test_windows_backend_parses_without_executing_commands(self):
        executable=shutil.which('powershell.exe') or shutil.which('pwsh')
        if not executable:self.skipTest('PowerShell parser unavailable')
        script=str(k.WINDOWS).replace("'","''")
        command="$e=$null;$t=$null;[System.Management.Automation.Language.Parser]::ParseFile('"+script+"',[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|Out-String|Write-Output;exit 1}"
        completed=subprocess.run([executable,'-NoProfile','-Command',command],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)

    def test_windows_effective_status_with_native_powershell_and_fixture_cmdlets(self):
        executable=shutil.which('powershell.exe') or shutil.which('pwsh')
        if not executable:self.skipTest('PowerShell unavailable')
        self.cfg['backend']='windows_firewall'
        host=subprocess.run([executable,'-NoProfile','-Command','[Environment]::MachineName'],capture_output=True,text=True,encoding='utf-8',check=True).stdout.strip()
        self.cfg['target']=host
        baseline=Path(self.tmp.name)/'baseline.json'
        self.cfg['windows']['state_path']=str(baseline)
        self.path.write_text(json.dumps(self.cfg),encoding='utf-8')
        baseline.write_text(json.dumps({'target':host,'names':['guardian-core'],
            'profiles':[{'Name':n,'Enabled':1,'DefaultOutboundAction':2} for n in ('Domain','Private','Public')],
            'rules':[{'Name':'guardian-core','Enabled':0}]}),encoding='utf-8')
        for mode,expected in [('Block','on'),('Allow','off')]:
            body="""Add-Type 'public enum TestPolicy { Allow=2, Block=4 }'
function Get-NetFirewallProfile { param($PolicyStore) @('Domain','Private','Public') | ForEach-Object { [pscustomobject]@{Name=$_;Enabled=$true;DefaultOutboundAction=[TestPolicy]::MODE} } }
function Get-NetFirewallRule { param($PolicyStore,$Name) [pscustomobject]@{Name=$Name;Enabled=ENABLED} }
& SCRIPT -Action Status -Config CONFIG
""".replace('MODE',mode).replace('ENABLED','$true' if expected=='on' else '$false').replace('SCRIPT',u.ps_quote(k.WINDOWS)).replace('CONFIG',u.ps_quote(self.path))
            fixture=Path(self.tmp.name)/'fixture.ps1';fixture.write_text(body,encoding='utf-8-sig')
            completed=subprocess.run([executable,'-NoProfile','-File',str(fixture)],capture_output=True,text=True,encoding='utf-8',errors='replace')
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertEqual(json.loads(completed.stdout.lstrip('\ufeff'))['protection'],expected)


class LocalUI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.session=u.Session(None,Path(self.tmp.name),preview=True)
        self.server=HTTPServer(('127.0.0.1',0),u.handler_for(self.session))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close)
        self.base='http://127.0.0.1:%s/%s/'%(self.server.server_port,self.session.token)

    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)

    def test_actual_http_preview_never_launches_native_commands(self):
        with patch.object(u,'launch_terminal',side_effect=AssertionError('must not launch')):
            for action,expected in [('on','on'),('off','off')]:
                req=Request(self.base+'action',data=json.dumps({'action':action}).encode(),headers={'Content-Type':'application/json'})
                with urlopen(req) as response: state=json.load(response)
                self.assertEqual(state['protection'],expected)
                self.assertTrue(state['preview'])
        with urlopen(self.base) as response:self.assertIn('Guardian Switch',response.read().decode())

    def test_rejects_cross_origin_invalid_token_unknown_actions_and_traversal(self):
        requests=[Request(self.base+'state',headers={'Origin':'https://example.com'}),Request(self.base.replace(self.session.token,'invalid')+'state'),Request(self.base+'../config.json'),Request(self.base+'action',data=b'{"action":"shell"}',headers={'Content-Type':'application/json'})]
        for req in requests:
            with self.subTest(url=req.full_url),self.assertRaises(HTTPError):urlopen(req)

    def test_receipt_is_not_success_until_read_and_old_result_is_stale(self):
        session=u.Session(None,Path(self.tmp.name))
        with patch.object(u,'launch_terminal') as launcher:
            launcher.return_value.poll.return_value = None
            session.action('on')
        self.assertTrue(session.state()['pending'])
        session.pending.write_text(json.dumps({'protection':'on','startup':True,'message':'checked','checked_at':time.time()-100,'exit_code':0}),encoding='utf-8')
        state=session.state()
        self.assertFalse(state['pending']);self.assertTrue(state['stale']);self.assertEqual(state['protection'],'on')


if __name__=='__main__':unittest.main()
