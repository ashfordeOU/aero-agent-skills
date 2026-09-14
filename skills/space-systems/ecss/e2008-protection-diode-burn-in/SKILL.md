---
name: e2008-protection-diode-burn-in
description: "Evaluate whether the burn-in applied to a protection diode qualification batch under ECSS-E-ST-20-08C clause 9.6.5 removes its early-life population or merely occupies an oven: derive the junction temperature the forward loading and the thermal path produce, size the Arrhenius acceleration that junction buys, convert the soak into equivalent operating hours, estimate the share of the infant-mortality population the run removes, confirm every declared early-life mechanism has a parameter watching it, and separate a cleaned batch from a lot whose failure count condemns the build. Use when planning or reviewing a protection diode burn-in before the qualification batch is accepted. Trigger: ecss, e-st-20-08c-clause-9-6-5, protection-diode-burn-in-loading, protection-diode-infant-mortality-screen, protection-diode-junction-temperature-limit, protection-diode-burn-in-equivalent-hours, protection-diode-lot-reject-limit."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-protection-diode-burn-in, protection-diode-burn-in-loading, protection-diode-infant-mortality-screen, protection-diode-junction-temperature-limit, protection-diode-burn-in-equivalent-hours, protection-diode-lot-reject-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Protection Diode Burn-in (space-systems/ecss/e2008-protection-diode-burn-in)

Use when the task is to plan or defend the operational loading applied
to a protection diode qualification batch under ECSS-E-ST-20-08C
clause 9.6.5 -- how hard, how long, watched through what, and whether
the batch that comes out has been cleaned or merely aged.

## Domain quick reference

- A batch leaving the line carries two populations. The main one fails
  late and slowly. A small early-life population carries a build defect
  -- a void under the die attach, a weak weld, a thin spot in the
  metallisation, a flaw in the junction passivation -- and reaches its
  failure within the first hours of operation, which on an array means
  the first hours of the mission.
- Burn-in moves those hours forward. That is the whole of its purpose:
  it does not improve a good diode, it finds the bad one while the
  batch is still on the ground and the cost of finding it is a part.
- The acceleration runs on the junction, not the oven. Case
  temperature plus the dissipated power across the thermal path is
  where the diode actually sits, and a run sized on the oven set point
  is sized on the wrong temperature.
- The same thermal path makes the ceiling real. A junction driven past
  its limit damages the batch the run was meant to clean, so more
  loading is not monotonically more screening.
- Duration alone says nothing. Duration multiplied by the acceleration
  factor gives equivalent operating hours, and that is the number the
  screening requirement is written against.
- Only a falling hazard describes an early-life population. A
  screening estimate built on a shape parameter at or above one is
  describing wear-out, and a run sized on it consumes life instead of
  removing defects.
- Every declared mechanism surfaces in one measurable parameter. A
  mechanism with nothing watching it survives the run untouched
  however long the run was, and the batch certificate will not say so.
- Failures during burn-in are the exercise working. A batch that sheds
  more than a small share is a different finding: the build is in
  question, and the survivors do not inherit a clean sheet from it.

## Workflow

1. Validate the screening policy first: equivalent-hours floor,
   junction ceiling, acceleration floor, screening floor and lot reject
   limit. An acceleration floor below unity is refused rather than
   used, because it would accept a run slower than the mission.
2. Group the declared early-life mechanisms, rejecting an unrecognised
   one rather than ignoring it, and map each to the parameter it has to
   be read through.
3. Derive the dissipated power from the forward loading, then the
   junction temperature from the case temperature and the thermal
   resistance. Every later quantity is built on that junction figure.
4. Size the acceleration factor at that junction against the use
   temperature, and convert the soak into equivalent operating hours.
5. Estimate the share of the early-life population the run removes, and
   check it against the screening floor. A soak that reaches the hours
   floor can still leave most of the early-life population in place if
   the characteristic life is long.
6. Check monitoring coverage separately from loading: a run can be long
   enough, hot enough and blind at the same time.
7. Take the batch outcome last and compare the failure share against
   the reject limit. A share landing exactly on the limit is accepted;
   the comparison tolerance absorbs representation error and the limit
   does not move.
8. Close on one verdict: burn-in not planned, loading inadequate,
   monitoring blind, lot rejected, or early-life failures screened --
   reporting every inadequacy found, not only the first.

## Pitfalls

- Sizing the run on the oven set point. The junction sits above the
  case by the dissipated power across the thermal path, and on a diode
  under forward load that difference is tens of degrees.
- Quoting soak duration as the screening evidence. Hours in an oven at
  an unstated temperature buy nothing; equivalent operating hours are
  what the requirement is written in.
- Turning the loading up to buy margin. Past the junction ceiling the
  run introduces the defects it was meant to remove, and the batch
  arrives damaged with a certificate saying it was screened.
- Sizing the screened share with a wear-out shape parameter. A hazard
  that rises with time means the run is consuming life, so the number
  it produces is not a screened fraction at all.
- Declaring a mechanism and not measuring its parameter. The run is
  then long, hot and blind to exactly the defect it was justified by.
- Reading burn-in failures as a failed test. Removing those units is
  the purpose; the separate question is whether the batch shed so many
  that the build, rather than the individual parts, is what was found.
- Letting the survivors inherit the batch conclusion. A lot beyond the
  reject limit is a lot finding, and screening the rest of it does not
  answer it.

## Behavior contract (gate 3)

The policy validation, dissipated power, junction temperature,
Arrhenius acceleration factor, equivalent operating hours, the
early-life screened fraction and its falling-hazard guard, the lot
failure share, the mechanism inventory and parameter coverage, and the
burn-in verdict are exercised by the gate 3 contract test:
scripts/test_e2008_protection_diode_burn_in.py against
scripts/e2008_protection_diode_burn_in_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_protection_diode_burn_in.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
