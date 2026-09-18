---
name: q2030-demating-logbook
description: "Maintain the per-connector (de-)mating logbook of the ECSS-Q-ST-20-30 Annex B worked example: hold the entry order, refuse a demate with no mate before it, a connector mated twice or a sheet running backwards in time, count the mating cycles each connector has consumed, subtract them from its declared maximum to give the remaining-cycle countdown, and render the maximum-cycle control table with an approaching-limit band computed in integers. Use when a connector logbook is opened, an integration mate or demate is entered, or a harness is screened before flight for cycle exhaustion. Trigger: ecss, q-st-20-30-annex-b, demating-logbook, connector-mating-cycle-countdown, maximum-mating-cycle-control, mate-demate-event-log, connector-cycle-exhaustion."
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
  tags: [ecss, q-st-20-30-connector-mating-scope, q2030-demating-logbook, connector-mating-cycle-countdown, maximum-mating-cycle-control, mate-demate-event-log, connector-cycle-exhaustion, demating-logbook-control-table]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Connector (De-)Mating Logbook (space-systems/ecss/q2030-demating-logbook)

Use when the task is the informative (de-)mating logbook of ECSS-Q-ST-20-30
Annex B taken as the house connector mating record: a connector is being
mated or demated during integration, or a harness is being screened before
flight, and the question is how many mating cycles each connector has left.

## Domain quick reference

- The logbook is per connector, not per operation. Entries for many
  connectors share one sheet, so the alternation and the countdown are
  resolved inside each connector's own entry stream and interleaving two
  connectors' work must not disturb either.
- A connector arrives demated. The first entry against it is therefore a
  mate, and mate and demate alternate from there. A demate with no mate
  before it, or a second mate with no demate between, is a book-keeping
  error rather than a cycle to count, and it is refused on entry.
- A cycle is consumed by the mate, not by the pair. A connector mated and
  left in place has already spent the cycle; waiting for the demate before
  counting it understates the wear on every connector still mated at
  delivery.
- The maximum is a property of the connector's qualification, not of the
  sheet. A connector with no maximum declared anywhere is not
  unconstrained; the default is applied and the absence itself is reported,
  because a silent default is how an under-rated connector reaches flight.
- The approaching-limit band is arithmetic, not judgement. Four fifths of
  the maximum, computed as an integer ratio so the band opens on the same
  cycle for an odd maximum on every machine, keeps the sheet reproducible.
- Two connectors at the same count are not in the same condition. The
  countdown, not the count, is what the control table shows, because a
  connector rated for thirty cycles and one rated for five read alike on
  cycles used alone.

## Workflow

1. Refuse an entry carrying a field the logbook has no place for, so a
   local variant is caught rather than silently dropped.
2. Normalise each entry: connector and operator identifiers trimmed and
   lowered, the day an ISO date, the operation one of the two the book
   records.
3. Group entries by connector in the order the connectors first appear, and
   check each group for non-decreasing dates and for mate/demate alternation
   from a mate.
4. Count the mates as consumed cycles and read the connector's state off its
   last entry.
5. Resolve each connector's maximum from the declared table, falling back to
   the default and flagging that it was needed, then compute the remaining
   countdown floored at zero.
6. Place each connector in its control band with integer arithmetic only:
   within limit, approaching limit, at limit, exceeded.
7. Render the control table with one aligned row per connector and report
   the findings: a connector over or at its maximum, an undeclared maximum,
   and a connector left in a state the integration flow did not expect.

## Pitfalls

- Counting a cycle only when the pair closes. Every connector still mated at
  the end of integration then reads one cycle light, which is exactly the
  population the countdown exists to protect.
- Sorting the whole sheet by date before grouping. Alternation is a property
  of one connector's stream; a global sort hides a demate that preceded its
  mate on a busy day.
- Treating an undeclared maximum as no limit. The default has to be applied
  and the omission reported, or the connector never appears in the exceeded
  band at all.
- Computing the warning band in floating point. Four fifths of an odd
  maximum lands between cycles, and a rounding difference moves the band
  edge by a whole cycle between machines.
- Reading cycles used instead of cycles left. Connectors with different
  qualifications are not comparable on the used count, and the sheet is read
  for the connector nearest exhaustion.

## Behavior contract (gate 3)

The entry field order and unknown-field refusal, the operation and date
validation, the per-connector alternation rules, the cycle count, the state
read-off, the countdown floor, the integer control band, the aligned control
table and the finding set are exercised by the gate 3 contract test:
scripts/test_q2030_demating_logbook.py against
scripts/q2030_demating_logbook_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2030_demating_logbook.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
