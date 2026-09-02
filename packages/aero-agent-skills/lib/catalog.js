// Catalog loader + deterministic router.
//
// The scoring here is a 1:1 port of scripts/router_eval.py (flat+tags
// token-overlap router, research/briefs/03-router-design.md section 5):
// tags 3.0, name 2.0, description 1.0, body 0.5, +4.0 phrase bonus, top-1
// by (score desc, path asc). Metadata comes from manifest.json, which
// gen_manifest.py derives with the same yaml.safe_load the Python router
// uses; bodies come from the same SKILL.md files. test/smoke.mjs replays
// the full Hit@1 corpus through this port and fails on any divergence.
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const STOP = new Set([
  'a', 'an', 'the', 'for', 'or', 'and', 'of', 'to', 'in', 'on', 'with',
  'is', 'are', 'was', 'be', 'at', 'by', 'from', 'as', 'into', 'onto',
  'under', 'over', 'per', 'via', 'it', 'its', 'this', 'that', 'these',
  'those', 'their', 'our', 'we', 'you', 'your', 'do', 'does', 'did',
  'can', 'could', 'should', 'would', 'will', 'shall', 'must', 'not', 'no',
]);

const TOKEN_RE = /[a-z0-9][a-z0-9-]*/g;

function tokens(text) {
  const out = [];
  for (const m of String(text).toLowerCase().matchAll(TOKEN_RE)) {
    if (!STOP.has(m[0])) out.push(m[0]);
  }
  return out;
}

const PKG_ROOT = path.join(__dirname, '..');

function skillsRoot() {
  // Prefer the repo checkout so a stale prepack payload copy can never
  // shadow the live tree in development; installed packages have no
  // ../../skills and fall through to the bundled copy.
  const repo = path.join(PKG_ROOT, '..', '..', 'skills');
  if (fs.existsSync(repo) && fs.existsSync(path.join(PKG_ROOT, '..', '..', 'standards-map.yaml'))) return repo;
  const bundled = path.join(PKG_ROOT, 'skills');
  if (fs.existsSync(bundled)) return bundled;
  throw new Error('skills tree not found (looked for the repo checkout and a bundled skills/)');
}

function loadManifest() {
  return JSON.parse(fs.readFileSync(path.join(PKG_ROOT, 'manifest.json'), 'utf8'));
}

function version() {
  return JSON.parse(fs.readFileSync(path.join(PKG_ROOT, 'package.json'), 'utf8')).version;
}

function readSkillFile(root, relPath) {
  return fs.readFileSync(path.join(root, relPath, 'SKILL.md'), 'utf8');
}

// Body extraction matching Python's text.split('---', 2)[2].
function bodyOf(text) {
  if (!text.startsWith('---')) return '';
  const i1 = text.indexOf('---');
  const i2 = text.indexOf('---', i1 + 3);
  return i2 === -1 ? '' : text.slice(i2 + 3);
}

class Catalog {
  constructor() {
    this.root = skillsRoot();
    this.manifest = loadManifest();
    this._tok = new Map(); // path -> {tag, name, desc, body} token sets
  }

  get skills() {
    return this.manifest.skills;
  }

  get leaves() {
    return this.manifest.skills.filter((s) => s.path.split('/').length === 3);
  }

  find(p) {
    return this.manifest.skills.find((s) => s.path === p);
  }

  read(p) {
    return readSkillFile(this.root, p);
  }

  _tokensFor(skill) {
    let t = this._tok.get(skill.path);
    if (!t) {
      t = {
        tag: new Set(skill.tags),
        name: new Set(tokens(skill.name)),
        desc: new Set(tokens(skill.description)),
        body: new Set(tokens(bodyOf(this.read(skill.path)))),
        haystack: (skill.name + ' ' + skill.description).toLowerCase(),
      };
      this._tok.set(skill.path, t);
    }
    return t;
  }

  score(skill, query) {
    const q = new Set(tokens(query));
    if (q.size === 0) return 0;
    const t = this._tokensFor(skill);
    let s = 0;
    for (const w of q) {
      if (t.tag.has(w)) s += 3;
      if (t.name.has(w)) s += 2;
      if (t.desc.has(w)) s += 1;
      if (t.body.has(w)) s += 0.5;
    }
    const phrase = tokens(query).join(' ');
    if (phrase && t.haystack.includes(phrase)) s += 4;
    return s;
  }

  search(query, limit = 5) {
    const scored = this.manifest.skills.map((s) => ({ skill: s, score: this.score(s, query) }));
    scored.sort((a, b) => b.score - a.score
      || (a.skill.path < b.skill.path ? -1 : a.skill.path > b.skill.path ? 1 : 0));
    return scored.slice(0, limit);
  }
}

module.exports = { Catalog, tokens, bodyOf, version, PKG_ROOT };
