---
name: q2010-dossier
description: "Maintain the off-the-shelf item evaluation dossier that ECSS-Q-ST-20-10C clause 5.1.3 and its Annex B data-requirement description ask for, as an append-only record of every evaluation performed on every candidate. Use when evidence is arriving from several evaluations and somebody has to say which Annex B sections a candidate still owes and whether any finding is unresolved. Adds entries without overwriting history, supersedes only by a higher revision, refuses a conclusion with no source reference or date behind it, reports coverage per candidate, and grades evidence older than its validity window as stale rather than counting it. Trigger: ecss, q-st-20-10, ots-evaluation-dossier, annex-b-drd-coverage, append-only-evaluation-record, entry-supersession-revision, stale-evaluation-evidence, unresolved-evaluation-finding."
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
  tags: [ecss, q-st-20-10-ots-utilisation-scope, q2010-dossier, ots-evaluation-dossier, annex-b-drd-coverage, append-only-evaluation-record, entry-supersession-revision, stale-evaluation-evidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS OTS Utilisation — Evaluation Dossier (space-systems/ecss/q2010-dossier)

Use when the task is the record-keeping step of ECSS-Q-ST-20-10C clause
5.1.3 — accumulating, per off-the-shelf candidate, the evidence of every
evaluation carried out on it, in the form the Annex B data-requirement
description asks for, so a selection can be defended long after the
people who made it have moved on.

## Domain quick reference

- The dossier is the deliverable, not a by-product. A selection
  defended by a summary table cannot answer the only question a review
  actually asks — what was examined, by whom, against what, and on which
  day — and that question arrives years later, when the supplier has
  changed the part.
- Accumulation is append-only. A later evaluation of the same subject
  supersedes the earlier one by carrying a higher revision, and the
  superseded entry stays in the dossier. Editing an entry in place
  destroys the only evidence that the conclusion ever moved, which is
  exactly the evidence an obsolescence argument later needs.
- Every entry rests on a source. An outcome with no reference behind it
  records somebody's opinion in a format that looks like a result, and
  it is indistinguishable from a measured conclusion once it is in the
  table.
- Coverage is per candidate, per section. A programme that has run deep
  functional evaluations on its favourite unit and nothing at all on the
  alternates has one dossier that looks healthy and a selection with no
  comparison behind it.
- Evidence ages. A qualification result from a supplier's earlier
  production lot is not wrong, but past a validity window it no longer
  describes the part on offer, so it is reported as stale rather than
  counted as coverage.
- An unresolved outcome is not an absence. A section carrying an open or
  failed evaluation is covered — the work was done — and the dossier
  still owes a closure entry, which is a different state from a section
  nobody has looked at.

## Workflow

1. Validate each entry: an identifier, the candidate, the Annex B
   section it populates, an outcome, the date, and the source reference
   the outcome rests on. Refuse an entry with no reference.
2. Append it. Refuse a repeat of an identifier at the same revision, and
   refuse a revision that does not exceed the standing one, so history
   can only grow.
3. Refuse a revision that moves an entry to a different candidate; that
   is a new entry, not a correction, and allowing it silently moves
   evidence between competing units.
4. Mark the predecessors superseded and keep them, so the dossier can
   show what an earlier evaluation concluded and when it was replaced.
5. Per candidate, compare the sections held by current entries with the
   Annex B section list; report covered, missing, and anything filed
   outside the description.
6. Compare each current entry's date with the as-of date and the
   validity window, counting an entry exactly on the window as still
   valid; refuse an entry dated after the as-of date outright.
7. Collect the unresolved outcomes as open findings, then assign the
   verdict in precedence order: incomplete while sections are missing,
   stale evidence next, open findings next, complete only when none of
   the three applies.

## Pitfalls

- Editing an entry in place when a re-evaluation changes the answer. The
  dossier then asserts that the conclusion was always the current one,
  and the reason it changed is unrecoverable.
- Filing a conclusion with the evaluator's name where the source
  reference belongs. Authorship is not evidence, and the substitution is
  invisible in the finished table.
- Treating a section with an open finding as missing. The evaluation
  happened; what it owes is a closure entry, and conflating the two
  sends somebody to repeat work that is already done.
- Counting evidence from an earlier production lot as current coverage.
  It is not wrong, it is stale, and the distinction is the whole point
  of the validity window.
- Building a full dossier on the preferred candidate only. The dossier
  then documents a decision instead of supporting one.

## Behavior contract (gate 3)

The entry validation, append-only accumulation, revision supersession,
history retention, per-candidate Annex B coverage, validity-window
staleness and verdict precedence are exercised by the gate 3 contract
test: scripts/test_q2010_dossier.py against
scripts/q2010_dossier_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2010_dossier.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
