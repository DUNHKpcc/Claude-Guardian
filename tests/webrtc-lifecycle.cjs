// Synthetic browser lifecycle tests. No real browser, sockets, media or STUN.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../skills/claude-guardian/assets/webrtc-probe.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
function fixture(host = '127.0.0.1', delayed = false) {
  const elements = Object.fromEntries(['start','cancel','output','profile','consent'].map(id => [id, {disabled:false, checked:false, value:'fixture-profile', textContent:'', listeners:{}, addEventListener(name, fn){this.listeners[name]=fn;}}]));
  const lifecycle = {}, timers = [], peers = [];
  let resolveOffer;
  class Peer {
    constructor(config){this.config=config;this.closed=false;this.localCalls=0;peers.push(this);}
    createDataChannel(){this.channel={closed:false,close(){this.closed=true;}};return this.channel;}
    createOffer(){return delayed ? new Promise(resolve=>{resolveOffer=resolve;}) : Promise.resolve({type:'offer'});}
    async setLocalDescription(){this.localCalls++;}
    close(){this.closed=true;}
  }
  const context = vm.createContext({document:{getElementById:id=>elements[id]},window:{addEventListener:(name,fn)=>lifecycle[name]=fn},location:{hostname:host,origin:`http://${host}:12345`},navigator:{userAgent:'synthetic-no-network'},RTCPeerConnection:Peer,setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:()=>{},console});
  vm.runInContext(script, context);
  return {elements,peers,timers,lifecycle,approve(){elements.consent.checked=true;},click:()=>elements.start.listeners.click(),result:()=>JSON.parse(elements.output.textContent),resolveOffer:()=>resolveOffer({type:'offer'})};
}
(async()=>{
  let f=fixture(); assert.equal(f.peers.length,0); await f.click();assert.equal(f.peers.length,0);
  f=fixture('remote.example');f.approve();await f.click();assert.equal(f.peers.length,0);
  f=fixture();f.approve();await f.click();assert.equal(f.peers.length,1);assert.equal(f.elements.consent.checked,false);assert.equal(f.peers[0].config.iceServers[0].urls,'stun:stun.cloudflare.com:3478');
  f.peers[0].onicecandidate({candidate:{address:'192.0.2.1',type:'host',protocol:'udp'}});f.peers[0].iceGatheringState='complete';f.peers[0].onicegatheringstatechange();assert.equal(f.result().collection,'complete');assert.equal(f.result().path_status,'unknown');assert(!f.elements.output.textContent.includes('192.0.2.1'));assert(f.peers[0].closed);assert(f.peers[0].channel.closed);
  f=fixture();f.approve();await f.click();f.timers[0]();assert.equal(f.result().collection,'timeout');assert.equal(f.result().path_status,'unknown');assert(f.peers[0].closed);
  f=fixture();f.approve();await f.click();f.elements.cancel.listeners.click();assert.equal(f.result().collection,'cancelled');assert(f.peers[0].closed);
  f=fixture('127.0.0.1',true);f.approve();const pending=f.click();f.lifecycle.pagehide();f.resolveOffer();await pending;assert.equal(f.result().collection,'cancelled');assert.equal(f.peers[0].localCalls,0);assert(f.peers[0].closed);
  f=fixture();f.approve();await f.click();for(let i=0;i<200;i++)f.peers[0].onicecandidate({candidate:{address:'192.0.2.2',type:'host'}});f.peers[0].onicecandidateerror({errorCode:701});f.timers[0]();assert.equal(f.result().candidates.length,128);assert.equal(f.result().truncated,true);assert.equal(f.result().path_status,'unknown');
  console.log('8 synthetic WebRTC lifecycle scenarios passed; no network or real-browser certification');
})().catch(error=>{console.error(error);process.exitCode=1;});
