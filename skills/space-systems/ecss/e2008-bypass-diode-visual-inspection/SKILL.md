---
name: e2008-bypass-diode-visual-inspection
description: "Verify every cell bypass diode on a photovoltaic assembly against ECSS-E-ST-20-08C clause 5.5.3.2.9: examine each diode body for a crack or for material that has separated, compute the crack extent against the smallest body side and the separated length against the length that was bonded, and disposition the diode as accept, refer-for-review, examination-invalid or reject — a defect seen at low magnification still stands while a clean look at low magnification establishes nothing — then total the cells whose bypass protection is left unestablished on each string and hold the assembly open until every declared diode carries a record. Use when the diodes on an assembly have been examined and each one needs a disposition. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-9, bypass-diode-body-crack-screening, bypass-diode-body-separation-limits, bypass-diode-examination-magnification, bypass-diode-record-completeness."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bypass-diode-visual-inspection, bypass-diode-body-crack-screening, bypass-diode-body-separation-limits, bypass-diode-examination-magnification, bypass-diode-string-protection-rollup, bypass-diode-record-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Bypass Diode Visual Inspection (space-systems/ecss/e2008-bypass-diode-visual-inspection)

Use when the task is the bypass diode examination of ECSS-E-ST-20-08C
clause 5.5.3.2.9 -- looking at the body of each cell bypass diode for a
crack or for separated material, and keeping the assembly open until
every diode has been looked at.

## Domain quick reference

- The question is narrow and the answer is binary in intent. A cracked
  body, or body material that has lifted or parted, is not permitted,
  because the diode is what carries a shadowed or reverse-biased
  string past the cells it protects and a broken body no longer
  guarantees that path.
- The numbers are still worth computing even when the verdict does not
  turn on them. A crack extent against the smallest body side says how
  close the crack is to crossing the body; a separated length against
  the length that was bonded says how much of the joint is left. Both
  belong in the record the review board reads.
- A reported crack longer than the body diagonal is a measurement
  error, not a worse defect, and a separated length longer than the
  bonded length is the same kind of error. Either one is refused
  before it is graded.
- The magnification is part of the evidence. A crack seen at low
  magnification is there, so the finding stands. An absence of
  findings at low magnification says nothing about the body, so the
  examination is marked invalid rather than accepted -- the two cases
  look identical in a record that only stores the verdict.
- A mark that could not be resolved into a crack or a separation is
  neither accepted nor rejected. It goes back for re-examination at
  higher magnification, and the diode stays out of the accept band
  until it has been.
- The consequence is a string-level one. Each diode not accepted
  leaves the cells it protects without established bypass protection,
  and those cells are totalled per string against the allowance rather
  than reported as one assembly count.

## Workflow

1. Take the declared diode count and the examination records. Refuse a
   record set larger than the declared count, and report the shortfall
   when it is smaller.
2. For each diode, derive the body geometry -- smallest side and
   diagonal -- and refuse a body whose sides are implausibly small for
   a record about to be graded.
3. Grade each observation: crack extent against the smallest side,
   separated length against the bonded length, and an unresolved mark
   back for re-examination.
4. Take the worst observation as the diode verdict, then apply the
   magnification rule: a rejection stands at any magnification, and an
   otherwise clean diode examined below the minimum is recorded as an
   invalid examination.
5. Total the protected cells of every diode that is not accepted, by
   string, and compare each string against the allowance.
6. Report the worst verdict, the diodes not accepted, the ones needing
   re-examination, the per-string unprotected cell counts and the
   completeness flag.

## Pitfalls

- Recording a clean look at low magnification as an acceptance. An
  examination that could not have seen the defect is not evidence that
  there is none.
- Discarding a finding because the magnification was too low. The
  inadequate magnification weakens a negative result, never a positive
  one.
- Forcing an unresolved mark into accept or reject. The clause needs
  the mark resolved first, and guessing either way loses the
  re-examination.
- Reporting a verdict with no numbers. The extent and the separated
  fraction are what a review board weighs when it looks at a
  non-conformance.
- Counting unprotected cells across the whole assembly. Bypass
  protection is a string property, and a single string carrying every
  loss reads as acceptable once it is averaged over the assembly.
- Grading a record whose separated length exceeds the bonded length,
  or whose crack is longer than the body diagonal. Those are data
  faults, and grading them puts a fabricated severity into the file.
- Comparing a measured magnification with the declared minimum by bare
  arithmetic. A value sitting exactly on the minimum can evaluate a
  few units in the last place below it; the comparison absorbs that
  representation error while the minimum stays untouched.

## Behavior contract (gate 3)

The body geometry, per-observation crack and separation grading, the
unresolved-mark path, the magnification rule, the per-string
unprotected cell totals and the assembly completeness rollup are
exercised by the gate 3 contract test:
scripts/test_e2008_bypass_diode_visual_inspection.py against
scripts/e2008_bypass_diode_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bypass_diode_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
