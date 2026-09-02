#!/usr/bin/env node
// Offline smoke + parity battery for the npm package. Fails loud, exits 1.
//
//  1. manifest freshness invariants vs docs/metrics.json
//  2. FULL Hit@1 corpus replay through the JS router — every task must
//     resolve top-1 to expected_skill, proving the port matches
//     scripts/router_eval.py on the entire gated corpus
//  3. installer: flatten + name-collision qualification into a temp dir
//  4. MCP server: initialize / tools/list / tools/call round-trip on stdio
//  5. CLI: list, search, show
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgRoot = path.join(here, '..');
const repoRoot = path.join(pkgRoot, '..', '..');
const require = createRequire(import.meta.url);
const { Catalog } = require('../lib/catalog.js');
const { install } = require('../lib/install.js');
const bin = path.join(pkgRoot, 'bin', 'aero-agent-skills.js');

let failures = 0;
const check = (name, fn) => {
  try {
    fn();
    console.log(`PASS ${name}`);
  } catch (e) {
    failures += 1;
    console.error(`FAIL ${name}: ${e.message}`);
  }
};

const catalog = new Catalog();
const metrics = JSON.parse(fs.readFileSync(path.join(repoRoot, 'docs', 'metrics.json'), 'utf8'));

check('manifest counts match docs/metrics.json', () => {
  assert.equal(catalog.manifest.counts.leaves, metrics.leaves);
  assert.equal(catalog.manifest.counts.families, metrics.families);
  assert.equal(catalog.manifest.counts.live_packs, metrics.live_packs);
  assert.equal(catalog.manifest.counts.corpus_tasks, metrics.corpus_tasks);
});

check('manifest skill entries match the tree', () => {
  assert.equal(catalog.leaves.length, metrics.leaves, 'leaf count');
  assert.equal(new Set(catalog.leaves.map((s) => s.family)).size, metrics.families, 'family count');
  for (const s of catalog.skills) {
    assert.ok(fs.existsSync(path.join(catalog.root, s.path, 'SKILL.md')), `missing ${s.path}`);
    assert.ok(s.name, `empty name in ${s.path}`);
    assert.ok(s.description, `empty description in ${s.path}`);
  }
  assert.ok(catalog.manifest.standards.length > 0, 'standards register empty');
});

check(`router parity: full Hit@1 corpus (${metrics.corpus_tasks} tasks)`, () => {
  // Load the corpus through yaml.safe_load — the exact reader gate 5 uses —
  // so the parity claim covers the parsing, not just the scoring.
  const corpusJson = execFileSync('python3', ['-c',
    'import json,yaml\n'
    + "d = yaml.safe_load(open('eval/hit1-corpus.yaml'))\n"
    + "print(json.dumps([[t.get('query',''), t.get('expected_skill','')] for t in d['tasks']]))",
  ], { cwd: repoRoot, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  const tasks = JSON.parse(corpusJson).map(([query, expected]) => ({ query, expected }));
  assert.equal(tasks.length, metrics.corpus_tasks, `parsed ${tasks.length} corpus tasks`);
  const misses = [];
  for (const t of tasks) {
    const top = catalog.search(t.query, 1)[0];
    if (top.skill.path !== t.expected) misses.push(`'${t.query.slice(0, 60)}' -> ${top.skill.path} (expected ${t.expected})`);
  }
  assert.equal(misses.length, 0, `Hit@1 misses:\n${misses.slice(0, 5).join('\n')}`);
});

check('installer flattens and qualifies duplicate names', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'aeroskills-install-'));
  try {
    const dupNames = new Map();
    for (const s of catalog.leaves) dupNames.set(s.name, (dupNames.get(s.name) || []).concat([s.path]));
    const dupPaths = [...dupNames.values()].filter((v) => v.length > 1).flat();
    assert.ok(dupPaths.length >= 2, 'expected at least one duplicate frontmatter name in the tree');
    const result = install(catalog, dupPaths.concat(['avionics/do178c/planning']), { dest: tmp });
    const folders = fs.readdirSync(tmp);
    assert.equal(folders.length, dupPaths.length + 1, 'one folder per selected skill');
    assert.equal(new Set(folders).size, folders.length, 'folder names unique');
    assert.ok(result.notes.length > 0, 'collision NOTE printed');
    for (const f of folders) assert.ok(fs.existsSync(path.join(tmp, f, 'SKILL.md')), `no SKILL.md in ${f}`);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

check('installer resolves pack selectors', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'aeroskills-pack-'));
  try {
    const result = install(catalog, ['avionics/do178c'], { dest: tmp });
    const expected = catalog.leaves.filter((s) => s.family === 'avionics' && s.pack === 'do178c').length;
    assert.equal(result.installed.length, expected);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

const mcpRoundTrip = () => new Promise((resolve, reject) => {
  const child = spawn(process.execPath, [bin, 'mcp'], { stdio: ['pipe', 'pipe', 'inherit'] });
  const responses = [];
  let buf = '';
  const timer = setTimeout(() => { child.kill(); reject(new Error('MCP server timed out')); }, 15000);
  child.stdout.on('data', (d) => {
    buf += d;
    let nl;
    while ((nl = buf.indexOf('\n')) !== -1) {
      responses.push(JSON.parse(buf.slice(0, nl)));
      buf = buf.slice(nl + 1);
      if (responses.length === 4) {
        clearTimeout(timer);
        child.stdin.end();
        resolve(responses);
      }
    }
  });
  child.on('error', reject);
  const send = (m) => child.stdin.write(JSON.stringify(m) + '\n');
  send({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'smoke', version: '0' } } });
  send({ jsonrpc: '2.0', method: 'notifications/initialized' });
  send({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
  send({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'search_skills', arguments: { query: 'determine the software level and draft the PSAC for DO-178C certification planning' } } });
  send({ jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'get_skill', arguments: { path: 'avionics/do178c/planning' } } });
});

try {
  const [init, toolsList, search, getSkill] = await mcpRoundTrip();
  check('MCP initialize handshake', () => {
    assert.equal(init.result.serverInfo.name, 'aero-agent-skills');
    assert.ok(init.result.capabilities.tools);
  });
  check('MCP tools/list exposes 5 tools', () => {
    assert.equal(toolsList.result.tools.length, 5);
    for (const t of toolsList.result.tools) assert.ok(t.inputSchema && t.description, t.name);
  });
  check('MCP search_skills routes the PSAC task', () => {
    assert.ok(search.result.content[0].text.startsWith('1. avionics/do178c/planning'), search.result.content[0].text.split('\n')[0]);
  });
  check('MCP get_skill returns the full SKILL.md', () => {
    assert.ok(getSkill.result.content[0].text.includes('# DO-178C Planning'));
  });
} catch (e) {
  failures += 1;
  console.error(`FAIL MCP round-trip: ${e.message}`);
}

check('CLI list / search / show', () => {
  const list = execFileSync(process.execPath, [bin, 'list'], { encoding: 'utf8' });
  assert.ok(list.includes('avionics'), 'list names families');
  assert.ok(list.includes(`${metrics.leaves} skills`), 'list totals from manifest');
  const search = execFileSync(process.execPath, [bin, 'search', 'xfoil', 'polar', 'naca', 'airfoil'], { encoding: 'utf8' });
  assert.ok(search.includes('aerodynamics/airfoil/xfoil-analysis'), 'search finds xfoil skill');
  const show = execFileSync(process.execPath, [bin, 'show', 'avionics/do178c/planning'], { encoding: 'utf8' });
  assert.ok(show.startsWith('---\nname: planning'), 'show prints raw SKILL.md');
});

if (failures) {
  console.error(`\nFAIL package smoke: ${failures} failing checks`);
  process.exit(1);
}
console.log('\nPASS package smoke: manifest + router parity + installer + MCP + CLI green');
