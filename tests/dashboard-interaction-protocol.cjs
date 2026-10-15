'use strict';
// Synthetic pipe/DOM fixtures only. This file never starts Chrome.
const assert = require('node:assert/strict');
const {EventEmitter} = require('node:events');
const {PipeClient, checkViewport, keyboardEvents, InteractionError, failureRecord} = require('../tools/check_dashboard_interactions.cjs');
function fixture() {
  const child = new EventEmitter(); child.stdio = Array.from({length:5}, () => new EventEmitter());
  const writes = [];
  child.stdio[3].write = data => writes.push(JSON.parse(data.slice(0, -1)));
  return {client: new PipeClient(child), child, writes};
}
async function tests() {
  for (const [name, text, downType, virtualKey] of [['Enter','\r','keyDown',13],['Space',' ','keyDown',32],['Tab','','rawKeyDown',9]]) {
    const [down, up] = keyboardEvents(name);
    assert.equal(down.type,downType); assert.equal(down.text,text); assert.equal(down.unmodifiedText,text);
    assert.equal(down.windowsVirtualKeyCode,virtualKey); assert.equal(up.windowsVirtualKeyCode,virtualKey);
    assert.equal(up.type,'keyUp'); assert.equal(down.modifiers,0); assert.equal(up.modifiers,0);
    assert.ok(!('text' in up)); assert.ok(!('nativeVirtualKeyCode' in down)); assert.ok(!('nativeVirtualKeyCode' in up));
  }
  assert.ok(keyboardEvents('Tab',8).every(event => event.modifiers === 8));
  assert.throws(() => keyboardEvents('Unknown'),/INTERACTION_ARGUMENTS/);
  assert.throws(() => keyboardEvents('Enter',8),/INTERACTION_ARGUMENTS/);
  assert.deepEqual(failureRecord(new InteractionError('INTERACTION_COMMAND_FAILED','DOM.querySelectorAll')),
    {schema_version:'guardian-interaction-failure/0.1',code:'INTERACTION_COMMAND_FAILED',stage:'DOM.querySelectorAll'});
  for (const error of [new Error('private-sentinel'), new InteractionError('private-sentinel','/private/path')]) {
    assert.deepEqual(failureRecord(error), {schema_version:'guardian-interaction-failure/0.1',code:'INTERACTION_FAILED',stage:'unknown'});
  }
  {
    const {client, child, writes} = fixture();
    const result = client.command('Page.enable', {}, 'owned-session');
    assert.equal(writes[0].sessionId, 'owned-session');
    child.stdio[4].emit('data', Buffer.from('{"id":1,"res'));
    child.stdio[4].emit('data', Buffer.from('ult":{"ok":true}}\0'));
    assert.deepEqual(await result, {ok:true});
    client.fail('done');
  }
  for (const [packet, code] of [['garbage\0', 'INTERACTION_PROTOCOL_INVALID'],
      ['[]\0', 'INTERACTION_PROTOCOL_INVALID'], ['{"id":99}\0', 'INTERACTION_UNEXPECTED_REPLY']]) {
    const {client, child} = fixture();
    const result = client.command('Page.enable');
    child.stdio[4].emit('data', Buffer.from(packet));
    await assert.rejects(result, new RegExp(code));
    assert.equal(client.pending.size, 0);
  }
  {
    const {client, child} = fixture(); const result = client.command('Page.enable');
    child.stdio[4].emit('data', Buffer.alloc(1024 * 1024 + 1));
    await assert.rejects(result, /INTERACTION_PROTOCOL_LIMIT/);
  }
  for (const event of ['end', 'error']) {
    const {client, child} = fixture(); const result = client.command('Page.enable');
    child.stdio[4].emit(event);
    await assert.rejects(result, /INTERACTION_PIPE_/);
  }
  // Deterministic fake browser checks the harness assertions, not Chrome behavior.
  async function runFake(change) {
    let focus = -1; let spacePressed = false; const opened = Array(12).fill(false); const methods = [];
    const client = {events: [], async command(method, p = {}, session) {
      methods.push(method);
      if (method === 'Target.createTarget') return {targetId:'owned'};
      if (method === 'Target.attachToTarget') return {sessionId:'session'};
      if (method === 'Page.navigate') {
        this.events.push({sessionId:session,method:'Page.loadEventFired'});
        this.events.push({sessionId:session,method:'Network.requestWillBeSent',params:{request:{url:p.url},type:'Document'}});
        if (change === 'resource') this.events.push({sessionId:session,method:'Network.requestWillBeSent',params:{request:{url:'https://invalid.test'},type:'Image'}});
      }
      if (method === 'DOM.getDocument') return {root:{nodeId:1,documentURL:'file:///synthetic.html'}};
      if (method === 'DOM.querySelectorAll') return {nodeIds:Array.from({length:12}, (_,i) => i+2)};
      if (method === 'DOM.getAttributes') return {attributes:opened[p.nodeId-2] ? ['open',''] : []};
      if (method === 'DOM.describeNode') return {node:{backendNodeId:p.nodeId}};
      if (method === 'Accessibility.getFullAXTree') return {nodes:[{backendDOMNodeId:focus+2,properties:[{name:'focused',value:{value:true}}]}]};
      if (method === 'CSS.getComputedStyleForNode') return {computedStyle:[{name:'outline-style',value:change==='outline'?'none':'solid'},{name:'outline-width',value:'2px'}]};
      if (method === 'Page.getLayoutMetrics') return {cssLayoutViewport:{clientWidth:390},cssContentSize:{width:change==='overflow'?500:390}};
      if (method === 'Input.dispatchKeyEvent') {
        assert.ok(!('nativeVirtualKeyCode' in p));
        if (p.type === 'rawKeyDown' && p.key === 'Tab') focus += p.modifiers === 8 ? -1 : 1;
        if (p.type === 'keyDown' && p.key === 'Enter') {
          assert.equal(p.text,'\r'); assert.equal(p.unmodifiedText,'\r');
          opened[focus] = !opened[focus];
        }
        if (p.type === 'keyDown' && p.key === ' ') {
          assert.equal(p.text,' '); assert.equal(p.unmodifiedText,' '); spacePressed = true;
        }
        if (p.type === 'keyUp' && p.key === ' ') {
          assert.ok(spacePressed); opened[focus] = !opened[focus]; spacePressed = false;
        }
      }
      return {};
    }};
    const result = await checkViewport(client,'file:///synthetic.html',390,1100);
    assert.equal(result.summary_count,12);
    assert.ok(opened.every(Boolean));
    assert.ok(!methods.some(method => /evaluate|Bypass|setAttribute|focus$/.test(method)));
    return result;
  }
  await runFake();
  for (const [change,error] of [['overflow','HORIZONTAL_OVERFLOW'],['outline','FOCUS_INDICATOR'],['resource','UNEXPECTED_PAGE_RESOURCE']]) {
    await assert.rejects(runFake(change),new RegExp(error));
  }
  console.log('Synthetic interaction protocol checks passed; no browser executed');
}
tests().catch(() => { console.error('Synthetic interaction protocol checks failed'); process.exitCode=1; });
