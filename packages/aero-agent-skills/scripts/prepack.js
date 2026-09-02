// Runs on `npm pack` / `npm publish` from the repo checkout: copies the
// payload (skills tree, standards map, LICENSE, NOTICE) from the repo root
// into the package so the tarball is self-contained. The copies are
// gitignored — the repo tree stays the single source of truth.
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const pkg = path.join(__dirname, '..');
const repo = path.join(pkg, '..', '..');

if (!fs.existsSync(path.join(repo, 'skills')) || !fs.existsSync(path.join(repo, 'standards-map.yaml'))) {
  console.error('prepack: must run from the aero-agent-skills repo checkout (skills/ not found two levels up)');
  process.exit(1);
}

fs.rmSync(path.join(pkg, 'skills'), { recursive: true, force: true });
fs.cpSync(path.join(repo, 'skills'), path.join(pkg, 'skills'), { recursive: true });
for (const f of ['standards-map.yaml', 'LICENSE', 'NOTICE']) {
  fs.copyFileSync(path.join(repo, f), path.join(pkg, f));
}
console.log('prepack: bundled skills/, standards-map.yaml, LICENSE, NOTICE from repo root');
