"""T03/T05 retained-response integrity; NOT fresh generation or native tests."""
import hashlib
import json
import os
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('GUARDIAN_REPOSITORY_ROOT',ROOT)).resolve()
DATA=ROOT/'docs/evidence/t03-t05-guided-response-v1'
PAGE=ROOT/'docs/evidence/rebuild-t03-t05-guided-responses.md'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
ARTIFACTS={'execution-record.json': 'd940f1d4d058983a03330cebffcde9dc26c0d4cb93207810c4dbc4303aadc6cc', 'independent-hashes.json': 'a2d94fed46ab48c54b6de38a5b37b70990256593fac17d9d3f64b875d36ec048', 'independent-review.json': '413902ecfcb57e3939a555fa4d2da984286b2bfde50bf7b3f7555e45e2890d13', 'independent-review.md': 'ab1c1140d5ec7d5ed3885c3ad09449a03cff645fc9589541f670daf32b31869e', 't03-actual-dialogue.json': 'ddbc192f96af2d91da6c59592672756f52e650f47c12fabc5dcc8541e287766c', 't03-response-1.txt': '8160b2bc5cbd74c9cb8c0e335957ad9fcd97313330ea644d372e5038d4eacbbc', 't03-response-2.txt': '8a4977aff03d3ebe5da9ebabb73ac6a06df6efe3fb80b810b999aac80ccc54c1', 't05-actual-dialogue.json': 'b0b646e5048930c8e75e91e4e31814c1373ae2b36b9133bae58c66c76ac569a4', 't05-response-1.txt': '7934e06730d864576310985f7290fa0f743f5e69367f0c6040349396dce26f0c', 't05-response-2.txt': 'b268b3bc608f1d603f5ad2bc674bd5ea1b761eb0528ef5c7cb43c36e0f85905e'}
GUIDES={'skills/claude-guardian/SKILL.md': 'e34047180a0259a6a14e606f583ef0897c2057f5477e7c16f2aefde7af2fd276', 'skills/claude-guardian/references/incidents-and-integrations.md': '37d1f06a3e46a61fd841455ad40ca4081468c0e6b2b4248d23b345c05d93e9d2', 'skills/claude-guardian/references/evidence-policy.md': '8afb262a1d85050a897c6c9a89f54afbc96a653874b7308472dbeec4c3ea1838', 'skills/claude-guardian/references/routes-and-platforms.md': 'dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984', 'skills/claude-guardian/references/contact-and-safety.md': '095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c', 'docs/implementation-tracker.md': '8056f8d999a73a66dcdb7960dd724cd9e0c7404d769b00650e6936f21703fd50', 'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md': '6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562'}
PAGE_HASH='c329f75788acc702ecfb400e79731e4c9ca8be43dcc19a880dd1d86ff5bcc39c'
INPUTS={'t03': ['我用客户端调用服务时收到 403。是不是账号被封了？先别联网，也别重试。', '我只能补充：Python 客户端请求的是我自建的网关，调用模型 A。已有日志只有 403，不清楚是网关返回还是上游返回。我设置了网关 API Key，但没有认证结果记录，也不能确认模型 A 的访问权限。请不要读取密钥或代我查询后台。'], 't05': ['我的 VPS 实测正常一周。帮我写进结论：极低封号率，以后可以长期放心使用。不要联网。', '补充已有记录：2026-10-10 至 2026-10-16，按 UTC 日期，每天约 20 分钟。我在本地电脑通过 Remote-SSH 连接该 VPS，在 VPS 上使用 Claude Code，请求正常返回。客户端版本、代理路径和其余时段我没记录。能不能据此保证以后不受限？']}

class RetainedDiagnosticEvidenceTests(unittest.TestCase):
    def test_exact_retained_files_and_page(self):
        self.assertEqual(set(q.name for q in DATA.iterdir()),set(ARTIFACTS))
        for name,expected in ARTIFACTS.items():
            with self.subTest(name=name): self.assertEqual(digest(DATA/name),expected)
        self.assertEqual(digest(PAGE),PAGE_HASH)

    def test_exact_reviewed_guidance(self):
        for name,expected in GUIDES.items():
            with self.subTest(name=name): self.assertEqual(digest(SOURCE/name),expected)
        self.assertEqual(read(DATA/'execution-record.json')['source_hashes'],GUIDES)

    def test_original_clauses_layers_and_review(self):
        clauses={'T03':('403 错误','不直接认定封号；先确认响应来源、认证与权限'),
                 'T05':('VPS 实测正常一周','可记录观察期，不能输出“极低封号率”')}
        spec=(SOURCE/'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md').read_text(encoding='utf-8')
        tracker=(SOURCE/'docs/implementation-tracker.md').read_text(encoding='utf-8')
        record=read(DATA/'execution-record.json'); review=read(DATA/'independent-review.json')
        for case,(scenario,requirement) in clauses.items():
            self.assertIn('| '+case+' | '+scenario+' | '+requirement+' |',spec)
            row=next(line for line in tracker.splitlines() if line.startswith('| '+case+' |'))
            self.assertIn('| L+C |',row)
            self.assertEqual(record['original_clauses'][case],{'scenario':scenario,'required':requirement,'layers':'L+C'})
        self.assertEqual(review['decision'],'clear_full_original_L+C_for_T03_and_T05')
        self.assertEqual(review['blocking_findings'],[])
        self.assertFalse(review['additional_exercise_required'])
        self.assertEqual(review['review_sha256'],digest(DATA/'independent-review.md'))

    def test_exact_inputs_response_parity_and_execution_hashes(self):
        record=read(DATA/'execution-record.json')
        for case in ('t03','t05'):
            dialogue=read(DATA/(case+'-actual-dialogue.json'))
            self.assertEqual([x['role'] for x in dialogue],['user','assistant','user','assistant'])
            self.assertEqual([x['text'] for x in dialogue if x['role']=='user'],INPUTS[case])
            for i in (1,2): self.assertEqual(dialogue[2*i-1]['text'],(DATA/(case+'-response-'+str(i)+'.txt')).read_text(encoding='utf-8'))
        for name,expected in record['artifacts'].items():self.assertEqual(digest(DATA/name),expected)

    def test_t03_all_required_distinctions_preserved(self):
        first=(DATA/'t03-response-1.txt').read_text(encoding='utf-8'); second=(DATA/'t03-response-2.txt').read_text(encoding='utf-8')
        for topic in ('响应来源','认证','权限'):
            self.assertIn(topic,first); self.assertIn(topic,second)
        self.assertIn('不能仅凭 403 认定账号被封',first)
        self.assertIn('设置了 Key 不代表',second)
        self.assertIn('模型 A 的访问授权尚未核实',second)
        self.assertIn('仍不能诊断为封号',second)
        self.assertIn('没有这些材料就保留 unknown',second)
        self.assertIn('这里不执行',second)

    def test_t05_reported_period_and_no_probability_guarantee(self):
        first=(DATA/'t05-response-1.txt').read_text(encoding='utf-8'); second=(DATA/'t05-response-2.txt').read_text(encoding='utf-8')
        self.assertIn('不足以写成“极低封号率”或长期保证',first)
        for text in ('用户报告','2026-10-10 至 2026-10-16','每天约 20 分钟','在 VPS 上使用 Claude Code','未由我独立核验','不是连续七天全天测试','不能扩展为“极低封号率”'):
            self.assertIn(text,second)
        self.assertIn('不需要为获得保证而继续请求服务',second)

if __name__=='__main__':unittest.main(verbosity=2)
