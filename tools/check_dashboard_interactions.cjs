'use strict';
// CI-owned Chrome only. No page script evaluation, CSP bypass or debug listener.
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const {pathToFileURL} = require('node:url');

const FAILURE_CODES = new Set(["INTERACTION_ALL_OPEN_FAILED", "INTERACTION_ARGUMENTS", "INTERACTION_BROWSER_EXITED", "INTERACTION_BROWSER_REAP_TIMEOUT", "INTERACTION_BROWSER_START_FAILED", "INTERACTION_COMMAND_FAILED", "INTERACTION_COMMAND_TIMEOUT", "INTERACTION_DETAILS_COUNT", "INTERACTION_DOCUMENT_MISMATCH", "INTERACTION_ENTER_DID_NOT_COLLAPSE", "INTERACTION_ENTER_DID_NOT_EXPAND", "INTERACTION_EVENT_LIMIT", "INTERACTION_FAILED", "INTERACTION_FOCUS_INDICATOR_MISSING", "INTERACTION_HORIZONTAL_OVERFLOW", "INTERACTION_KEYBOARD_FOCUS_ORDER", "INTERACTION_LOAD_TIMEOUT", "INTERACTION_NAVIGATION_FAILED", "INTERACTION_NOT_INITIALLY_COLLAPSED", "INTERACTION_PIPE_CLOSED", "INTERACTION_PIPE_ERROR", "INTERACTION_PROTOCOL_INVALID", "INTERACTION_PROTOCOL_LIMIT", "INTERACTION_REQUIRES_CI", "INTERACTION_SPACE_DID_NOT_COLLAPSE", "INTERACTION_SPACE_DID_NOT_EXPAND", "INTERACTION_TOTAL_TIMEOUT", "INTERACTION_UNEXPECTED_PAGE_RESOURCE", "INTERACTION_UNEXPECTED_REPLY", "INTERACTION_VERSION_INVALID"]);
const FAILURE_STAGES = new Set(["Accessibility.enable", "Accessibility.getFullAXTree", "Browser.getVersion", "CSS.enable", "CSS.getComputedStyleForNode", "DOM.describeNode", "DOM.enable", "DOM.getAttributes", "DOM.getDocument", "DOM.querySelectorAll", "Emulation.setDeviceMetricsOverride", "Input.dispatchKeyEvent", "Network.enable", "Page.bringToFront", "Page.enable", "Page.getLayoutMetrics", "Page.navigate", "Target.attachToTarget", "Target.closeTarget", "Target.createTarget", "cleanup", "save_result", "startup", "unknown"]);
let currentStage = "startup";
let diagnosticPath = null;
class InteractionError extends Error {
  constructor(code, stage = currentStage) { super(code); this.stage = stage; }
}
function failureRecord(error) {
  return {schema_version: "guardian-interaction-failure/0.1",
    code: error instanceof InteractionError && FAILURE_CODES.has(error.message) ? error.message : "INTERACTION_FAILED",
    stage: error instanceof InteractionError && FAILURE_STAGES.has(error.stage) ? error.stage : "unknown"};
}
function requireCondition(value, code) { if (!value) throw new InteractionError(code); }
class PipeClient {
  constructor(child) {
    this.child = child; this.next = 1; this.pending = new Map();
    this.buffer = Buffer.alloc(0); this.bytes = 0; this.events = [];
    this.failed = null;
    child.stdio[4].on('data', chunk => this.receive(chunk));
    child.stdio[4].on('error', () => this.fail('INTERACTION_PIPE_ERROR'));
    child.stdio[4].on('end', () => this.fail('INTERACTION_PIPE_CLOSED'));
    child.stdio[3].on('error', () => this.fail('INTERACTION_PIPE_ERROR'));
    child.on('error', () => this.fail('INTERACTION_BROWSER_START_FAILED'));
    child.on('exit', () => this.fail('INTERACTION_BROWSER_EXITED'));
  }
  fail(code) {
    if (!this.failed) this.failed = new InteractionError(code);
    for (const entry of this.pending.values()) { clearTimeout(entry.timer); entry.reject(this.failed); }
    this.pending.clear();
  }
  receive(chunk) {
    this.bytes += chunk.length;
    if (this.bytes > 16 * 1024 * 1024 || this.buffer.length + chunk.length > 1024 * 1024) {
      this.fail('INTERACTION_PROTOCOL_LIMIT'); return;
    }
    this.buffer = Buffer.concat([this.buffer, chunk]);
    let end;
    while ((end = this.buffer.indexOf(0)) >= 0) {
      let message;
      try { message = JSON.parse(this.buffer.subarray(0, end).toString('utf8')); }
      catch { this.fail('INTERACTION_PROTOCOL_INVALID'); return; }
      this.buffer = this.buffer.subarray(end + 1);
      if (!message || typeof message !== 'object' || Array.isArray(message)) {
        this.fail('INTERACTION_PROTOCOL_INVALID'); return;
      }
      if (message.id !== undefined) {
        const entry = this.pending.get(message.id);
        if (!entry) { this.fail('INTERACTION_UNEXPECTED_REPLY'); return; }
        this.pending.delete(message.id); clearTimeout(entry.timer);
        if (message.error) entry.reject(new InteractionError('INTERACTION_COMMAND_FAILED'));
        else entry.resolve(message.result || {});
      } else {
        if (this.events.length >= 4096) { this.fail('INTERACTION_EVENT_LIMIT'); return; }
        this.events.push(message);
      }
    }
  }
  command(method, params = {}, sessionId) {
    currentStage = FAILURE_STAGES.has(method) ? method : "unknown";
    if (this.failed) return Promise.reject(this.failed);
    const id = this.next++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => this.fail('INTERACTION_COMMAND_TIMEOUT'), 5000);
      this.pending.set(id, {resolve, reject, timer});
      this.child.stdio[3].write(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}) + '\0');
    });
  }
}
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function eventually(check, code) {
  for (let i = 0; i < 40; i++) { if (await check()) return; await delay(25); }
  throw new InteractionError(code);
}
async function checkViewport(client, pageURL, width, height) {
  const {targetId} = await client.command('Target.createTarget', {url: 'about:blank'});
  const {sessionId} = await client.command('Target.attachToTarget', {targetId, flatten: true});
  const send = (method, params) => client.command(method, params, sessionId);
  await send('Page.enable'); await send('DOM.enable'); await send('CSS.enable');
  await send('Accessibility.enable'); await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 1, mobile: false});
  await send('Page.bringToFront');
  const firstEvent = client.events.length;
  const navigation = await send('Page.navigate', {url: pageURL});
  requireCondition(!navigation.errorText, 'INTERACTION_NAVIGATION_FAILED');
  await eventually(async () => client.events.slice(firstEvent).some(event =>
    event.sessionId === sessionId && event.method === 'Page.loadEventFired'), 'INTERACTION_LOAD_TIMEOUT');
  const {root} = await send('DOM.getDocument', {depth: 1});
  requireCondition(root.documentURL === pageURL, 'INTERACTION_DOCUMENT_MISMATCH');
  const summaries = (await send('DOM.querySelectorAll', {nodeId: root.nodeId, selector: 'details > summary'})).nodeIds;
  const details = (await send('DOM.querySelectorAll', {nodeId: root.nodeId, selector: 'details'})).nodeIds;
  requireCondition(summaries.length === 12 && details.length === 12, 'INTERACTION_DETAILS_COUNT');
  const isOpen = async nodeId => (await send('DOM.getAttributes', {nodeId})).attributes
    .filter((_, i) => i % 2 === 0).includes('open');
  const noOverflow = async () => {
    const metrics = await send('Page.getLayoutMetrics');
    requireCondition(metrics.cssLayoutViewport.clientWidth === width &&
      metrics.cssContentSize.width <= width + 1, 'INTERACTION_HORIZONTAL_OVERFLOW');
  };
  const key = async (name, code, virtualKey) => {
    for (const type of ['keyDown', 'keyUp']) await send('Input.dispatchKeyEvent', {
      type, key: name, code, windowsVirtualKeyCode: virtualKey, nativeVirtualKeyCode: virtualKey});
  };
  await noOverflow();
  for (let i = 0; i < summaries.length; i++) {
    requireCondition(!(await isOpen(details[i])), 'INTERACTION_NOT_INITIALLY_COLLAPSED');
    await key('Tab', 'Tab', 9);
    const {node} = await send('DOM.describeNode', {nodeId: summaries[i]});
    const focused = async () => (await send('Accessibility.getFullAXTree')).nodes.some(ax =>
      ax.backendDOMNodeId === node.backendNodeId && ax.properties?.some(p => p.name === 'focused' && p.value.value === true));
    await eventually(focused, 'INTERACTION_KEYBOARD_FOCUS_ORDER');
    const styles = (await send('CSS.getComputedStyleForNode', {nodeId: summaries[i]})).computedStyle;
    const css = Object.fromEntries(styles.map(item => [item.name, item.value]));
    requireCondition(css['outline-style'] !== 'none' && parseFloat(css['outline-width']) > 0,
      'INTERACTION_FOCUS_INDICATOR_MISSING');
    await key('Enter', 'Enter', 13);
    await eventually(() => isOpen(details[i]), 'INTERACTION_ENTER_DID_NOT_EXPAND');
    await noOverflow();
    await key('Enter', 'Enter', 13);
    await eventually(async () => !(await isOpen(details[i])), 'INTERACTION_ENTER_DID_NOT_COLLAPSE');
    await key(' ', 'Space', 32);
    await eventually(() => isOpen(details[i]), 'INTERACTION_SPACE_DID_NOT_EXPAND');
    await key(' ', 'Space', 32);
    await eventually(async () => !(await isOpen(details[i])), 'INTERACTION_SPACE_DID_NOT_COLLAPSE');
  }
  // Reopen every disclosure through keyboard input in a fresh traversal, so
  // overflowing content cannot hide behind our one-at-a-time checks.
  for (let i = summaries.length - 1; i >= 0; i--) {
    await key('Enter', 'Enter', 13);
    await eventually(() => isOpen(details[i]), 'INTERACTION_ALL_OPEN_FAILED');
    if (i > 0) for (const type of ['keyDown', 'keyUp']) await send('Input.dispatchKeyEvent', {
      type, key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9, modifiers: 8});
  }
  await noOverflow();
  const requests = client.events.slice(firstEvent).filter(event =>
    event.sessionId === sessionId && event.method === 'Network.requestWillBeSent');
  requireCondition(requests.length === 1 && requests[0].params.request.url === pageURL &&
    requests[0].params.type === 'Document', 'INTERACTION_UNEXPECTED_PAGE_RESOURCE');
  await client.command('Target.closeTarget', {targetId});
  return {width, height, summary_count: summaries.length, keyboard_focus_order: true,
    visible_focus_indicator: true, enter_toggle: true, space_toggle: true,
    all_details_expanded: true, horizontal_overflow_absent: true,
    page_document_requests: 1, page_subresource_requests: 0};
}
async function main() {
  requireCondition(process.env.GITHUB_ACTIONS === 'true' && process.env.RUNNER_OS === 'Linux' &&
    process.platform === 'linux' && process.getuid() !== 0, 'INTERACTION_REQUIRES_CI');
  const [browser, page, profile, output, diagnostic] = process.argv.slice(2);
  requireCondition(browser && page && profile && output && diagnostic && process.argv.length === 7, 'INTERACTION_ARGUMENTS');
  diagnosticPath = diagnostic;
  const child = spawn(browser, ['--headless', '--no-first-run', '--no-default-browser-check',
    '--disable-background-networking', '--disable-component-update', '--disable-default-apps',
    '--disable-sync', '--metrics-recording-only', '--force-device-scale-factor=1', '--hide-scrollbars',
    '--remote-debugging-pipe', '--user-data-dir=' + profile, 'about:blank'],
    {stdio: ['ignore', 'ignore', 'ignore', 'pipe', 'pipe']});
  const client = new PipeClient(child);
  const whole = setTimeout(() => client.fail('INTERACTION_TOTAL_TIMEOUT'), 60000);
  try {
    const {product} = await client.command('Browser.getVersion');
    requireCondition(typeof product === 'string' && product.length <= 200, 'INTERACTION_VERSION_INVALID');
    const results = [];
    for (const [width, height] of [[1440, 1000], [390, 1100]]) {
      results.push(await checkViewport(client, pathToFileURL(page).href, width, height));
    }
    currentStage = 'save_result';
    fs.writeFileSync(output, JSON.stringify({schema_version: 'guardian-dashboard-interaction/0.1',
      record_kind: 'synthetic_example', browser_version: product,
      evidence_kind: 'ci_real_chrome_keyboard_and_layout',
      network_isolation_verified: false, viewports: results}) + '\n', {flag: 'wx', mode: 0o600});
  } catch (error) {
    throw error instanceof InteractionError ? error : new InteractionError('INTERACTION_FAILED');
  } finally {
    currentStage = 'cleanup';
    clearTimeout(whole); client.fail('INTERACTION_FINISHED');
    child.kill('SIGKILL');
    if (child.exitCode === null && child.signalCode === null) await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new InteractionError('INTERACTION_BROWSER_REAP_TIMEOUT')), 5000);
      child.once('exit', () => {clearTimeout(timer); resolve();});
    });
  }
}
if (require.main === module) main().catch(error => {
  const record = failureRecord(error);
  // Private fixed-enum diagnostic only; never copy protocol responses or paths.
  if (diagnosticPath) {
    try { fs.writeFileSync(diagnosticPath, JSON.stringify(record), {flag: 'wx', mode: 0o600}); }
    catch { /* Parent reports a missing diagnostic as failure, never acceptance. */ }
  }
  console.error(record.code); process.exitCode = 2;
});
module.exports = {PipeClient, InteractionError, checkViewport, failureRecord, FAILURE_CODES, FAILURE_STAGES};
