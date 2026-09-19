#!/usr/bin/env node
// Offline smoke + parity battery for the npm package. Fails loud, exits 1.
//
//  1. manifest freshness invariants vs docs/metrics.json
//  2. FULL Hit@1 replay through the JS router — every case in eval/ must
//     resolve top-1 to expected_skill, proving the port matches
//     scripts/router_eval.py on the entire gated corpus
//  3. installer: flatten + name-collision qualification, exercised against a
//     SYNTHESISED catalogue in a temp dir (never against corpus defects)
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

check(`router parity: every gated case (${metrics.router_cases})`, () => {
  // Load every case gate 5 executes — the assembled corpus AND the per-leaf
  // fragments — through yaml.safe_load, the exact reader gate 5 uses, so the
  // parity claim covers the parsing and not just the scoring. Reading only
  // hit1-corpus.yaml proved the port on 1,754 of 6,308 cases while this test
  // called itself full.
  const corpusJson = execFileSync('python3', ['-c',
    'import json,glob,yaml\n'
    + "out = []\n"
    + "for f in sorted(glob.glob('eval/hit1-*.yaml')):\n"
    + "    d = yaml.safe_load(open(f)) or {}\n"
    + "    for t in (d.get('tasks') or []):\n"
    + "        out.append([t.get('query',''), t.get('expected_skill','')])\n"
    + "print(json.dumps(out))",
  ], { cwd: repoRoot, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
  const tasks = JSON.parse(corpusJson).map(([query, expected]) => ({ query, expected }));
  assert.equal(tasks.length, metrics.router_cases, `parsed ${tasks.length} router cases`);
  const misses = [];
  for (const t of tasks) {
    const top = catalog.search(t.query, 1)[0];
    if (top.skill.path !== t.expected) misses.push(`'${t.query.slice(0, 60)}' -> ${top.skill.path} (expected ${t.expected})`);
  }
  assert.equal(misses.length, 0, `Hit@1 misses:\n${misses.slice(0, 5).join('\n')}`);
});

// ---------------------------------------------------------------------------
// Installer: flatten + name-collision qualification.
//
// This block used to assert `dupPaths.length >= 2` over the real corpus, i.e.
// "expected at least one duplicate frontmatter name in the tree". That is an
// assertion that a DEFECT still exists: it passed only while two leaves shared
// a frontmatter name, and inverted into a false red the moment slug/name
// uniqueness was made provable. It also never reached the escalation rungs of
// the qualifier ladder, because which rungs fired depended on whichever
// collisions the corpus happened to contain that week.
//
// The installer's ladder (name -> family-name -> family-pack-name -> full
// path, per lib/install.js folderNames) is now exercised against SYNTHESISED
// catalogues built in a temp dir, one case per rung. The test depends on the
// installer, not on the corpus being broken. Corpus name uniqueness is
// asserted separately below, in the direction that is actually desirable.
// ---------------------------------------------------------------------------

// A catalogue duck-typed to what lib/install.js consumes: .root, .leaves,
// .skills, and .search (only reached on a selector miss). Each spec writes a
// real SKILL.md under the temp root so the copy step is exercised for real.
function synthCatalog(root, specs) {
  const leaves = specs.map(({ path: p, name }) => {
    const [family, pack, slug] = p.split('/');
    fs.mkdirSync(path.join(root, p), { recursive: true });
    fs.writeFileSync(
      path.join(root, p, 'SKILL.md'),
      `---\nname: ${name}\ndescription: synthetic leaf for ${p}\n---\n\n# leaf ${p}\n`,
    );
    return { path: p, name, family, pack, slug, description: `synthetic leaf for ${p}`, tags: [] };
  });
  return {
    root,
    leaves,
    skills: leaves,
    find: (p) => leaves.find((s) => s.path === p),
    search: () => [],
  };
}

// Build a synthesised catalogue + empty destination, run fn, always clean up.
function withSynthCatalog(specs, fn) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'aeroskills-synth-'));
  try {
    const src = path.join(tmp, 'skills');
    fs.mkdirSync(src, { recursive: true });
    return fn(synthCatalog(src, specs), path.join(tmp, 'dest'));
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// Every installed folder must hold the body of the leaf it was named for. A
// qualifier that produced unique names but copied the wrong source directory
// would satisfy a folder-count check and still ship the wrong skill.
function assertBodiesLandedCorrectly(dest, result) {
  for (const { path: p, folder } of result.installed) {
    const body = fs.readFileSync(path.join(dest, folder, 'SKILL.md'), 'utf8');
    assert.ok(body.includes(`# leaf ${p}`), `folder ${folder} holds the body of ${p}`);
  }
}

check('installer: unique names install flat and unqualified', () => {
  withSynthCatalog([
    { path: 'alpha/pack-one/first', name: 'first-widget' },
    { path: 'beta/pack-two/second', name: 'second-widget' },
  ], (cat, dest) => {
    const result = install(cat, ['all'], { dest });
    assert.deepEqual(fs.readdirSync(dest).sort(), ['first-widget', 'second-widget']);
    assert.deepEqual(result.notes, [], `no collision NOTE expected, got ${JSON.stringify(result.notes)}`);
    assertBodiesLandedCorrectly(dest, result);
  });
});

check('installer: synthesised duplicate qualifies to family-name (rung 1)', () => {
  withSynthCatalog([
    { path: 'alpha/pack-one/widget-a', name: 'twin-widget' },
    { path: 'beta/pack-one/widget-b', name: 'twin-widget' },
    { path: 'gamma/pack-one/widget-c', name: 'twin-widget' },
    { path: 'alpha/pack-one/solo', name: 'solo-widget' },
  ], (cat, dest) => {
    const result = install(cat, ['all'], { dest });
    const folders = fs.readdirSync(dest).sort();
    assert.equal(new Set(folders).size, folders.length, `folder names unique: ${folders.join(', ')}`);
    assert.equal(folders.length, 4, `one folder per selected skill: ${folders.join(', ')}`);
    assert.deepEqual(folders, [
      'alpha-twin-widget', 'beta-twin-widget', 'gamma-twin-widget', 'solo-widget',
    ], `family-qualified names, uncollided name left bare: ${folders.join(', ')}`);
    assert.ok(
      result.notes.some((n) => n.includes("'twin-widget'") && n.startsWith('NOTE:')),
      `collision NOTE names the clashing skill: ${JSON.stringify(result.notes)}`,
    );
    assertBodiesLandedCorrectly(dest, result);
  });
});

check('installer: same family escalates to family-pack-name (rung 2)', () => {
  withSynthCatalog([
    { path: 'alpha/pack-one/widget-a', name: 'twin-widget' },
    { path: 'alpha/pack-two/widget-b', name: 'twin-widget' },
  ], (cat, dest) => {
    const result = install(cat, ['all'], { dest });
    const folders = fs.readdirSync(dest).sort();
    assert.deepEqual(folders, ['alpha-pack-one-twin-widget', 'alpha-pack-two-twin-widget'],
      `family-name still collides, must escalate: ${folders.join(', ')}`);
    assertBodiesLandedCorrectly(dest, result);
  });
});

check('installer: same family+pack escalates to the full path (rung 3)', () => {
  withSynthCatalog([
    { path: 'alpha/pack-one/widget-a', name: 'twin-widget' },
    { path: 'alpha/pack-one/widget-b', name: 'twin-widget' },
  ], (cat, dest) => {
    const result = install(cat, ['all'], { dest });
    const folders = fs.readdirSync(dest).sort();
    assert.deepEqual(folders, ['alpha-pack-one-widget-a', 'alpha-pack-one-widget-b'],
      `both earlier rungs collide, must fall back to the path: ${folders.join(', ')}`);
    assert.equal(new Set(folders).size, folders.length, 'folder names unique');
    assertBodiesLandedCorrectly(dest, result);
  });
});

// The invariant the old assertion had backwards: the shipped corpus should
// need NO qualification at all. Red here means two leaves share a frontmatter
// name and every harness that flattens the tree would clobber one of them.
check('corpus: leaf frontmatter names are unique (installer needs no qualification)', () => {
  const byName = new Map();
  for (const s of catalog.leaves) byName.set(s.name, (byName.get(s.name) || []).concat([s.path]));
  const clashes = [...byName.entries()].filter(([, v]) => v.length > 1);
  assert.equal(clashes.length, 0,
    `duplicate frontmatter names: ${clashes.map(([n, v]) => `${n} -> ${v.join(' + ')}`).join('; ')}`);
  assert.equal(byName.size, catalog.leaves.length, 'one distinct name per leaf');
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
      if (responses.length === 7) {
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
  send({ jsonrpc: '2.0', id: 5, method: 'resources/list' });
  send({ jsonrpc: '2.0', id: 6, method: 'resources/read', params: { uri: 'skill://avionics/do178c/planning' } });
  send({ jsonrpc: '2.0', id: 7, method: 'resources/read', params: { uri: 'skill://aerodynamics/cfd/cfd-validation/references/vv-guidance.md' } });
});

try {
  const [init, toolsList, search, getSkill, resList, resRead, refRead] = await mcpRoundTrip();
  check('MCP initialize handshake', () => {
    assert.equal(init.result.serverInfo.name, 'aero-agent-skills');
    assert.ok(init.result.capabilities.tools);
    assert.ok(init.result.capabilities.resources, 'advertises resources capability');
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
  check('MCP resources/list enumerates skill:// URIs', () => {
    assert.ok(resList.result.resources.length > 500, `expected >500 resources, got ${resList.result.resources.length}`);
    assert.ok(resList.result.resources.some((r) => r.uri === 'skill://avionics/do178c/planning'), 'leaf listed');
  });
  check('MCP resources/read serves a skill body', () => {
    assert.equal(resRead.result.contents[0].uri, 'skill://avionics/do178c/planning');
    assert.ok(resRead.result.contents[0].text.includes('# DO-178C Planning'), 'body is the SKILL.md');
  });
  check('MCP resources/read serves a reference file', () => {
    assert.ok(refRead.result.contents[0].text.length > 200, 'reference body returned');
    assert.ok(/V&V Guidance/i.test(refRead.result.contents[0].text), 'reference content is the file');
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
