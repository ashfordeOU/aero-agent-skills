---
name: q40-02-step2-identify-assess
description: "Identify and assess the hazards of a space system under ECSS-Q-ST-40-02C clause 5.2.2, step 2. Use when the task is working all four identification sources - the generic hazard library, the system functions, the planned operations and the induced or natural environments - into one hazard list, then giving each entry a severity category and a likelihood band drawn from evidence rather than opinion, banding a quantified per-mission probability instead of carrying the number forward, and reading the pair into the project risk index and its acceptability grouping. Reports the sources left unworked and the entries whose severity or likelihood nothing supports. Trigger: ecss, q-st-40-02c, ecss-hazard-identification-sources, ecss-hazard-severity-category, ecss-hazard-likelihood-band, ecss-project-risk-index, space-hazard-acceptability-grouping."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-40-02-hazard-analysis-scope, q40-02-step2-identify-assess, ecss-hazard-identification-sources, ecss-hazard-severity-category, ecss-hazard-likelihood-band, ecss-project-risk-index, space-hazard-acceptability-grouping]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hazard Analysis — Step 2, Identify and Assess (space-systems/ecss/q40-02-step2-identify-assess)

Use when the task is step 2 of the ECSS-Q-ST-40-02C clause 5.2 process —
building the hazard list from all four identification sources and giving
each entry the severity, likelihood and risk index the rest of the
process is decided on.

## Domain quick reference

- There are four sources, and they surface different hazards. The
  generic library carries what has hurt space projects before; the
  system functions carry what this design can do wrong; the planned
  operations carry what people will do to it; the induced and natural
  environments carry what it will be subjected to. A list built from
  one source is complete with respect to that source and silent about
  the other three.
- Severity is about the worst credible consequence, not the likely
  one. The categories run from catastrophic down to minor, and the
  ordinal is what enters the matrix — the words are a label on an
  index, not the index itself.
- Likelihood is a band, not a number. Where a quantified per-mission
  probability exists it is placed in a band and the band is what moves
  forward, because the fourth significant figure of a probability
  never survives the assumptions behind it. A supplied probability
  overrides a hand-declared band: the evidence wins.
- The risk index is an integer read from the severity-likelihood
  matrix, and it stays an integer all the way to the acceptability
  grouping. Unacceptable, undesirable, acceptable-with-review and
  acceptable are the four groups the project acts on; nothing in the
  chain needs a float, so nothing in it can disagree across platforms.
- An unsupported severity or likelihood is a finding of its own. The
  index is only as good as the pair it is read from, so an entry whose
  severity nobody can defend produces an index nobody should act on,
  and it is reported as such rather than silently used.

## Workflow

1. Validate each hazard entry: identifier, identification source,
   severity category, and either a likelihood band or a per-mission
   probability. Reject an unknown source or severity, and reject an
   entry with neither a band nor a probability.
2. Where a probability is supplied, place it in its band. Boundaries
   are inclusive at the upper band, and the tolerance applied there
   absorbs the representation error of a probability that was itself
   computed rather than measured.
3. Read the severity and likelihood ordinals into the risk-index matrix
   and group the resulting index into its acceptability band.
4. Record whether the severity and the likelihood each have evidence
   behind them, and raise a finding for either one that does not.
5. Compute source coverage across the whole list and name the sources
   nobody worked.
6. Aggregate: the acceptability distribution, the unacceptable entries
   called out by identifier, and every finding. Step 2 is complete only
   when all four sources were worked and every entry is supported.

## Pitfalls

- Working the generic library and stopping. It is the fastest source
  and the one least specific to this design, so a list built from it
  alone looks long and misses the function-specific hazards entirely.
- Assigning severity from the expected outcome rather than the worst
  credible one. A hazard whose usual result is an aborted operation
  can still have a catastrophic worst case, and severity is set by the
  second.
- Carrying a quantified probability forward as a number. It implies a
  precision the underlying assumptions do not support, and two entries
  that differ only in the third significant figure will be argued over
  as if the difference were real.
- Treating a declared likelihood band as authoritative when a
  probability is also on record. The probability is the evidence and
  the band is a summary of it, so the probability decides.
- Acting on an index whose severity or likelihood nothing supports.
  The number looks the same as a supported one, which is exactly why
  the support state travels with it.

## Behavior contract (gate 3)

The probability banding, risk-index matrix, acceptability grouping,
entry validation, evidence-support and source-coverage logic is
exercised by the gate 3 contract test:
scripts/test_q40_02_step2_identify_assess.py against
scripts/q40_02_step2_identify_assess_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_02_step2_identify_assess.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
