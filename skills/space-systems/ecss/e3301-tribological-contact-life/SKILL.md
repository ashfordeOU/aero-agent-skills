---
name: e3301-tribological-contact-life
description: "Evaluate the wear and material-transfer life of a mechanism contact pair against its mission cycles under ECSS-E-ST-33-01C clause 4.7.3.4.1. Use when the task is accumulating the sliding distance the pair really sees, derating the wear coefficient to the worst-case vacuum, temperature and contamination combination instead of the nominal one, converting that into an Archard wear depth and comparing it with the tighter of the allowable depth and the remaining dry-film thickness, judging whether transfer-film starvation limits life before wear-through, and sizing the demonstration cycles the life factor demands. Trigger: ecss, e-st-33-01c, contact-pair-wear-life, archard-wear-depth, dry-film-coating-depletion, transfer-film-starvation, worst-case-wear-coefficient, mechanism-life-factor, sliding-distance-accumulation."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-tribological-contact-life, contact-pair-wear-life, archard-wear-depth, dry-film-coating-depletion, transfer-film-starvation, mechanism-life-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Tribological Contact-Pair Life (space-systems/ecss/e3301-tribological-contact-life)

Use when the task is the contact-pair life demonstration of ECSS-E-ST-33-01C
clause 4.7.3.4.1 — showing that a rubbing or rolling pair inside a mechanism
still works after the cycles the mission asks of it, with wear and material
transfer both accounted for, and with the conditions taken at their worst-case
combination rather than at the nominal design point.

## Domain quick reference

- Life is spent in sliding distance, not in cycles. A cycle number only
  becomes a life statement once the stroke and the number of passes the
  contact makes per cycle are attached to it, and a reciprocating contact
  makes two passes per cycle, not one.
- Ground testing, integration exercising and acceptance cycling come out of
  the same life budget as flight. A pair sized on flight cycles alone is
  under-sized by however much the ground programme spends.
- The wear coefficient of a space contact pair is a condition-dependent
  number, not a material constant. Vacuum removes the oxide repair mechanism,
  temperature moves the lubricant regime, particulate contamination turns a
  two-body contact into a three-body one, and long static dwell can cold-weld
  a pair that slides freely when exercised. The clause asks for the worst-case
  combination, so the derating factors multiply — they do not average.
- The Archard relation V = k*F*s/H turns that coefficient into a wear volume;
  spread over the apparent contact area it becomes a depth, which is the
  quantity a design limit and a bonded dry-film thickness are both written in.
- A self-lubricating pair has a second, independent life limit: the transfer
  film has to be replenished from a reservoir (a polymer cage, a bonded film,
  a sacrificial rider). When the reservoir is consumed, the pair starves long
  before the substrate is worn through, so the two limits are computed
  separately and the earlier one governs.
- A demonstration is not a one-for-one repeat of the mission. A life factor
  sits on top, and the test is only complete when the cycles actually run
  reach the factored number.

## Workflow

1. Validate the geometry and duty: stroke, passes per cycle, mission cycles
   and the ground cycles already spent. A non-integer cycle count or a
   non-positive stroke is an input error, not a case to be rounded.
2. Accumulate the total sliding distance and the distance spent per cycle;
   the second is what a transfer-film reservoir is divided by.
3. Derate the nominal wear coefficient by every declared worst-case condition
   factor. Refuse a factor below unity — a worst case cannot be milder than
   the nominal case — and refuse a condition name outside the known set rather
   than dropping it silently.
4. Compute the Archard wear volume from the derated coefficient, the contact
   load, the accumulated distance and the counterface hardness, then convert
   it to a wear depth over the apparent contact area.
5. Take the governing depth limit as the tighter of the allowable wear depth
   and any bonded coating thickness, and name which of the two governs so the
   reader knows whether the finding is a design allowance or a coating one.
6. Where a transfer film is relied on, convert the reservoir volume and the
   transfer rate into an available sliding distance and then into cycles, and
   compare that with the mission cycles.
7. Size the demonstration: the factored cycle count, and the ratio the cycles
   already run achieve against it.
8. Report the wear depth, the governing limit, the transfer-limited cycles,
   the life limiter and every finding, absorbing an exact equality at the
   depth limit with a named tolerance rather than by relaxing the limit.

## Pitfalls

- Counting cycles and calling it life. Two mechanisms with the same cycle
  count and different strokes spend different sliding distances, and it is the
  distance that wears the pair.
- Leaving the ground programme out of the budget. Qualification and acceptance
  cycling are real sliding distance; a life demonstration that ignores them
  overstates the flight margin by the whole ground count.
- Using the nominal wear coefficient because the worst-case conditions are
  unlikely to coincide. The clause asks for the combination, and the factors
  multiply; taking the largest single factor understates the derating.
- Comparing wear depth with the allowable depth while a bonded dry-film
  coating thinner than that allowance is doing the lubricating. The coating
  thickness is the real limit, and wearing through it changes the contact into
  an unlubricated one rather than merely losing a little material.
- Treating a self-lubricating pair as wear-limited only. Reservoir exhaustion
  is a separate and often earlier limit, and a pair that passes the wear-depth
  check can still starve inside the mission.
- Accepting a partial demonstration because the trend looks flat. The life
  factor is on the cycle count, not on the extrapolation, and cycles not run
  are not cycles demonstrated.
- Widening the allowable depth to make an exact-equality case pass. An
  equality at the limit is a representation question handled by the tolerance
  inside the comparison; the limit stays as specified.

## Behavior contract (gate 3)

The duty accumulation, worst-case coefficient derating, Archard volume and
depth conversion, governing-limit selection, transfer-film reservoir life and
demonstration sizing are exercised by the gate 3 contract test:
scripts/test_e3301_tribological_contact_life.py against
scripts/e3301_tribological_contact_life_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3301_tribological_contact_life.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
