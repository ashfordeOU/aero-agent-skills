---
name: liquid-penetrant-inspection
description: "Use when you must plan and execute a liquid penetrant inspection (PT) of an aerospace part and turn penetrant behavior into inspection decisions: compute the capillary pressure and capillary rise that pull the penetrant into a surface-breaking crack, apply the Washburn equation to estimate penetration depth during the dwell time, size the dwell time that fills a crack of a given width and depth, convert crack opening width to effective capillary radius, and relate bleed-out indication width to the actual flaw width for indication sizing. Produces the penetration depth, dwell time, and bleed-out ratio that gate liquid penetrant acceptance dispositions. Trigger: liquid penetrant, penetrant testing, dye penetrant, fluorescent penetrant, dwell time, developer time, capillary action, washburn, bleed out, indication width, surface crack."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
  - id: nas-410
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [liquid-penetrant-inspection, penetrant-testing, dye-penetrant, fluorescent-penetrant, capillary-action, capillary-rise, washburn-equation, dwell-time, developer-time, bleed-out, indication-sizing, penetration-depth, contact-angle, surface-tension, crack-width, sensitivity-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# Liquid Penetrant Inspection (manufacturing-quality/ndt/liquid-penetrant-inspection)

Use when the task is executing liquid penetrant inspection (PT) on a
part: computing the capillary pressure and rise that pull the
penetrant into a surface-breaking crack, applying the Washburn
equation to estimate how deep the penetrant reaches during the dwell
time, sizing the dwell time for a crack of given width and depth, and
sizing indications from the bleed-out of excess penetrant under the
developer.

## Domain quick reference

- Capillary pressure: P = 2 * gamma * cos(theta) / r, with gamma the
  surface tension in N/m, theta the contact angle in degrees, and r the
  effective capillary radius in meters. This pressure difference drives
  the penetrant into the crack; a tighter crack gives a higher driving
  pressure, which is why penetrant finds tight fatigue cracks.
- Capillary rise: h = 2 * gamma * cos(theta) / (rho * g * r), the
  height at which the hydrostatic head balances the capillary pressure
  in a vertical crack. Water in a 0.5 mm tube rises about 5.9 cm.
- Washburn penetration: L = sqrt(r * gamma * cos(theta) * t / (2 * eta)),
  with eta the penetrant viscosity in Pa.s and t the dwell time in
  seconds. Depth grows as the square root of time, so doubling the
  dwell time multiplies the penetration by sqrt(2), about 1.41.
- Dwell time sizing: t = 2 * eta * L^2 / (r * gamma * cos(theta)),
  the inverse of the Washburn equation. Dwell time scales with the
  square of the depth and inversely with the capillary radius, so a
  crack twice as deep needs four times the dwell and a crack with half
  the radius needs twice the dwell.
- Penetration rate: dL/dt = r * gamma * cos(theta) / (4 * eta * L).
  The front slows as it advances, so most penetration happens early in
  the dwell time.
- Crack width to radius: a slit crack of opening width w behaves as a
  capillary of radius r = w / 2.
- Bleed-out: the developer draws excess penetrant out of the flaw, so
  the visible indication is wider than the actual opening. Tight cracks
  typically bleed out 3 to 5 times their opening width, and the
  bleed-out ratio (indication width over flaw width) converts a
  measured indication to an implied flaw size.
- Developer coverage: developer mass = area * areal density, with dry
  developer typically applied at 0.1 to 0.2 kg/m2 of part surface.
- Contrast: contrast ratio = abs(bg - ind) / max(bg, ind), near 1 for
  a bright fluorescent indication on a dark background or a dark dye
  indication on a white developer background, near 0 when the
  indication is indistinguishable from the background.
- Acceptance: indications are compared with reference standards and the
  engineering specification, recorded, and dispositioned under
  special-process control by NAS 410 qualified personnel. The penetrant
  process (penetrant, dwell time, developer, removal method) must match
  the qualified procedure for the sensitivity level required.

## Workflow

1. Establish the penetrant system: surface tension gamma in N/m,
   viscosity eta in Pa.s, and contact angle theta in degrees (below 90
   degrees, the wetting condition for capillary pull).
2. Convert the crack opening width to an effective capillary radius
   with crack_radius_from_width (radius = width / 2).
3. Compute the capillary pressure with capillary_pressure to confirm
   the penetrant can enter the crack, and the capillary rise with
   capillary_rise_height where the crack is vertical.
4. Size the dwell time with dwell_time_for_depth for the crack depth,
   radius, and penetrant properties, then confirm the penetration with
   washburn_penetration_depth over that dwell time and with
   penetration_rate at the target depth.
5. After development, measure the indication width and convert it to an
   implied flaw width with bleed_out_ratio and bleed_out_width; check
   the contrast ratio with contrast_ratio to confirm the indication is
   visible above the background.
6. Compare the indication with the acceptance criteria in the
   engineering specification, record the results, and disposition the
   part.

## Pitfalls

- Using a non-wetting penetrant: a contact angle at or above 90
  degrees gives zero or negative capillary pull and the penetrant never
  enters the crack; the wetting condition theta below 90 degrees is
  enforced by the math.
- Forgetting the sqrt scaling of the Washburn equation: doubling the
  dwell time does not double the penetration, it multiplies it by
  sqrt(2), so a shallow indication after a short dwell needs a much
  longer dwell, not a marginally longer one.
- Treating dwell time as linear in depth: dwell scales with depth
  squared, so a 2 mm crack needs four times the dwell of a 1 mm crack
  at the same radius.
- Sizing the flaw as the indication width: the bleed-out makes the
  indication 3 to 5 times wider than the opening; dividing by the
  bleed-out factor recovers the implied flaw size.
- Ignoring viscosity: a thick penetrant at a cold temperature takes far
  longer to fill the same crack, since dwell time scales linearly with
  viscosity.
- Skipping the developer step in the math: the indication only appears
  after the developer draws the penetrant back out; the bleed-out
  width, not the penetration depth, is what the inspector sizes.
- Reading a low-contrast smear as an indication: a contrast ratio near
  0 means the mark is indistinguishable from the background and is
  background bleed, not a flaw.
- Skipping procedure qualification: PT results are dispositioned under
  special-process control with NAS 410 qualified personnel, and the
  penetrant materials, dwell time, and developer must match the
  qualified procedure for the required sensitivity level.

## Behavior contract (gate 3)

The inspection math is exercised by the gate 3 contract test:
scripts/test_liquid_penetrant_inspection.py against
scripts/liquid_penetrant_inspection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_liquid_penetrant_inspection.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.5.1.3 frames
  NDT as a special process requiring controlled procedures and
  qualified personnel, and NAS 410 sets the qualification and
  certification requirements for the NDT personnel who execute liquid
  penetrant inspection; the capillary, Washburn, and bleed-out
  calculations above are common PT methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
