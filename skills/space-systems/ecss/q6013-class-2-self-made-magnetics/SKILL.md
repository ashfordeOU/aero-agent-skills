---
name: q6013-class-2-self-made-magnetics
description: "Use when a wound magnetic delivery has to be judged acceptable. Evaluate whether a supplier-built magnetic component and its delivery lot carry the build basis and screening the intermediate assurance class needs under ECSS-Q-ST-60-13C clause 5.6.8: refuse a build standard with no issue, an unreleased supplier process or undelivered acceptance data, hold winding current density and hot-case flux utilization to their ceilings with equality admissible under a named tolerance, compare winding hot spot with the insulation rating and demonstrated withstand with the required multiple of working voltage, size the sample-drawn screening from the lot and name every per-unit and sample step never run. Trigger: ecss, q-st-60-13c-clause-5-6-8, supplier-built-magnetic-build-basis, wound-magnetic-lot-sample-sizing, magnetic-per-unit-screening-coverage, winding-current-density-ceiling, hot-case-flux-utilization-ceiling, magnetic-insulation-withstand-ratio."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-2-self-made-magnetics, q-st-60-13c-clause-5-6-8, supplier-built-magnetic-build-basis, wound-magnetic-lot-sample-sizing, magnetic-per-unit-screening-coverage, winding-current-density-ceiling, hot-case-flux-utilization-ceiling, magnetic-insulation-withstand-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 Commercial Parts — Supplier-Built Magnetics (space-systems/ecss/q6013-class-2-self-made-magnetics)

Use when the task is the self-made magnetics provision of ECSS-Q-ST-60-13C
clause 5.6.8 at the intermediate assurance class — a transformer, inductor or
choke built by a supplier to the project's own drawing rather than bought as a
catalogue item, the build basis that has to stand behind the delivered lot,
and the screening that lot receives before any unit is fitted.

## Domain quick reference

- A supplier-built magnetic has a builder but no catalogue standing. There is
  no datasheet to derate against, so the supplier's released winding process,
  the drawing it was built to and the issue of that drawing take the place a
  manufacturer's qualification would hold. A lot delivered against a drawing
  number with no issue has no traceable basis, because two deliveries to the
  same number can be two different parts if the process moved between them.
- Acceptance data delivered with the lot is part of the basis, not a courtesy.
  Measurements the supplier made and kept are measurements the project cannot
  review, and an unreviewable measurement carries the same weight as one that
  was never taken.
- The design basis is arithmetic. Conductor current density, worked in ampere
  per square millimetre, is what turns a winding into a heat source; core
  margin is stated as peak working flux over saturation flux at the hot case,
  never at room temperature. Both are quotients of measured values, so a
  design landing exactly on its ceiling is admissible and the equality is
  absorbed by a named tolerance rather than by moving the ceiling.
- The insulation system carries two independent duties: surviving the winding
  hot spot, and withstanding a voltage well above the one it works at. One can
  pass while the other fails, so each is reported separately.
- Screening at this class splits in two, and the split is the whole point.
  Some steps are owed by every delivered unit because they catch the defect
  that kills one piece — an insulation weakness, a mis-terminated winding.
  Others are drawn from a sample because they characterise the build rather
  than the piece. Reading a sample step as though it covered the lot, and
  running a per-unit step on a sample, are the same error in opposite
  directions.
- A sample is a count, not a gesture. The required number follows the lot size
  through a declared fraction, is floored at a minimum so a small lot is not
  screened by one piece, and can never exceed the lot itself.

## Workflow

1. Validate the screening and margin policy: the sample fraction, the minimum
   sample, the density and utilization ceilings, the insulation margin and the
   withstand multiple. A fraction above one, or a utilization ceiling looser
   than the class allows, is refused rather than used.
2. Validate the part identity and build basis — designation, supplier, build
   standard, its issue, the released-process flag and the acceptance-data
   flag — and name every reason the basis is not traceable before measuring
   anything.
3. Validate the delivery lot: its identifier, the lot size and the units
   actually delivered, refusing a delivery larger than the lot it came from.
4. Validate every winding, compute each current density and hold it to the
   ceiling, taking an exactly-met ceiling as admissible.
5. Compute the core flux utilization at the hot case against its ceiling, the
   insulation margin against the hot spot, and the withstand ratio against the
   working voltage, keeping every finding that applies rather than the first.
6. Size the sample-drawn screening from the lot, compare the units actually
   screened against it, and name each per-unit and each sample step the lot
   never ran, separately.
7. Report the identity, the lot, the margins, the screening gaps, the sample
   shortfall and a verdict: build basis not established, design margin not
   demonstrated, screening coverage shortfall, or magnetic meets class two.

## Pitfalls

- Accepting a drawing number as a build standard. Without the issue, the lot
  is traceable to a document rather than to a build, and the next lot to the
  same number will look identical on paper.
- Taking the saturation flux density from the room-temperature curve. Ferrite
  saturation falls with temperature, and a core checked cold can run into the
  knee exactly when the mission is hottest.
- Sizing a winding by wire gauge habit rather than by current density. A gauge
  comfortable in air is a different part in vacuum, where the only heat path
  out of the winding is conduction.
- Treating the sample as a formality and screening one unit. The sample is
  derived from the lot size and floored, because a single piece characterises
  the piece and nothing else.
- Counting a sample step as lot coverage. A turns-ratio check on four units
  says the build is right; it does not say the insulation on unit thirty-one
  is intact, and only the per-unit steps do.
- Loosening a ceiling to make a delivered lot close. The ceilings are inputs
  here; a lot closes by being rewound with more copper or a larger core, not
  by editing the policy it is measured against.
- Reading a partial delivery as a smaller lot. The sample was sized on the lot
  the units came from, so units arriving later inherit that screening instead
  of earning their own, and that is worth saying once on the acceptance.

## Behavior contract (gate 3)

The policy validation, identity and build-basis findings, lot validation,
sample sizing and shortfall, per-winding current density, hot-case flux
utilization, insulation margin and withstand ratio, the two-part screening
coverage and the overall acceptance verdict are exercised by the gate 3
contract test:
scripts/test_q6013_class_2_self_made_magnetics.py against
scripts/q6013_class_2_self_made_magnetics_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_2_self_made_magnetics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
