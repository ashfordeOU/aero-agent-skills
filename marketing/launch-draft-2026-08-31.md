# AeroSkills launch draft (X thread), founder-gated, not posted

**Status:** draft-in-tree only. No external send without founder GO.
**Date:** 2026-08-31 · **Owner:** Content Writer · **Gate:** release is
founder-gated (AGENTS.md: publish is founder VETO).
**Numbers:** canonical register ops/automation/numbers.yaml, as_of
2026-08-31; live snapshot ops/automation/state/stars-latest.json.
**Voice:** cold truth, no superlatives. "Verified" = replayable
make validate 5/5 on the commit you are looking at. Cross-harness is
a format-level claim, not a per-host test report.

## Draft (5 lines, X thread style)

1. AeroSkills ships: 43 aerospace engineering skills for AI agents,
   mapped to the 15 domain standards in standards-map.yaml (DO-178C,
   DO-254, ARP4754A, ARP4761A, AS9100, DO-330, DO-160G, AS9102,
   MMPDS, FAR-25/CS-25, FAR-33, ARINC 429, ECSS, NACA TR-824), delivered as SKILL.md on
   the open agentskills.io format and served over MCP per SEP-2640
   (skills-over-MCP, delivery format, not a domain standard).
2. Not a folder of prompts. Every skill passes make validate: 5 real
   gates, spec conformance to Hit@1 routing. Deterministic, offline,
   replayable: clone, run, exit 0.
3. Verified means exactly that: the gates pass on the commit you are
   looking at. Nothing more. Not certification, not approval, not
   airworthy.
4. The lane is empty. Total across all attempts is about 228★.
   Adjacent domains prove the play: Anthropic-Cybersecurity-Skills at
   31.7k★, K-Dense Scientific Agent Skills at 40.4k★.
5. Format-level cross-harness: SKILL.md on the open agentskills.io
   format, loadable by any host that reads it (Claude Code, Hermes,
   OpenClaw, Codex). Apache-2.0. Star the repo if it saves you an
   afternoon.

## Notes

- "Verified" is defined by line 3 every time it appears; it never
  means certified, approved, or airworthy.
- If the founder wants a release-note variant, the same five lines
  convert to bullets with no factual change.
- Repo URL to be filled at founder GO (origin is private today).
