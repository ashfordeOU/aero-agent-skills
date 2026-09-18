---
name: q6012-die-selection-detailed-requirements
description: "Evaluate one candidate microwave die against the detailed selection criteria of ECSS-Q-ST-60-12 clause 5.1.2. Use when a die has cleared the baseline rules and the design now has to prove it, criterion by criterion: grade gain, output power, noise figure and both return losses at the graded band edge, compare each bias rail with a derated rating rather than an absolute maximum, form the channel temperature from the dissipation and the junction-to-case path, project the Arrhenius life at that temperature against the mission life, and settle electrostatic-sensitivity and bond-pad compatibility. A missing mandatory datum is an open finding, never a pass. Trigger: ecss, q-st-60-12, mmic-die-detailed-criteria, die-bias-derating, die-channel-temperature, die-arrhenius-life-projection, die-band-edge-rf-margin, die-esd-sensitivity-category."
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
  tags: [ecss, q-st-60-microwave-die-scope, q6012-die-selection-detailed-requirements, mmic-die-detailed-criteria, die-bias-derating, die-channel-temperature, die-arrhenius-life-projection, die-esd-sensitivity-category]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Detailed Selection Criteria (space-systems/ecss/q6012-die-selection-detailed-requirements)

Use when the task is the parameter-by-parameter case of ECSS-Q-ST-60-12
clause 5.1.2 — the specific criteria one candidate microwave die has to meet
before the design commits to it, once the baseline rules of clause 5.1 have
already admitted it. Every criterion returns a signed margin and a verdict,
and the die is selectable only when none of them is short or blank.

## Domain quick reference

- The detailed case is graded at the worst point of the duty, not at the
  datasheet's nominal point. Gain, output power at compression, noise figure
  and both return losses are read at the band edge where they are weakest,
  because that is the point the equipment has to work at.
- A bias rail is never compared with the absolute maximum rating. The applied
  voltage and current are compared with the rating after the programme's
  derating factor has been applied, so the headroom the derating policy buys
  is preserved rather than spent.
- Thermal and reliability are one chain, not two criteria. The dissipation and
  the junction-to-case thermal resistance set the channel temperature; that
  temperature sets the derated thermal verdict and it is also the temperature
  the life projection is made at. Projecting life at the base-plate
  temperature instead of the channel temperature overstates life by orders of
  magnitude, because the Arrhenius exponent is steep.
- Handling criteria are pass or fail against a line capability, not a margin
  to be negotiated. A die more sensitive to electrostatic discharge than the
  assembly line can handle is not a die with a small risk; it is a die the
  line cannot mount. Bond-pad metallisation is graded the same way against
  the assembly route actually used.
- Evidence is a criterion in its own right. Screening level, lot-acceptance
  reference and process-monitor reference are either on record or they are
  open findings; an absent value is never read as a satisfied criterion.

## Workflow

1. Validate the die record and the design duty. A non-numeric parameter, a
   derating factor outside its interval, an unrecognised sensitivity category
   or assembly route, and a sub-absolute-zero temperature are input errors.
2. Grade the five radio-frequency criteria at the graded band edge, each as a
   signed margin against its requirement with the correct sense: gain, output
   power and both return losses are floors, noise figure is a ceiling.
3. Derate each bias rating, then compare the applied voltage and current with
   the derated limit. Absent ratings produce an evidence gap, not a pass.
4. Form the channel temperature as base temperature plus dissipation times
   junction-to-case resistance, and compare it with the rated channel limit
   less the thermal derating allowance.
5. Project the median life from the rated life, the rated temperature and the
   activation energy to that same channel temperature, and compare it with the
   life the equipment owes.
6. Settle the handling criteria: the die sensitivity category against the line
   capability, and the bond-pad routes against the assembly route in use.
7. Split the outcome three ways — criteria evaluated and short, mandatory
   criteria with no value on record, and evidence references missing — and
   report the die as selectable only when all three sets are empty.

## Pitfalls

- Grading the radio-frequency criteria at band centre because that is where
  the datasheet curve is prettiest. The equipment lives at the edges, and a
  centre-graded margin is a margin for a duty nobody flies.
- Comparing an applied rail with the absolute maximum rating. That silently
  spends the whole derating allowance and leaves nothing for the tolerance
  stack, the transient and the end-of-life drift the policy was sized for.
- Projecting life at the base-plate temperature. The Arrhenius exponent makes
  a forty-degree error a factor of tens in life, so the projection has to be
  made at the channel temperature the thermal step produced.
- Reading an absent parameter as a satisfied criterion. A blank noise figure
  is a die owing a measurement; recording it as a pass moves an open action
  into the design baseline where nobody will look for it again.
- Comparing a margin against its limit with a bare inequality. An exactly
  compliant rail or an exactly met return loss can land a unit in the last
  place short; absorb that in the comparison, never by relaxing the limit.

## Behavior contract (gate 3)

The temperature and derating arithmetic, criterion verdicts and their senses,
the Arrhenius life projection, the radio-frequency, bias, thermal, reliability
and handling criterion sets, the evidence gaps and the selectability rollup
are exercised by the gate 3 contract test:
scripts/test_q6012_die_selection_detailed_requirements.py against
scripts/q6012_die_selection_detailed_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_die_selection_detailed_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
