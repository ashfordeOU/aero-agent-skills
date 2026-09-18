---
name: e2007-wiring-and-shielding-verification
description: "Audit the two-stage wiring and shielding verification of a spacecraft harness under ECSS-E-ST-20-07C clause 5.3.11. Use when the task is confirming that every run was both design-reviewed on paper and physically inspected on the build, that the as-built wire category agrees with the documented one, that the shield termination matches what the category needs, that a pigtail stub stays inside its length limit, and that the inspected share of each category clears its sampling floor, with a full-population floor for the sensitive and interfering runs. Trigger: ecss, e-st-20-07c, harness-shield-termination, wire-category-verification, as-built-harness-inspection, pigtail-length-limit, full-circumference-shield-termination, harness-inspection-coverage, wiring-design-review."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-wiring-and-shielding-verification, harness-shield-termination, wire-category-verification, as-built-harness-inspection, pigtail-length-limit, harness-inspection-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Wiring And Shielding Verification (space-systems/ecss/e2007-wiring-and-shielding-verification)

Use when the task is the wiring and shielding verification of
ECSS-E-ST-20-07C clause 5.3.11 -- proving that the harness categories
and the shield treatment were checked twice, once against the
documentation and once against the hardware, and that the two checks
agree.

## Domain quick reference

- Two stages, two different jobs. The design review reads the wiring
  documentation and confirms that each run has been given a category
  and a shield treatment on paper. The physical inspection looks at the
  built harness and records what was actually fitted. Paper without
  hardware verifies an intention; hardware without paper has nothing to
  verify against. Both are required for every run, and each has to
  leave an evidence reference behind, because a stage recorded as done
  with nothing to point at is an assertion, not a verification.
- The interesting output is the disagreement. A run categorized as
  sensitive on the drawing and built into a signal bundle is exactly
  the defect the two-stage structure exists to catch, and so is a
  shield that left the drawing as a full-circumference termination and
  arrived as a pigtail. Neither stage alone can see either one.
- The shield treatment is graded against the run's category, not
  against a single house rule. A sensitive or interfering run needs a
  full-circumference termination, because the transfer impedance of the
  joint is in series with the shield and a stub undoes it. A signal or
  power run may be pigtailed, but the stub is unshielded wire in series
  with a shielded run, so its length is capped. A shielded run
  terminated nowhere is a finding in every category -- an unterminated
  shield is an antenna with a floating feed.
- Inspection coverage is per category, not per harness. Sensitive and
  interfering runs are inspected one by one, because each is either the
  victim or the aggressor in every coupling path it touches. Signal and
  power runs may be sampled, but the sample has a floor, and a floor
  met across the harness while one category sits at zero is not met.
- An unshielded run is not exempt from the review, it is checked
  differently: it must not carry a shield termination in its
  documentation, because a termination recorded against a run with no
  shield means the two records describe different hardware.

## Workflow

1. Validate each run record: identifier, documented category,
   inspected category, documented and inspected terminations, pigtail
   lengths, shielded flag, the two stage flags and their evidence
   references. Reject an unknown category or termination, a negative
   pigtail length, or a non-boolean stage flag.
2. Grade the design-review stage: performed at all, an evidence
   reference present, and a documented pigtail carrying a documented
   length.
3. Grade the physical-inspection stage: performed at all, an evidence
   reference present, and the as-built category, termination and
   pigtail length actually recorded rather than left blank.
4. Compare the stages: an as-built category differing from the
   documented one, and an as-built termination differing from the
   documented one, are separate findings.
5. Grade the shield treatment against the run's category, using the
   as-built termination where one was recorded and the documented one
   otherwise, and cap a pigtail at its length limit.
6. Compute the inspected share of each category and compare it against
   that category's floor. Treat a share falling under its floor only by
   the ratio representation error as met -- the named tolerance absorbs
   it and the floor itself is never lowered. The harness is verified
   only when no run carries a finding and no category is under its
   floor.

## Pitfalls

- Accepting a design review as the verification. It confirms that
  somebody wrote a category down, and the clause asks whether the
  harness was built that way.
- Accepting an inspection as the verification. A photograph of a
  termination proves a termination exists, not that it is the one the
  run's category needs.
- Recording a stage as done with no evidence reference. It reads as
  coverage in every summary and cannot be reviewed by anyone who was
  not in the room.
- Grading every shield termination against one rule. A pigtail is
  acceptable on a power run and defeats a sensitive one, and a single
  house rule either over-constrains the first or passes the second.
- Averaging inspection coverage over the whole harness. A large
  well-sampled signal population hides a sensitive category nobody
  inspected, and the sensitive runs are the ones that had to be seen.

## Behavior contract (gate 3)

The record-validation, design-review, physical-inspection,
category-agreement, shield-treatment, pigtail-limit and
coverage-floor logic is exercised by the gate 3 contract test:
scripts/test_e2007_wiring_and_shielding_verification.py against
scripts/e2007_wiring_and_shielding_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_wiring_and_shielding_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
