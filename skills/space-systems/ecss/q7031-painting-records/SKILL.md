---
name: q7031-painting-records
description: "Audit the per-unit painting record that has to survive the paint shop, and name every gap in it. Use when a coated unit is being released on its paperwork: check that the record states unit, drawing issue, primer and topcoat lots, operator and inspection result, that every application parameter from mix ratio to cure duration is actually stated rather than implied, that the mixed material went on inside its pot life, that each lot was inside its shelf life when mixed, that every applied lot walks back to the received-lots register, and that the retention date is set. Trigger: ecss, q-st-70-31c-painting-scope, per-unit-painting-record, paint-lot-traceability-chain, mixed-paint-pot-life-window, paint-lot-shelf-life-at-mixing, painting-record-retention-period."
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
  tags: [ecss, q-st-70-31c-painting-scope, q7031-painting-records, per-unit-painting-record, paint-lot-traceability-chain, mixed-paint-pot-life-window, paint-lot-shelf-life-at-mixing, painting-record-retention-period]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Painting — Painting Records (space-systems/ecss/q7031-painting-records)

Use when the task is the records clause of ECSS-Q-ST-70-31C: a unit has been
coated, the hardware is long out of the booth, and everything anyone will ever
know about how it was painted is what the record says.

## Domain quick reference

- The record is per unit, not per shift. A shop log that says which lots were
  open that week cannot answer which lots went onto serial number twelve, and
  that is the question a nonconformance five years later will ask.
- Application parameters are stated, not implied. Mix ratio, spray pressure,
  gun distance, pass count, flash-off, cure temperature and cure duration each
  either appear as a value or are a gap; a parameter recorded as a blank or as
  a word is missing, not zero.
- Pot life is spent in minutes, which is why the record carries timestamps and
  not dates. A stamp with no time cannot be read as midnight, because midnight
  quietly hands the mix a whole extra working life.
- Material used right up to the stated pot life is inside it. Material still
  going on afterwards was applied past what the datasheet supports, whatever
  the film looks like.
- Shelf life is judged at the moment of mixing, against the lot manufacture
  day, and a lot mixed on its expiry day is still usable. A month-end
  manufacture day clamps to the shorter month at expiry rather than rolling
  forward and gaining a day.
- Traceability closes only when every lot applied to the part walks back to a
  receipt in the register. A lot that appears solely in the paint shop's own
  note is a gap, and it is the gap that makes an investigation stop.
- The findings split. Missing fields and unstated parameters leave the record
  incomplete and can be filled in. An exceeded pot life, a lot past shelf life
  or a broken traceability chain make the record invalid, because they are
  statements about the hardware rather than about the paperwork.

## Workflow

1. Name every required record field that is absent or blank, individually.
2. Name every application parameter the record fails to state, treating a
   non-numeric value as unstated rather than as a reading.
3. Take the minutes between the mix stamp and the end of application and put
   them against the pot life, treating a use exactly on the limit as inside.
   Raise an unevaluated pot life when either stamp is missing.
4. Expire each paint lot from its manufacture day and shelf months, and raise
   any lot that was already past expiry on the day it was mixed.
5. Walk every applied lot back to the received-lots register, matching
   identifiers without regard to letter case, and name each one that does not
   land.
6. Set the retention end day from the record day and the retention period.
7. Issue the state: complete with no findings; invalid where pot life, shelf
   life or traceability failed; incomplete where only fields or parameters are
   missing. Aggregate across the record set, which closes only when every unit
   record does.

## Pitfalls

- Recording the lot number of the tin on the bench rather than the lots
  actually mixed, which breaks the chain at the one point it is needed.
- Writing a mix date without a time, so pot life can never be computed and the
  record silently supports whatever anyone later claims.
- Judging shelf life against the application day instead of the mix day, which
  is later and more forgiving than the moment that matters.
- Filing one record per batch, so a later unit-level question has no unit-level
  answer.
- Treating a traceability gap as a paperwork gap. A lot nobody can find the
  receipt for is an unknown material on flight hardware.
- Letting the retention clock start at delivery rather than at the record, so
  records are disposed of while the hardware is still flying.

## Behavior contract (gate 3)

The field and parameter completeness, timestamp parsing and minute arithmetic,
pot-life window, shelf-life expiry at mixing, traceability chain closure,
retention dating and the record state are exercised by the gate 3 contract
test: scripts/test_q7031_painting_records.py against
scripts/q7031_painting_records_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7031_painting_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
