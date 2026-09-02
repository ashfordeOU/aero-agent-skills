---
name: skill-evaluation
description: "Use when you must evaluate a delivered skill against SEP-2640-style conformance and quality criteria: run conformance checks on the package (frontmatter, description with trigger, license, standards references), judge whether the skill's contract test exercises the core logic, score deterministic quality criteria (offline, no network, stdlib only), compute coverage ratio of tested versus total behavior, and issue an acceptance verdict (accept, rework, or reject). SEP-2640 stays an emerging spec and an adapter over the agentskills.io content format, so evaluation reuses the same conformance shape as skill delivery. Trigger: skill evaluation, SEP-2640, conformance check, acceptance verdict, quality score, coverage ratio, skill review."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: sep-2640
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: sep2640
  tags: [sep-2640, skill-evaluation, conformance-check, acceptance-verdict, quality-score, coverage-ratio, skill-review]
  version: 0.1.0
  author: Aero Agent Skills
---

# SEP-2640 Skill Evaluation (cross-cutting/sep2640/skill-evaluation)

Use when the task is evaluating a delivered skill against SEP-2640-style
conformance and quality criteria: conformance checks, behavioral
coverage, quality scoring, and an acceptance verdict.

## Domain quick reference

- Evaluation mirrors the SEP-2640 delivery shape (skills over MCP,
  agentskills.io content form); the spec is emerging, so evaluation
  targets the stable conformance surface: frontmatter fields,
  description with trigger, license, and standards references.
- Conformance checks are boolean gates; one failure fails the package.
- Quality criteria are scored 0.0-1.0 each and combined by weighted
  mean; weights must sum to 1.0.
- Coverage ratio = tested behaviors / total behaviors, in 0.0-1.0.
- Acceptance verdict by weighted score and threshold:
  score >= accept threshold -> accept; score >= rework threshold
  (but below accept) -> rework; below both -> reject.
- Verdicts stay deterministic: same inputs, same outputs, offline.

## Workflow

1. Run the conformance checks on the delivered package (frontmatter
   present, name kebab-case matching the folder, description with a
   trigger clause, license, standards references).
2. Combine the pass/fail checks into a conformance verdict dict and
   decide whether the package is conformant (all pass) or not.
3. Inspect the contract test: does it exercise the core logic of the
   skill? Score behavioral coverage (tested versus total behavior).
4. Score the deterministic quality criteria (offline, no network,
   stdlib only) and compute the weighted total.
5. Issue the acceptance verdict from the weighted score and the
   thresholds, then report the coverage ratio.

## Pitfalls

- Failing one conformance check but declaring the package conformant.
- Weights that do not sum to 1.0 silently skewing the total.
- Scoring a contract test that imports non-stdlib modules as
  deterministic and offline.
- Accepting a skill whose contract test never calls the core logic.
- Reject threshold above the accept threshold (accept then becomes
  unreachable).

## Behavior contract (gate 3)

The conformance, scoring, coverage, and verdict logic is exercised by
the gate 3 contract test: scripts/test_evaluation.py against
scripts/evaluation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_evaluation.py

## Compliance

- SEP-2640 is an open specification; quote with citation and note the
  status (emerging, not yet stable) per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
