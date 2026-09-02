// Installer: copies (or symlinks) leaf skill folders into a harness skills
// root, flattened per docs/harness-integration.md — every harness consumes
// flat <skill-name>/SKILL.md folders, so the nested authoring path
// family/pack/skill becomes a folder named after the frontmatter name.
// When a selection contains duplicate frontmatter names the folder name is
// progressively qualified (family-name, then family-pack-name, then the
// full path) and a NOTE is printed, because two folders cannot share a name.
'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HARNESS_ROOTS = {
  claude: () => path.join(os.homedir(), '.claude', 'skills'),
  'claude-project': () => path.join(process.cwd(), '.claude', 'skills'),
  codex: () => path.join(process.cwd(), '.agents', 'skills'),
  opencode: () => path.join(process.cwd(), '.agents', 'skills'),
  agents: () => path.join(process.cwd(), '.agents', 'skills'),
  gemini: () => path.join(os.homedir(), '.gemini', 'skills'),
  cursor: () => path.join(process.cwd(), '.cursor', 'skills'),
};

function resolveSelection(catalog, selectors) {
  const leaves = catalog.leaves;
  if (selectors.length === 0 || selectors.includes('all')) return leaves.slice();
  const picked = new Map();
  for (const sel of selectors) {
    const norm = sel.replace(/\/+$/, '');
    const hits = leaves.filter((s) => s.path === norm
      || s.path.startsWith(norm + '/'));
    if (hits.length === 0) {
      const near = catalog.search(norm.replace(/\//g, ' '), 3)
        .map((r) => r.skill.path).join(', ');
      throw new Error(`no skill matches '${sel}' (family, family/pack, or family/pack/skill). Closest: ${near}`);
    }
    for (const h of hits) picked.set(h.path, h);
  }
  return [...picked.values()].sort((a, b) => (a.path < b.path ? -1 : 1));
}

function folderNames(selection) {
  const names = new Map(selection.map((s) => [s.path, s.name || path.basename(s.path)]));
  const qualifiers = [
    (s) => `${s.family}-${s.name}`,
    (s) => `${s.family}-${s.pack}-${s.name}`,
    (s) => s.path.replace(/\//g, '-'),
  ];
  let notes = [];
  for (const qualify of qualifiers) {
    const byName = new Map();
    for (const s of selection) {
      const n = names.get(s.path);
      byName.set(n, (byName.get(n) || []).concat([s]));
    }
    const dups = [...byName.entries()].filter(([, v]) => v.length > 1);
    if (dups.length === 0) break;
    for (const [n, group] of dups) {
      notes.push(`NOTE: ${group.length} selected skills share the name '${n}'; using qualified folder names.`);
      for (const s of group) names.set(s.path, qualify(s));
    }
    notes = [...new Set(notes)];
  }
  return { names, notes };
}

function install(catalog, selectors, opts) {
  const dest = opts.dest
    ? path.resolve(opts.dest)
    : (HARNESS_ROOTS[opts.harness || 'agents'] || HARNESS_ROOTS.agents)();
  const selection = resolveSelection(catalog, selectors);
  const { names, notes } = folderNames(selection);
  fs.mkdirSync(dest, { recursive: true });
  const installed = [];
  for (const s of selection) {
    const src = path.join(catalog.root, s.path);
    const dst = path.join(dest, names.get(s.path));
    if (opts.link) {
      fs.rmSync(dst, { recursive: true, force: true });
      fs.symlinkSync(src, dst, 'dir');
    } else {
      fs.cpSync(src, dst, { recursive: true, force: true });
    }
    installed.push({ path: s.path, folder: names.get(s.path) });
  }
  return { dest, installed, notes, linked: !!opts.link };
}

module.exports = { install, HARNESS_ROOTS };
