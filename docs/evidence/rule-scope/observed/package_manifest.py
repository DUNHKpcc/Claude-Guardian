"""Package factual provenance; no acceptance assertions or source modifications."""
import sys, pathlib, subprocess, re
sys.path.insert(0,'/tmp/guardian-rule-scope-responses');from evidence_tools import *
import rule_source_import,rules_extension_plan,config_edit_plan,remedy_plans,yaml
source_paths=[
 'AGENTS.md','skills/claude-guardian/SKILL.md',
 'skills/claude-guardian/references/contact-and-safety.md',
 'skills/claude-guardian/references/network-and-remedies.md',
 'skills/claude-guardian/references/agent-remediation.md',
 'docs/config-edit-plan.md','docs/rules-extension-plan.md','docs/remedy-plans.md',
]
for name,module in sorted(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if file and pathlib.Path(file).is_relative_to(REPO):
  rel=str(pathlib.Path(file).relative_to(REPO))
  if rel not in source_paths: source_paths.append(rel)
sources=[]
for rel in source_paths:
 raw=(REPO/rel).read_bytes();dest=ROOT/'source-snapshots'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 sources.append({'repository_path':rel,'saved_copy':str(dest.relative_to(ROOT)),'sha256':sha(raw),'bytes':len(raw),'hash_capture_stage':'final packaging; no initial pre-call source hash was separately logged'})
events=[json.loads(line) for line in (ROOT/'events.jsonl').read_text().splitlines()]
helper_events=[x for x in events if x['kind'] in ('helper_return','helper_error')]
responses=[x for x in events if x['kind']=='response_saved']
scenario=obj('scenarios.json')
links=[]
for p in (ROOT/'responses').glob('*.md'):
 for url in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  dest=(p.parent/url).resolve()
  links.append({'from':str(p.relative_to(ROOT)),'relative_target':url,'exists':dest.exists()})
# Inventory consistency is evidence bookkeeping, not acceptance grading.
checks={'linked_artifact_count':len(links),'missing_link_targets':[x for x in links if not x['exists']],
 'response_files':len(list((ROOT/'responses').glob('*.md'))),
 'conversation_files':len(list((ROOT/'conversations').glob('*.md'))),
 'candidate_files':len(list((ROOT/'traces').glob('*/candidate.yaml'))),
 'helper_invocations':len(helper_events),
 'helper_exception_count':sum(x['kind']=='helper_error' for x in helper_events)}
for row in responses:
 p=ROOT/row['response'];row['hash_at_packaging']=sha(p.read_bytes());row['same_bytes_as_saved_event']=row['sha256']==row['hash_at_packaging']
input_manifest=json.loads((ROOT/'input-manifest.json').read_text())
input_checks=[]
for row in input_manifest['files']:
 orig=pathlib.Path(row['path']).read_bytes();saved=(ROOT/row['saved_copy']).read_bytes()
 input_checks.append({'path':row['path'],'original_sha256_at_packaging':sha(orig),'saved_copy_sha256':sha(saved),'same_as_initial_capture':sha(orig)==row['sha256']==sha(saved)})
outputs=[]
for p in sorted(ROOT.rglob('*')):
 if p.is_file() and p.name not in ('provenance-manifest.json','provenance-manifest.sha256'):
  raw=p.read_bytes();outputs.append({'path':str(p.relative_to(ROOT)),'sha256':sha(raw),'bytes':len(raw)})
manifest={
 'schema':'guardian-offline-response-provenance/1','created_at_utc':now(),
 'response_generation':'Chinese responses directly authored by this responding Agent, one turn at a time with saved prior turns; no answer generator or canned response template used',
 'input_boundary':'scenarios.json and its referenced fixtures only; active skill/references and applicable helper API/source code consulted. No review-only materials, helper-trace-plan, handoff, planning documents, original-case ledgers/evidence, or evaluation rubric were opened.',
 'source_repository':str(REPO),'repository_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
 'repository_state_note':'Repository already contains modifications from other work. This responding Agent did not edit source or tests. Final source snapshots are supplied for the exact files used; no claim is made that HEAD alone identifies the used working tree.',
 'python_version':sys.version,'pyyaml_version':yaml.__version__,
 'required_scenario_order':scenario['scenario_order'],
 'actual_response_generation_order':[{'sequence':i+1,**row} for i,row in enumerate(responses)],
 'actual_helper_call_order':[{'sequence':i+1,**row,'input':f'traces/{row["call_id"]}/input.json','output_or_error':f'traces/{row["call_id"]}/'+('error.json' if row['kind']=='helper_error' else 'output.json')} for i,row in enumerate(helper_events)],
 'helper_trace_notes':['Calls were made against existing imported repository functions. capture records positional/keyword arguments before invocation and exact returned dictionaries or actual object getter outputs afterward.','For object results the getters preview(), binding_components() if present, and private_material() were actually invoked without arguments. Tuple and bytes tags make the recorded values reconstructible.','compile_edit_plan and compile_rules_extension each call remedy_plans.compile_plan internally; separate explicit semantic calls were also made to retain the IPv4-only conflict projection.','No callbacks granting authorization were supplied; omitted limits/cancellation use the existing API defaults listed in input.json.','Both rejected mixed rule batches were preserved whole; no partial returned object existed.'],
 'input_manifest':input_manifest,'input_recheck':input_checks,'source_hashes':sources,
 'artifact_inventory':outputs,'artifact_bookkeeping':checks,
 'known_limits':['All evidence is offline and synthetic. Candidates are unapplied. Native acceptance not run.','The source inputs include a deliberately retained legacy ipv6_goal=preserve declaration. IPV4_ONLY_INTENT_CONFLICT remains in every captured semantic output; target-policy compliance is not established.','Source authenticity, freshness, installation, ownership, runtime merge and real effective routes remain unestablished.','Source hashes were captured at final packaging, not before each invocation; function arguments and returns/errors were recorded at invocation time.','There is no grading or overall acceptance/pass/fail conclusion in this package.'],
 'actions_not_taken':['network requests','browser use','Claude or Anthropic contact','native device operations','host setting changes','installation','real cleanup','credential reads','candidate application','source or test edits']
}
dump(ROOT/'provenance-manifest.json',manifest)
(ROOT/'provenance-manifest.sha256').write_text(sha((ROOT/'provenance-manifest.json').read_bytes())+'  provenance-manifest.json\n')
print(json.dumps(checks,ensure_ascii=False,indent=2))
print('Input unchanged observations:',sum(x['same_as_initial_capture'] for x in input_checks),'/',len(input_checks))
print('Response unchanged observations:',sum(x['same_bytes_as_saved_event'] for x in responses),'/',len(responses))
