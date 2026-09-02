// MCP server over stdio: newline-delimited JSON-RPC 2.0, zero dependencies.
// Implements the subset every MCP host needs (initialize, ping, tools/list,
// tools/call); anything else gets -32601 per spec, and requests without an
// id are treated as notifications and never answered. Deterministic and
// offline: every answer comes from the bundled tree — no network, ever.
'use strict';

const { Catalog, version } = require('./catalog');

const TOOLS = [
  {
    name: 'search_skills',
    description: 'Search the Aero Agent Skills library with its deterministic router (the same '
      + 'token-overlap scoring the repository proves with a full Hit@1 corpus gate). Use when an '
      + 'aerospace engineering task needs a standards-mapped workflow: certification planning, '
      + 'sizing, aero/structures/propulsion analysis, GNC, flight test, space systems, or quality. '
      + 'Returns ranked skill paths with descriptions; load the winner with get_skill.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'The engineering task, in plain words.' },
        limit: { type: 'integer', minimum: 1, maximum: 25, description: 'Max results (default 5).' },
      },
      required: ['query'],
      additionalProperties: false,
    },
  },
  {
    name: 'get_skill',
    description: 'Fetch one complete SKILL.md by path (family/pack/skill, e.g. '
      + 'avionics/do178c/planning). Use after search_skills to load the full workflow: the '
      + 'step-by-step method, its verification gates, and the stop points where a human must sign.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Skill path as returned by search_skills or list_skills.' },
      },
      required: ['path'],
      additionalProperties: false,
    },
  },
  {
    name: 'list_families',
    description: 'List the discipline families with their pack and skill counts. Use to get an '
      + 'overview of what the library covers before searching or browsing.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'list_skills',
    description: 'List skills, optionally filtered to one family or one family/pack. Use to browse '
      + 'a discipline; each entry gives the path to pass to get_skill.',
    inputSchema: {
      type: 'object',
      properties: {
        family: { type: 'string', description: 'Family, e.g. avionics.' },
        pack: { type: 'string', description: 'Pack within the family, e.g. do178c.' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'get_standards',
    description: 'Look up the machine-readable aerospace standards register: publisher, status '
      + '(public-domain, proprietary, open-spec) and whether verbatim text is gated. Use when a '
      + 'task cites a standard (DO-178C, ARP4754A, AS9100, CS-25, ECSS, ...) and you need its '
      + 'scope or handling rules. Omit id to list all.',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'string', description: 'Standard id, e.g. do-178c (case-insensitive).' },
      },
      additionalProperties: false,
    },
  },
];

function text(t) {
  return { content: [{ type: 'text', text: t }], isError: false };
}

function toolError(t) {
  return { content: [{ type: 'text', text: t }], isError: true };
}

function familiesSummary(catalog) {
  const fams = new Map();
  for (const s of catalog.skills) {
    const f = fams.get(s.family) || { packs: new Set(), leaves: 0 };
    if (s.pack) f.packs.add(s.pack);
    if (s.path.split('/').length === 3) f.leaves += 1;
    fams.set(s.family, f);
  }
  return [...fams.entries()].sort()
    .map(([name, f]) => `${name}: ${f.packs.size} packs, ${f.leaves} skills`)
    .join('\n');
}

function callTool(catalog, name, args) {
  args = args || {};
  switch (name) {
    case 'search_skills': {
      if (!args.query || !String(args.query).trim()) return toolError('query is required');
      const limit = Math.min(Math.max(args.limit || 5, 1), 25);
      const hits = catalog.search(String(args.query), limit);
      return text(hits.map((h, i) => `${i + 1}. ${h.skill.path} (score ${h.score})\n   ${h.skill.description}`).join('\n\n'));
    }
    case 'get_skill': {
      const skill = catalog.find(String(args.path || '').replace(/\/+$/, ''));
      if (!skill) {
        const near = catalog.search(String(args.path || '').replace(/\//g, ' '), 3)
          .map((h) => h.skill.path).join(', ');
        return toolError(`no skill at '${args.path}'. Closest: ${near}`);
      }
      return text(catalog.read(skill.path));
    }
    case 'list_families':
      return text(familiesSummary(catalog));
    case 'list_skills': {
      let skills = catalog.leaves;
      if (args.family) skills = skills.filter((s) => s.family === args.family);
      if (args.pack) skills = skills.filter((s) => s.pack === args.pack);
      if (skills.length === 0) return toolError('no skills match that family/pack filter. Call list_families first.');
      return text(skills.map((s) => `${s.path}: ${s.description.split('. ')[0]}.`).join('\n'));
    }
    case 'get_standards': {
      let standards = catalog.manifest.standards;
      if (args.id) {
        const id = String(args.id).toLowerCase();
        standards = standards.filter((s) => s.id.toLowerCase() === id);
        if (standards.length === 0) return toolError(`no standard with id '${args.id}'. Omit id to list all.`);
      }
      return text(standards.map((s) =>
        `${s.id}: ${s.name}\n  publisher: ${s.publisher}\n  status: ${s.status}${s.gated ? ' (gated: no verbatim text)' : ''}\n  domain: ${s.domain}`)
        .join('\n\n'));
    }
    default:
      return toolError(`unknown tool '${name}'`);
  }
}

function serve() {
  const catalog = new Catalog();
  let buffer = '';

  const reply = (id, result, error) => {
    const msg = { jsonrpc: '2.0', id };
    if (error) msg.error = error;
    else msg.result = result;
    process.stdout.write(JSON.stringify(msg) + '\n');
  };

  const handle = (req) => {
    const isNotification = req.id === undefined || req.id === null;
    switch (req.method) {
      case 'initialize':
        return reply(req.id, {
          protocolVersion: (req.params && req.params.protocolVersion) || '2025-06-18',
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: 'aero-agent-skills', version: version() },
        });
      case 'ping':
        return reply(req.id, {});
      case 'tools/list':
        return reply(req.id, { tools: TOOLS });
      case 'tools/call':
        try {
          return reply(req.id, callTool(catalog, req.params && req.params.name, req.params && req.params.arguments));
        } catch (e) {
          return reply(req.id, toolError(`tool failed: ${e.message}`));
        }
      default:
        if (isNotification) return undefined; // notifications/* — no response by design
        return reply(req.id, undefined, { code: -32601, message: `method not found: ${req.method}` });
    }
  };

  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => {
    buffer += chunk;
    let nl;
    while ((nl = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      let req;
      try {
        req = JSON.parse(line);
      } catch {
        reply(null, undefined, { code: -32700, message: 'parse error' });
        continue;
      }
      handle(req);
    }
  });
  process.stdin.on('end', () => process.exit(0));
}

module.exports = { serve, callTool, TOOLS };
