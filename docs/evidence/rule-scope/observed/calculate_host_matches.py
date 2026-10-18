"""Transparent offline string matching for supplied synthetic host fixtures.
Not a Guardian API, DNS lookup, Mihomo execution, or runtime verification.
"""
import sys
sys.path.insert(0,'/tmp/guardian-rule-scope-responses')
from evidence_tools import *
import yaml

def matches(host,rule):
    fields=rule.split(',');kind=fields[0]
    if kind=='MATCH': return True
    selector=fields[1]
    if kind=='DOMAIN': return host==selector
    if kind=='DOMAIN-SUFFIX': return host==selector or host.endswith('.'+selector)
    if kind=='DOMAIN-KEYWORD': return selector in host
    raise ValueError('Unsupported offline analysis predicate: '+kind)
def first(host,rules):
    for i,r in enumerate(rules):
        if matches(host,r): return {'index':i,'rule':r,'action':r.split(',')[-1]}
    return None

if __name__=='__main__':
    mode=sys.argv[1]
    base=yaml.safe_load(read('fixtures/effective-base.yaml'))['rules']
    ext=yaml.safe_load(read('fixtures/owned-rules-extension.yaml'))
    before=ext['prepend']+base+ext['append']
    hosts=obj('fixtures/env-t41-host-matrix.json')['hosts']
    if mode=='keyword':
        proposed=yaml.safe_load(read('fixtures/env-t41-keyword-source.yaml'))['rules']
        result={'method':'Python exact equality, dot-label-boundary suffix, or literal substring; ordered first match. Synthetic declared merge: prepend + base + append, delete empty. Hypothetical broad rules are not a chosen candidate.','before_rules':before,'hypothetical_keyword_prepend':proposed,'rows':[{'host':h,'matching_proposed_rules':[r for r in proposed if matches(h,r)],'before':first(h,before),'hypothetical_after':first(h,proposed+before)} for h in hosts]}
        dump(ROOT/'ENV-T41-turn-1-keyword-analysis.json',result)
    elif mode=='exact':
        candidate=yaml.safe_load((ROOT/'traces/ENV-T41-turn-2-compile/candidate.yaml').read_bytes())
        after=candidate['prepend']+base+candidate['append']
        suffixes=['DOMAIN-SUFFIX,sentry.invalid,approved-group','DOMAIN-SUFFIX,datadoghq.com,approved-group','DOMAIN-SUFFIX,sift.invalid,approved-group']
        result={'method':'Pure offline first-match string analysis only; no lookup or routing execution. Suffix examples are explanatory only, not imported or compiled.','before_rules':before,'after_rules':after,'hypothetical_wide_suffix_prepend':suffixes,'rows':[{'host':h,'before':first(h,before),'after':first(h,after),'matching_hypothetical_suffixes':[r for r in suffixes if matches(h,r)]} for h in hosts]}
        dump(ROOT/'ENV-T41-turn-2-host-matrix.json',result)
    else: raise ValueError(mode)
    event('offline_host_match_calculation',case_id='ENV-T41',mode=mode,script_sha256=sha(pathlib.Path(__file__).read_bytes()),host_count=len(hosts))
    print(json.dumps(result,ensure_ascii=False,indent=2))
