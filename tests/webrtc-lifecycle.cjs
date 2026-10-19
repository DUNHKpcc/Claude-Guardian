// Synthetic browser lifecycle tests. No real browser, sockets, media or STUN.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../skills/claude-guardian/assets/webrtc-probe.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const REFERENCE = '198.51.100.27';
const DIFFERENT = '203.0.113.43';
const IPV6 = '2001:db8::beef';
const STUN = 'stun:stun.cloudflare.com:3478';
const fixtures = [];
function fixture(host = '127.0.0.1', delayed = false, options = {}) {
  const writes = [], externalCalls = [], logs = [], maps = [];
  const elements = Object.fromEntries(['start','cancel','output','profile','consent','expected_ipv4'].map(id => {
    let text = '';
    return [id, {disabled:false, checked:false, value:id==='profile'?'fixture-profile':'', listeners:{},
      get textContent(){return text;},set textContent(value){text=value;writes.push(value);},
      addEventListener(name, fn){this.listeners[name]=fn;}}];
  }));
  const lifecycle = {}, timers = [], peers = [], clearedTimers = [];
  let resolveOffer;
  const forbidden = name => (...args) => {externalCalls.push({name,args});throw new Error(`Forbidden synthetic API: ${name}`);};
  const storage = {setItem:forbidden('storage.setItem'),getItem:forbidden('storage.getItem'),removeItem:forbidden('storage.removeItem')};
  class TrackedMap extends Map {constructor(...args){super(...args);maps.push(this);}}
  class Peer {
    constructor(config){
      if(options.onConstruct) options.onConstruct(elements);
      if(options.constructorError) throw new Error(options.constructorError);
      this.config=config;this.closed=false;this.localCalls=0;peers.push(this);
    }
    createDataChannel(name){this.channel={name,closed:false,close(){this.closed=true;},send:forbidden('dataChannel.send')};return this.channel;}
    createOffer(){return delayed ? new Promise(resolve=>{resolveOffer=resolve;}) : Promise.resolve({type:'offer'});}
    async setLocalDescription(){this.localCalls++;}
    close(){this.closed=true;}
  }
  const context = vm.createContext({document:{getElementById:id=>elements[id],createElement:forbidden('document.createElement')},
    window:{addEventListener:(name,fn)=>lifecycle[name]=fn,open:forbidden('window.open')},
    location:{hostname:host,origin:`http://${host}:12345`,search:'?expected_ipv4=192.0.2.201',hash:'#192.0.2.202'},
    navigator:{userAgent:'synthetic-no-network',sendBeacon:forbidden('sendBeacon'),mediaDevices:{getUserMedia:forbidden('getUserMedia')}},
    RTCPeerConnection:Peer,Map:TrackedMap,
    fetch:forbidden('fetch'),XMLHttpRequest:forbidden('XMLHttpRequest'),WebSocket:forbidden('WebSocket'),EventSource:forbidden('EventSource'),
    localStorage:storage,sessionStorage:storage,indexedDB:{open:forbidden('indexedDB.open')},
    URL:{createObjectURL:forbidden('createObjectURL')},URLSearchParams:forbidden('URLSearchParams'),Blob:forbidden('Blob'),
    crypto:{subtle:{digest:forbidden('digest')}},
    setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:id=>clearedTimers.push(id),
    console:{log:(...args)=>logs.push(args),error:(...args)=>logs.push(args),warn:(...args)=>logs.push(args)}});
  vm.runInContext(script, context);
  const f = {elements,peers,timers,lifecycle,writes,externalCalls,logs,maps,clearedTimers,
    approve(){elements.consent.checked=true;},click:()=>elements.start.listeners.click(),
    result:()=>JSON.parse(elements.output.textContent),comparison:()=>f.result().ipv4_reference_comparison,
    resolveOffer:()=>resolveOffer({type:'offer'}),
    candidate(address,type='srflx',protocol='udp'){peers.at(-1).onicecandidate({candidate:{address,type,protocol}});},
    complete(){const p=peers.at(-1);p.iceGatheringState='complete';p.onicegatheringstatechange();}};
  fixtures.push(f);
  return f;
}
async function begin(reference = '', options = {}) {
  const f=fixture('127.0.0.1', false, options);f.elements.expected_ipv4.value=reference;f.approve();await f.click();return f;
}
function counts(f, expected) {
  for(const [key,value] of Object.entries(expected)) assert.equal(f.comparison()[key],value,key);
  assert.equal(f.comparison().reference_source,'user_supplied_https_sample');
  assert.equal(f.result().path_status,'unknown');
  assert.equal(f.result().path_association,'unknown');
  assert.equal(f.result().selected_media_path,'not_observed');
  assert.equal(f.result().effective_browser_policy,'not_observed');
}
function cleaned(f) {
  assert.equal(f.elements.expected_ipv4.value,'');
  assert.equal(f.elements.expected_ipv4.disabled,false);
  assert.equal(f.elements.start.disabled,false);
  assert.equal(f.elements.cancel.disabled,true);
  assert(f.maps.every(map=>map.size===0),'Temporary candidate address maps must be cleared');
  for(const p of f.peers) {
    assert(p.closed);assert(p.channel.closed);
    assert.equal(p.onicecandidate,null);assert.equal(p.onicecandidateerror,null);assert.equal(p.onicegatheringstatechange,null);
  }
}
let passed=0;
async function scenario(name, run) {await run();passed++;console.log(`PASS ${name}`);}
(async()=>{
  await scenario('No sample on load or without consent',async()=>{
    const f=fixture();assert.equal(f.peers.length,0);await f.click();assert.equal(f.peers.length,0);assert.equal(f.timers.length,0);
    f.elements.profile.value='';f.approve();await f.click();assert.equal(f.peers.length,0);
  });
  await scenario('Remote origins remain rejected',async()=>{
    const f=fixture('remote.example');f.approve();await f.click();assert.equal(f.peers.length,0);
  });
  await scenario('Exact manual STUN consent and all-candidate configuration',async()=>{
    const f=await begin();assert.equal(f.peers.length,1);assert.equal(f.elements.consent.checked,false);
    assert.equal(f.peers[0].config.iceServers.length,1);assert.equal(f.peers[0].config.iceServers[0].urls,STUN);
    assert.equal(f.peers[0].config.iceTransportPolicy,'all');assert.equal(f.peers[0].config.iceCandidatePoolSize,0);
    f.candidate('192.0.2.1','host');f.complete();assert.equal(f.result().collection,'complete');assert(!f.elements.output.textContent.includes('192.0.2.1'));cleaned(f);
  });
  await scenario('Matching canonical srflx IPv4 is same with count-only results',async()=>{
    const f=await begin(REFERENCE);f.candidate(REFERENCE);f.candidate(REFERENCE);f.complete();
    counts(f,{reference_status:'valid',comparison:'same',srflx_ipv4_candidates:2,comparable_ipv4_candidates:2,matching_ipv4_candidates:2,different_ipv4_candidates:0,srflx_ipv6_candidates:0});cleaned(f);
  });
  await scenario('Mismatch stays different after later matching candidates',async()=>{
    const f=await begin(REFERENCE);f.candidate(REFERENCE);f.candidate(DIFFERENT);f.candidate(REFERENCE);f.complete();
    counts(f,{comparison:'different',srflx_ipv4_candidates:3,comparable_ipv4_candidates:3,matching_ipv4_candidates:2,different_ipv4_candidates:1});
  });
  await scenario('Missing reference cannot infer a match from candidates or URL parameters',async()=>{
    const f=await begin();f.candidate(REFERENCE);f.complete();counts(f,{reference_status:'missing',comparison:'unknown',srflx_ipv4_candidates:1,comparable_ipv4_candidates:0,matching_ipv4_candidates:0,different_ipv4_candidates:0});
  });
  await scenario('Invalid references never become comparable or enter results',async()=>{
    const invalid=['https://198.51.100.27','198.51.100.27:443','198.051.100.27','01.2.3.4','1.2.3','1.2.3.4.5','256.1.2.3','-1.2.3.4','+1.2.3.4','0x01.2.3.4','1e2.2.3.4','1.2.3.4\n',' 1.2.3.4','1.2.3.4 ','1.2.3.4/32',IPV6,'peer.local','１.2.3.4','INVALID-PRIVATE-SENTINEL'];
    for(const value of invalid) {const f=await begin(value);f.candidate(REFERENCE);f.complete();counts(f,{reference_status:'invalid',comparison:'unknown',comparable_ipv4_candidates:0});assert(!f.elements.output.textContent.includes(value));cleaned(f);}
  });
  await scenario('Canonical private and special IPv4 inputs do not certify public scope',async()=>{
    for(const value of ['0.0.0.0','10.0.0.1','100.64.0.1','127.0.0.1','192.168.0.1','255.255.255.255']) {
      const f=await begin(value);f.candidate(value);f.complete();counts(f,{reference_status:'valid',comparison:'same',comparable_ipv4_candidates:1});
    }
  });
  await scenario('Host, mDNS, prflx and relay addresses are not reference comparisons',async()=>{
    const f=await begin(REFERENCE);f.candidate(REFERENCE,'host');f.candidate(DIFFERENT,'host');f.candidate('privacy-sentinel.local','host');f.candidate(DIFFERENT,'prflx');f.candidate(DIFFERENT,'relay');f.candidate('privacy-sentinel.local');f.complete();
    counts(f,{comparison:'unknown',srflx_ipv4_candidates:0,comparable_ipv4_candidates:0,srflx_ipv6_candidates:0});
  });
  await scenario('Malformed and ambiguous candidate IPv4 addresses are not comparable',async()=>{
    const f=await begin(REFERENCE);for(const address of ['198.051.100.27','198.51.100.027','198.51.100.27\n','198.51.100.27:80','256.51.100.27','',undefined])f.candidate(address);f.complete();
    counts(f,{comparison:'unknown',srflx_ipv4_candidates:0,comparable_ipv4_candidates:0});
  });
  await scenario('IPv6-only srflx is separately observed and IPv4 comparison stays unknown',async()=>{
    const f=await begin(REFERENCE);f.candidate(IPV6);f.complete();counts(f,{comparison:'unknown',srflx_ipv4_candidates:0,comparable_ipv4_candidates:0,srflx_ipv6_candidates:1});
  });
  await scenario('Mixed-family samples retain IPv6 observation alongside IPv4 equality',async()=>{
    const f=await begin(REFERENCE);f.candidate(REFERENCE);f.candidate(IPV6);f.complete();counts(f,{comparison:'same',matching_ipv4_candidates:1,srflx_ipv6_candidates:1});
  });
  await scenario('No candidates remain unknown even after complete',async()=>{
    const f=await begin(REFERENCE);f.peers[0].onicecandidate({candidate:null});f.complete();counts(f,{comparison:'unknown',comparable_ipv4_candidates:0});
  });
  await scenario('Timeout without candidates remains unknown and closes resources',async()=>{
    const f=await begin(REFERENCE);f.timers[0]();assert.equal(f.result().collection,'timeout');counts(f,{comparison:'unknown'});cleaned(f);
  });
  await scenario('Error 701 is retained and is never a passing path result',async()=>{
    const f=await begin(REFERENCE);f.peers[0].onicecandidateerror({errorCode:701,errorText:REFERENCE,url:DIFFERENT});f.complete();
    assert.equal(f.result().errors[0].code,701);counts(f,{comparison:'unknown'});
    const g=await begin(REFERENCE);g.candidate(REFERENCE);g.peers[0].onicecandidateerror({errorCode:701});g.complete();counts(g,{comparison:'same'});assert.equal(g.result().errors[0].code,701);
  });
  await scenario('Aggregate observes mismatches after the retained candidate cap',async()=>{
    const f=await begin(REFERENCE);for(let i=0;i<128;i++)f.candidate(REFERENCE);f.candidate(DIFFERENT);f.candidate(REFERENCE);f.candidate(IPV6);f.complete();
    assert.equal(f.result().candidates.length,128);assert.equal(f.result().truncated,true);
    counts(f,{comparison:'different',srflx_ipv4_candidates:130,comparable_ipv4_candidates:130,matching_ipv4_candidates:129,different_ipv4_candidates:1,srflx_ipv6_candidates:1});cleaned(f);
  });
  await scenario('Host candidate truncation preserves unknown comparison and 701',async()=>{
    const f=await begin(REFERENCE);for(let i=0;i<200;i++)f.candidate(DIFFERENT,'host');f.peers[0].onicecandidateerror({errorCode:701});f.timers[0]();
    assert.equal(f.result().candidates.length,128);assert.equal(f.result().truncated,true);counts(f,{comparison:'unknown'});
  });
  await scenario('Error cap remains bounded with explicit truncation',async()=>{
    const f=await begin(REFERENCE);for(let i=0;i<50;i++)f.peers[0].onicecandidateerror({errorCode:701});f.complete();assert.equal(f.result().errors.length,32);assert.equal(f.result().truncated,true);counts(f,{comparison:'unknown'});
  });
  await scenario('Reference clears before peer creation and is frozen against mid-run input edits',async()=>{
    const f=await begin(REFERENCE,{onConstruct:elements=>assert.equal(elements.expected_ipv4.value,'')});assert.equal(f.elements.expected_ipv4.disabled,true);
    f.elements.expected_ipv4.value=DIFFERENT;f.candidate(REFERENCE);f.complete();counts(f,{comparison:'same',matching_ipv4_candidates:1});cleaned(f);
  });
  await scenario('A second sample cannot reuse the previous temporary reference',async()=>{
    const f=await begin(REFERENCE);f.candidate(REFERENCE);f.complete();f.approve();await f.click();f.candidate(REFERENCE);f.complete();
    counts(f,{reference_status:'missing',comparison:'unknown',comparable_ipv4_candidates:0});cleaned(f);
  });
  await scenario('Cancel clears input, reference and candidate maps',async()=>{
    const f=await begin(REFERENCE);f.candidate(REFERENCE);f.elements.expected_ipv4.value=DIFFERENT;f.elements.cancel.listeners.click();assert.equal(f.result().collection,'cancelled');cleaned(f);
  });
  await scenario('Pagehide before start clears an unsampled input',async()=>{
    const f=fixture();f.elements.expected_ipv4.value=REFERENCE;f.lifecycle.pagehide();assert.equal(f.elements.expected_ipv4.value,'');assert.equal(f.peers.length,0);
  });
  await scenario('Pagehide after sample finish clears a newly entered reference',async()=>{
    const f=await begin(REFERENCE);f.complete();f.elements.expected_ipv4.value=DIFFERENT;f.lifecycle.pagehide();assert.equal(f.elements.expected_ipv4.value,'');
  });
  await scenario('Pagehide during a pending offer cancels and prevents late local description',async()=>{
    const f=fixture('127.0.0.1',true);f.elements.expected_ipv4.value=REFERENCE;f.approve();const pending=f.click();f.lifecycle.pagehide();f.resolveOffer();await pending;
    assert.equal(f.result().collection,'cancelled');assert.equal(f.peers[0].localCalls,0);cleaned(f);
  });
  await scenario('Late saved callbacks after finish cannot alter the completed result',async()=>{
    const f=await begin(REFERENCE);const callback=f.peers[0].onicecandidate;f.complete();const before=f.elements.output.textContent;
    callback({candidate:{address:REFERENCE,type:'srflx',protocol:'udp'}});f.timers[0]();assert.equal(f.elements.output.textContent,before);cleaned(f);
  });
  await scenario('Browser API errors clear the input without reflecting exception content',async()=>{
    const f=await begin(REFERENCE,{constructorError:`PRIVATE EXCEPTION ${REFERENCE} ${DIFFERENT}`});assert.equal(f.result().collection,'error');counts(f,{comparison:'unknown'});assert.equal(f.result().errors[0].code,'browser_api_error');assert.equal(f.elements.expected_ipv4.value,'');
  });
  await scenario('Page copy preserves exact consent and explicit comparison limitations',async()=>{
    assert(html.includes('I authorize this one ICE sample with a requested 12-second collection window from this browser and profile, including local candidate gathering and STUN traffic to exactly stun:stun.cloudflare.com:3478 via its current WebRTC routing'));
    assert(html.includes('locally visible before you start'));assert(html.includes('same path'));assert(html.includes('whole machine'));assert(html.includes('IPv4-only'));assert(html.includes('701'));assert(html.includes('truncat'));
    assert(html.includes('autocomplete="off"'));assert(html.includes('connect-src \'none\''));
    assert(!/\b(fetch|XMLHttpRequest|WebSocket|EventSource|localStorage|sessionStorage|indexedDB|sendBeacon|URLSearchParams|createObjectURL|digest)\b/.test(script));
    assert(!/\.candidate\b[^;\n]*\.candidate\b|\.sdp\b/.test(script),'Do not inspect/export full ICE strings or SDP');
    assert(/expectedIPv4\s*=\s*null/.test(script),'Temporary reference must be released on terminal cleanup');
  });
  await scenario('Privacy sentinels never enter output, logs or external APIs',async()=>{
    for(const f of fixtures) {
      for(const value of [REFERENCE,DIFFERENT,IPV6,'privacy-sentinel.local','INVALID-PRIVATE-SENTINEL','192.0.2.201','192.0.2.202']) assert(!f.writes.some(write=>write.includes(value)),`Raw sentinel rendered: ${value}`);
      assert.deepEqual(f.externalCalls,[]);assert.deepEqual(f.logs,[]);
    }
  });
  console.log(`${passed} synthetic WebRTC lifecycle/comparison scenarios passed; no network or real-browser certification`);
})().catch(error=>{console.error(error);process.exitCode=1;});
