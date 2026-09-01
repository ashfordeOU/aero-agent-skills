# AeroSkills v1.0.0-rc1 release notes (draft, founder-gated)

**Status:** draft-in-tree only. No external send without founder GO
(publish = founder VETO, AGENTS.md).
**Date:** 2026-08-31 · **Owner:** Ops Manager (draft), Content Writer
(public copy on GO) · **Base:** final RC commit, tag v1.0.0-rc1.
**Voice:** cold truth. "Verified" is defined in section 2 and means
exactly that, nothing more. No certified, no approved, no airworthy.

## 1. What ships

- 43 aerospace engineering skills for AI agents across 27 sub-domain
  packs in 9 families (52 SKILL.md files: 9 family router roots + 43
  leaf skills). Families: aerodynamics, avionics, gnc-autonomy,
  manufacturing-quality, space-systems, structures,
  systems-engineering-safety, vehicle-design, cross-cutting.
- Standards map (standards-map.yaml, machine-readable): 16 mapped
  standards, 10 gated. Gated standards never appear verbatim anywhere;
  a real gate (make validate gate 4, no-verbatim) enforces it. The
  15 DOMAIN standards are DO-178C, DO-254, ARP4754A, ARP4761A,
  AS9100, DO-330, DO-160G, AS9102, MMPDS, FAR-25/CS-25, FAR-33,
  ARINC 429, ECSS, and
  NACA TR-824; SEP-2640 is the delivery format (skills over MCP,
  emerging open spec), separate from the domain list.
- Eval corpus: 102 tasks (90 domain + 12 adversarial cross-pair), all
  asserting top-1 routing on a deterministic offline router. Every
  skill also ships a stdlib unittest behavior contract (43 suites)
  run by gate 3.

## 2. Verified means this

make validate runs 5 REAL gates before anything ships:

1. spec lint: agentskills.io conformance + compliance flags
2. description lint: what + when + trigger, written for the router
3. behavior tests: per-skill contract, stdlib unittest, offline
4. no-verbatim: standards text copyright control
5. Hit@1: routing corpus resolves to the expected skill (102/102)

Deterministic, offline, replayable: clone, run make validate, exit 0.
That is what verified means in this repository, on the commit you are
looking at. It is not certification, not approval, not airworthy.

## 3. Honesty, stated plainly

- Not affiliated with or endorsed by RTCA, EUROCAE, SAE International,
  IAQG, EASA, FAA, or any government.
- As published, the library is not ITAR- or EAR-controlled technical
  data (public-domain exclusion, EU dual-use Regulation (EU)
  2021/821, Annex I General Technology Note). Users are responsible
  for their own compliance with the export-control and sanctions laws
  that apply to their use. Verify before use.
- Pricing HOLD: no prices are set or proposed here. The core library
  is Apache-2.0 and free.

## 4. Why the lane matters

The aerospace lane is unserved. Total across all attempts is about 228★.
The two live attempts: ajhcs/mbse-agents (22★) and
devideamax/aerospace-team (21★). Adjacent domains prove the play:
Anthropic-Cybersecurity-Skills (31,700★) and K-Dense Scientific Agent
Skills (40,842★) both won on framework mapping and evals, the same
two things AeroSkills ships first.

## 5. Format and license

Each skill is a SKILL.md document on the open agentskills.io format;
any host that reads the format can load it (Claude Code, Hermes,
OpenClaw, and Codex are named examples; this is a format-level claim,
not a per-host test report). Skills are plain files, no lock-in.
Apache-2.0, published by Ashforde OU (Estonia). Standards remain the
property of their publishers and must be purchased from them
(STANDARDS.md).

## 6. Related

- Gate contract: docs/harness-contract.md
- FAQ: docs/FAQ.md · Standards: STANDARDS.md
