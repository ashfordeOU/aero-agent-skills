---
name: e2008-measurement-equipment-set-up
description: "Prepare the equipment arrangement the second cell measurement method of ECSS-E-ST-20-08C clause 11 is run from, per clause 11.2.2: confirm the bias supply, excitation source, guarded four-terminal fixture, transient recorder, single-point ground and temperature stage are present, size the supply range and resolution against the sweep, the sample count and one recorder bit against the response, the fixture stray against the cell and the stage against the reference temperature, then hold every instrument inside its calibration interval and assemble the chain ground first, power last. Use when a cell measurement is about to start on a bench nobody characterised. Trigger: ecss, e-st-20-08c-clause-11-2-2, cell-measurement-equipment-set-up, guarded-cell-fixture-stray-share, transient-recorder-sampling-adequacy, single-point-ground-bonding-order, bias-supply-range-and-resolution, instrument-calibration-interval-validity."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-measurement-equipment-set-up, cell-measurement-equipment-set-up, guarded-cell-fixture-stray-share, transient-recorder-sampling-adequacy, single-point-ground-bonding-order, bias-supply-range-and-resolution, instrument-calibration-interval-validity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Measurement Equipment Set-Up (space-systems/ecss/e2008-measurement-equipment-set-up)

Use when the task is clause 11.2.2 of ECSS-E-ST-20-08C -- arranging the
measurement equipment before the second cell measurement method of
clause 11 is run, rather than discovering afterwards that the bench
contributed more to the result than the cell did.

The clause exists because the arrangement is part of the method. A cell
is a small, lightly driven article: the fixture stray sits in parallel
with it, the lead resistance sits in series with it, the recorder
quantises whatever survives, and the ground path decides how much of the
room joins the reading. None of that is recoverable in post-processing,
because every one of those contributions is a bias in the same direction
on every repeat, and no amount of averaging reveals a bias.

## Domain quick reference

- Six stations make the arrangement: the bias supply, the excitation
  source the second method drives with, a guarded four-terminal cell
  fixture, a transient recorder, a shield brought to one ground point,
  and a temperature stage. An absent station is not a degraded set-up,
  it is a different measurement.
- The bias supply is characterised by two numbers, not one. Its range
  has to span the bias the method sweeps, and its resolution has to be
  fine against the smallest step the sweep asks for, or the sweep
  cannot place the points it was designed around.
- The recorder has a horizontal and a vertical adequacy, and they fail
  separately. Roughly twenty samples across the response is the
  horizontal floor; one least significant bit staying under about a
  hundredth of the expected signal is the vertical one.
- A four-terminal, guarded fixture is what separates the cell from its
  leads. Two-terminal mounting puts the lead resistance in the result,
  and an unguarded one puts the harness capacitance there.
- Open and short compensation is a prerequisite rather than a
  correction applied later. It is what makes the fixture stray a known
  quantity instead of an unknown one folded into the cell.
- A single ground point is the difference between measuring the cell
  and measuring the loop the cabling encloses. Ground is bonded before
  anything else so that no station is ever referenced through a signal
  lead.
- The result is quoted at a reference temperature, so the stage holding
  the cell within a couple of kelvin of it is part of the arrangement,
  not an environmental nicety.
- Calibration is a property of the arrangement on the day. An
  instrument past its interval makes every number it produced
  unquotable, however well the rest of the bench was built.

## Workflow

1. Take the declared chain and refuse an invented station or a station
   with no settings. An arrangement that cannot be named cannot be
   assessed.
2. Name the stations still absent before assessing any of the ones
   present, since a missing ground or fixture makes the rest moot.
3. Size the bias supply twice: span against the sweep, resolution
   against the smallest step.
4. Size the recorder twice: samples across the response, and one bit
   against the expected signal.
5. Size the fixture stray against the cell capacitance, and require the
   mount to be four-terminal and already compensated.
6. Confirm the shield is brought to a single point and the stage sits
   inside the band around the reference temperature.
7. Sweep every station for a calibration interval that has run out.
8. Compare the proposed assembly order against the canonical one,
   holding ground first and the bias supply energised last. The
   arrangement stays not-ready while any finding stands.

## Pitfalls

- Treating the set-up as a preamble and starting the run to save bench
  time. Every contribution the arrangement makes is a one-directional
  bias, so the repeat that would reveal a random error reveals nothing
  at all here.
- Quoting the supply range and ignoring its resolution. A supply that
  reaches the end of the sweep in steps coarser than the sweep asks for
  places the points somewhere other than where the method put them.
- Choosing the recorder on sample rate alone. A fast recorder with a
  coarse vertical scale turns a small cell response into a staircase,
  and the staircase fits smoothly.
- Setting the recorder full scale from the supply rather than from the
  expected signal. The bit size is what matters, and a full scale
  chosen for headroom throws most of the bits away.
- Mounting the cell two-terminal because the leads are short. Short
  leads still carry the contact resistance, and on a lightly driven
  cell that is not a small term.
- Bonding ground last, after the fixture and the recorder are already
  connected. Until the bond exists, every station is referenced through
  whatever signal lead happens to be lowest impedance.
- Energising the bias supply before the chain is complete, so that the
  last connection is made to a live article.
- Comparing a derived sample count, stray share or temperature
  deviation against a written limit by bare arithmetic. Each is a
  product or difference of floats that can land a few units in the last
  place either side of the limit, so the comparison absorbs that error
  while the limit itself is never relaxed.

## Behavior contract (gate 3)

The station completeness check, bias supply span and resolution share,
samples across the response, recorder quantisation share, fixture stray
fraction with the four-terminal and compensation conditions,
single-point ground, stage temperature deviation, calibration interval
sweep and the canonical ground-first power-last assembly order are
exercised by the gate 3 contract test:
scripts/test_e2008_measurement_equipment_set_up.py against
scripts/e2008_measurement_equipment_set_up_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_measurement_equipment_set_up.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
