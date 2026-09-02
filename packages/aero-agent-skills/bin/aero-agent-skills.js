#!/usr/bin/env node
// aero-agent-skills CLI: list / search / show / install / where / mcp.
// Everything answers from the bundled tree + generated manifest — offline,
// deterministic, no telemetry, no network.
'use strict';

const { Catalog, version, PKG_ROOT } = require('../lib/catalog');
const { install, HARNESS_ROOTS } = require('../lib/install');

const HELP = `aero-agent-skills ${version()} — the aerospace knowledge layer for AI agents (Ashforde OU)

Usage:
  aero-skills list [family[/pack]]          browse families, packs, skills
  aero-skills search <task words...>        rank skills with the deterministic router
  aero-skills show <family/pack/skill>      print one SKILL.md
  aero-skills install [selector...]         copy skills into a harness skills root
      --harness ${Object.keys(HARNESS_ROOTS).join('|')}
      --dest <dir>                          explicit destination (overrides --harness)
      --link                                symlink instead of copy
      selector: all | family | family/pack | family/pack/skill (default: all)
  aero-skills mcp                           run the MCP server on stdio
  aero-skills where                         print the bundled skills root
  aero-skills version

MCP host config (JetBrains AI Assistant/Junie, Claude Desktop, VS Code, Cursor, Windsurf):
  {"mcpServers":{"aero-agent-skills":{"command":"npx","args":["-y","aero-agent-skills","mcp"]}}}
`;

function parseFlags(argv) {
  const flags = {};
  const rest = [];
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--harness') flags.harness = argv[++i];
    else if (argv[i] === '--dest') flags.dest = argv[++i];
    else if (argv[i] === '--link') flags.link = true;
    else rest.push(argv[i]);
  }
  return { flags, rest };
}

function cmdList(catalog, sel) {
  if (!sel) {
    const fams = new Map();
    for (const s of catalog.leaves) {
      const f = fams.get(s.family) || { packs: new Set(), leaves: 0 };
      f.packs.add(s.pack);
      f.leaves += 1;
      fams.set(s.family, f);
    }
    for (const [name, f] of [...fams.entries()].sort()) {
      console.log(`${name.padEnd(28)} ${String(f.packs.size).padStart(3)} packs ${String(f.leaves).padStart(4)} skills`);
    }
    console.log(`\n${catalog.manifest.counts.leaves} skills, ${catalog.manifest.counts.live_packs} packs, ${catalog.manifest.counts.families} families. \`list <family>\` to drill in.`);
    return;
  }
  const norm = sel.replace(/\/+$/, '');
  const parts = norm.split('/');
  const hits = catalog.leaves.filter((s) => s.family === parts[0] && (!parts[1] || s.pack === parts[1]));
  if (hits.length === 0) {
    console.error(`nothing under '${sel}'. Run \`aero-skills list\` for families.`);
    process.exitCode = 1;
    return;
  }
  for (const s of hits) console.log(s.path);
}

function main() {
  const [cmd, ...args] = process.argv.slice(2);
  if (!cmd || cmd === 'help' || cmd === '--help' || cmd === '-h') {
    console.log(HELP);
    return;
  }
  if (cmd === 'version' || cmd === '--version' || cmd === '-v') {
    console.log(version());
    return;
  }
  if (cmd === 'mcp') {
    require('../lib/mcp').serve();
    return;
  }

  const catalog = new Catalog();
  if (cmd === 'list' || cmd === 'packs') {
    cmdList(catalog, args[0]);
  } else if (cmd === 'search') {
    const query = args.join(' ').trim();
    if (!query) {
      console.error('usage: aero-skills search <task words...>');
      process.exitCode = 1;
      return;
    }
    for (const [i, h] of catalog.search(query, 5).entries()) {
      const desc = h.skill.description.length > 110 ? h.skill.description.slice(0, 110) + '...' : h.skill.description;
      console.log(`${i + 1}. ${h.skill.path}  (score ${h.score})\n   ${desc}`);
    }
  } else if (cmd === 'show') {
    const skill = catalog.find((args[0] || '').replace(/\/+$/, ''));
    if (!skill) {
      console.error(`no skill at '${args[0] || ''}'. Try \`aero-skills search\`.`);
      process.exitCode = 1;
      return;
    }
    process.stdout.write(catalog.read(skill.path));
  } else if (cmd === 'install') {
    const { flags, rest } = parseFlags(args);
    try {
      const result = install(catalog, rest, flags);
      for (const n of result.notes) console.log(n);
      for (const item of result.installed) console.log(`${result.linked ? 'linked' : 'installed'} ${item.path} -> ${item.folder}/`);
      console.log(`\n${result.installed.length} skills ${result.linked ? 'linked' : 'installed'} into ${result.dest}`);
    } catch (e) {
      console.error(e.message);
      process.exitCode = 1;
    }
  } else if (cmd === 'where') {
    console.log(catalog.root);
  } else {
    console.error(`unknown command '${cmd}'\n`);
    console.log(HELP);
    process.exitCode = 1;
  }
}

main();
