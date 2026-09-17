---
name: q60-class-2-stock-relifing
description: "Determine whether expired Class 2 EEE stock can have its storage validity restored under ECSS-Q-ST-60C clause 5.3.10: scale the package family baseline period by the store the parts actually sat in, test the elapsed storage against the period that grants, check the relifing round ceiling before any test is sized, assemble the test set the package, lead finish and part function owe, judge every result against its accept number, and re-grant a decaying shortened period floored so a re-grant too short to issue against becomes re-screening. Use when stored Class 2 parts are past their expiry and stores needs a disposition. Trigger: ecss, q-st-60c, class-2-storage-period-scaling, class-2-relifing-round-ceiling, class-2-relifing-test-set, class-2-shortened-regrant-period, class-2-relifing-disposition."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c, q60-class-2-stock-relifing, class-2-storage-period-scaling, class-2-relifing-round-ceiling, class-2-relifing-test-set, class-2-shortened-regrant-period, class-2-relifing-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — Stock Relifing (space-systems/ecss/q60-class-2-stock-relifing)

Use when the task is clause 5.3.10 of ECSS-Q-ST-60C: restoring the storage
validity of Class 2 stock whose original period has run out, so parts already
bought and already in store can be issued again without being re-procured.

## Domain quick reference

- The storage period is a property of the package and the store together. A
  hermetic package in dry nitrogen and the same package in an uncontrolled bay
  are not entitled to the same period, so the store is a multiplier on the
  package baseline rather than a separate clock kept beside it.
- An unlisted package family is refused, never read off a neighbouring entry.
  Between two families in the register there is no period at all, and picking
  the nearer of the two invents an entitlement nobody granted.
- Relifing is a recovery, not a routine. Stock still inside its period owes
  nothing, and running the tests early consumes units and buys no validity.
- The round ceiling is checked before any test is sized. Repeated relifing
  cannot substitute for re-establishing the screen, so stock that has used up
  its rounds is referred to full re-screening without a test being run.
- The test set comes from the part, not from the cupboard. A hermetic package
  owes a leak test, a finished lead owes solderability, a pure-tin finish owes
  a whisker review, and an active part owes electrical at the extremes.
- A result for a test the stock does not owe is refused alongside a missing
  result for one it does. Neither can be quietly read as a pass.
- The re-granted period decays with every round, because each round restores
  validity to stock that has been in store longer than the round before it. A
  re-grant under its floor is not a short period, it is re-screening.

## Workflow

1. Read the package family baseline and the store grade, and multiply them
   into the period this stock was entitled to.
2. Compare the elapsed storage against that period, counting stock exactly on
   the period as still inside it, and return early where nothing is owed.
3. Test the completed relifing rounds against the ceiling before sizing any
   sample; a lot at the ceiling is referred to re-screening.
4. Assemble the owed test set from the package family, the lead finish and the
   part function, and size the sample proportionally, floored and capped.
5. Judge each owed test against its accept number, refusing a missing result,
   an unowed result, or more failures than the sample holds.
6. Re-grant a decayed period from the relifing date and test it against the
   usable floor before it is issued against.

## Pitfalls

- Granting a period from the package alone. The store is half the answer, and
  a period taken from the datasheet passes stock that sat in a warm bay.
- Interpolating a period for an unlisted package family. The register is the
  entitlement; between two entries there is no entitlement to interpolate.
- Relifing stock that has not expired. It destroys sample units and restores
  validity the lot already held.
- Sizing the relifing tests before checking the round ceiling. The tests then
  pass, the stock is relifed a fourth time, and the ceiling is found in audit.
- Reading a missing test result as a pass. An owed test with no result is the
  most common way a relifing record looks complete and is not.
- Issuing against a re-granted period too short to reach the build. A period
  under its floor is re-screening wearing the wrong label.

## Behavior contract (gate 3)

The period scaling, expiry test, round ceiling, owed test set, sample sizing,
accept-number judgement, decayed re-grant and the relifing disposition are
exercised by the gate 3 contract test:
scripts/test_q60_class_2_stock_relifing.py against
scripts/q60_class_2_stock_relifing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q60_class_2_stock_relifing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
