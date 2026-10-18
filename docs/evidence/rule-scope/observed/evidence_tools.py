"""Local evidence capture only. Responses are authored by the responding agent.
This utility does not contain responses, expected answers, grading or acceptance.
"""
import base64, copy, dataclasses, datetime, difflib, hashlib, inspect, json, pathlib, sys, traceback
ROOT=pathlib.Path('/tmp/guardian-rule-scope-responses')
INPUT=pathlib.Path('/tmp/guardian-rule-scope-candidate/generator-inputs')
REPO=pathlib.Path('/workspace/scratch/887ef42f8bd2/Claude-Guardian-thirtyfirst')
SCRIPTS=REPO/'skills/claude-guardian/scripts'
sys.path.insert(0,str(SCRIPTS))
sys.dont_write_bytecode=True

def sha(raw): return hashlib.sha256(raw).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(name): return (INPUT/name).read_bytes()
def obj(name): return json.loads(read(name))
def encode(x):
    if isinstance(x,bytes):
        return {'type':'bytes','base64':base64.b64encode(x).decode(),'sha256':sha(x),'length':len(x),'utf8':x.decode('utf-8')}
    if dataclasses.is_dataclass(x): return {'type':type(x).__name__,'fields':{f.name:encode(getattr(x,f.name)) for f in dataclasses.fields(x)}}
    if isinstance(x,tuple): return {'type':'tuple','items':[encode(v) for v in x]}
    if isinstance(x,list): return [encode(v) for v in x]
    if isinstance(x,dict): return {k:encode(v) for k,v in x.items()}
    if x is None or isinstance(x,(str,bool,int,float)): return x
    if callable(x): return {'type':'callable','name':x.__qualname__}
    raise TypeError(type(x).__name__)
def dump(path,x):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(encode(x),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def event(kind,**fields):
    with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps({'time_utc':now(),'kind':kind,**fields},ensure_ascii=False)+'\n')
def capture(call_id,func,*args,**kwargs):
    p=ROOT/'traces'/call_id;p.mkdir(parents=True,exist_ok=False)
    trace={'call_id':call_id,'callable':func.__module__+'.'+func.__qualname__,'signature':str(inspect.signature(func)),'positional_arguments':args,'keyword_arguments':kwargs,'started_at':now(),'default_arguments':'Omitted keyword-only defaults are the function defaults shown in signature. No live authorization callback supplied.'}
    dump(p/'input.json',trace)
    try:
        result=func(*args,**kwargs)
        output={'return_type':type(result).__name__}
        if isinstance(result,dict): output['result']=result
        else:
            output['repr']=repr(result)
            for method in ('preview','binding_components','private_material'):
                if hasattr(result,method): output[method]=getattr(result,method)()
        dump(p/'output.json',output)
        if 'private_material' in output and 'candidate_bytes' in output['private_material']:
            mat=output['private_material'];original=mat['original_bytes'];candidate=mat['candidate_bytes']
            (p/'original.yaml').write_bytes(original);(p/'candidate.yaml').write_bytes(candidate)
            diff=''.join(difflib.unified_diff(original.decode().splitlines(keepends=True),candidate.decode().splitlines(keepends=True),fromfile='original-supplied-snapshot',tofile='unapplied-candidate',n=100000))
            (p/'complete.diff').write_text(diff,encoding='utf-8')
        event('helper_return',call_id=call_id,return_type=type(result).__name__)
        print(call_id,json.dumps(output.get('preview',output.get('result',{})),ensure_ascii=False))
        return result
    except Exception as exc:
        dump(p/'error.json',{'exception_module':type(exc).__module__,'exception_type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc(),'finished_at':now()})
        event('helper_error',call_id=call_id,exception_type=type(exc).__name__,message=str(exc))
        print(call_id,type(exc).__name__,str(exc));return None

def source_binding(file,ref,feature,version='synthetic-fixture-v1',shared=False):
    return {'schema_version':'guardian-rule-source-binding/0.1','source_ref':ref,'expected_sha256':sha(read(file)),'evidence_kind':'user_supplied','verified_at':'2026-10-18','version_scope':version,'purpose':'workflow-repair','client_scope':['fixture-client'],'feature_gate':feature,'shared_service':shared,'activation_state':'candidate'}
def extension_request(refs):
    req=copy.deepcopy(obj('fixtures/synthetic-semantic-request.json'))
    req['intent']['rule_refs']=list(refs)
    return req

def extension_binding(parts):
    return {'schema_version':'guardian-rules-extension-binding/0.1','operation':'insert_selected_prepend_rules','target_ref':'lab-device','scope_refs':['workflow-a'],'layer_ref':'extension','base_layer_ref':'effective','layer_kind':'owned-profile-rules-extension','placement':'prepend','group_name':parts['group_name'],'rules':parts['rules'],'rule_order':parts['rule_order'],'protected_rule_indexes':[0,1]}

def save_response(case_id,turn):
    answer=ROOT/'responses'/f'{case_id}-turn-{turn}.md'
    text=answer.read_text(encoding='utf-8')
    scenarios=obj('scenarios.json');case=next(c for c in scenarios['cases'] if c['id']==case_id)
    if turn>1 and not (ROOT/'responses'/f'{case_id}-turn-{turn-1}.md').exists(): raise ValueError('prior response missing')
    conversation='# '+case_id+'：离线合成对话\n\n'+scenarios['common_context']['notice']+'\n\n'
    for t in case['turns'][:turn]:
        conversation+=f'## 第 {t["turn"]} 轮 · 用户\n\n{t["user"]}\n\n## 第 {t["turn"]} 轮 · Claude-Guardian\n\n'
        conversation+=(ROOT/'responses'/f'{case_id}-turn-{t["turn"]}.md').read_text(encoding='utf-8')+'\n\n'
    path=ROOT/'conversations'/f'{case_id}-through-turn-{turn}.md';path.parent.mkdir(exist_ok=True)
    path.write_text(conversation,encoding='utf-8')
    event('response_saved',case_id=case_id,turn=turn,response=str(answer.relative_to(ROOT)),sha256=sha(text.encode()),conversation=str(path.relative_to(ROOT)))
