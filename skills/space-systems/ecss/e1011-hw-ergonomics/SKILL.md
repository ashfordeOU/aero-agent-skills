---
name: e1011-hw-ergonomics
description: "Use when you apply hardware ergonomics requirements to space system hardware items under ECSS-E-ST-10-11C §4.6.4: categorize each item as a control, display, handle, or maintenance access point; check controls against operating-force and torque limits with inadvertent-activation safeguards in mind; verify displays satisfy minimum and maximum character visual angle and minimum contrast ratio thresholds; confirm handles provide adequate grip clearance and stay within one-hand or two-hand payload limits; and validate maintenance access openings against task-type minimum diameters. Flag each non-conformance with the specific limit exceeded so that the design can be corrected before the human factors engineering review. Trigger: ecss, e-st-10-11c, e-st-10-system-scope, hardware-ergonomics, controls, displays, handles, maintainability, human-factors."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-11c, hardware-ergonomics, controls, displays, handles, maintainability, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — Hardware Ergonomics (space-systems/ecss/e1011-hw-ergonomics)

Use when the task is applying hardware ergonomics requirements to
space system hardware items under ECSS-E-ST-10-11C §4.6.4 --
categorizing each item into one of the four ergonomics families
(control, display, handle, maintenance access point), evaluating it
against quantitative limits, and producing a finding for every
exceedance so the design can be corrected before the human factors
engineering review.

## Domain quick reference

- §4.6.4 addresses four hardware families. A **control** (push-button,
  toggle switch, rocker switch, rotary knob, foot pedal, keyboard key)
  must not demand an operating force or torque that exceeds the limit
  for its type; limits range from approximately 3 N for keyboard keys
  to 111 N for single-hand grip controls. A control that can be
  activated inadvertently by a gloved hand or floating debris must
  carry a guard or recessed mounting.
- A **display** must present alphanumeric characters at a visual angle
  between 20 arcmin and 80 arcmin so characters are legible without
  magnification and without being uncomfortably large; the luminance
  contrast ratio between character and background must be at least 3:1.
- A **handle** used to move, install, or restrain equipment must be
  sized so the grip clearance (the space between the grip surface and
  any adjacent structure) is at least 38 mm; the payload the handle
  is designed for must not exceed 111 N for a single-hand grip or
  222 N for a two-hand grip, unless a supplementary mechanical aid is
  provided.
- A **maintenance access point** must provide an opening at least as
  large as the minimum diameter for the task performed through it:
  38 mm for a finger, 102 mm for a one-hand reach, 152 mm for a
  two-hand reach, and 455 mm for a head-and-shoulders entry.
- Items that belong to more than one family (e.g., a handle that is
  also a control) are reviewed under each applicable family, and all
  findings are reported.

## Workflow

1. Inventory every hardware item subject to §4.6.4 and assign each to
   its ergonomics family: control, display, handle, or access_point.
   Reject an item whose type does not match a known family before it
   enters the check.
2. For each **control**, identify the control type and record its
   operating force or torque value (measured or from the design
   datasheet). Apply `check_control_force_limit`; flag any exceedance
   with the control type, the measured value, and the applicable limit.
   Separately note whether the control's location and mounting prevent
   inadvertent activation.
3. For each **display**, record the character visual angle at the
   design viewing distance and the contrast ratio from the display
   specification. Apply `check_display_visual_angle` and
   `check_display_contrast`; flag any angle outside the 20–80 arcmin
   band and any contrast ratio below 3:1.
4. For each **handle**, record the payload the handle is rated for,
   the intended grip mode (one-hand or two-hand), and the grip
   clearance from the design drawing. Apply `check_handle_requirements`;
   flag a payload that exceeds the grip-mode limit and a clearance
   below 38 mm.
5. For each **maintenance access point**, record the task type
   performed through the opening and the opening diameter. Apply
   `check_maintenance_access`; flag any opening below the task-type
   minimum diameter.
6. Aggregate all findings per item using `hw_ergonomics_review`; the
   item is conformant under §4.6.4 only when `is_hw_ergonomics_compliant`
   returns True (findings list is empty).

## Pitfalls

- Applying the one-hand payload limit to a two-hand handle and vice
  versa -- the limits differ by a factor of two and the grip mode must
  be determined from the design intent, not assumed.
- Checking only the minimum visual angle without checking the maximum
  -- characters set at 90 arcmin may be technically legible but impose
  excessive head movement and fail the upper bound of the ergonomics
  band.
- Treating a missing grip-clearance measurement as a pass -- an
  unrecorded clearance is a data gap, not evidence of compliance;
  require the measurement before closing the finding.
- Omitting the inadvertent-activation review for controls that pass
  force limit checks -- a push-button may be within its force limit
  yet still require a guard if it sits in a crew traffic path.
- Conflating the access-opening diameter with the access envelope --
  the minimum diameter is measured at the narrowest cross-section of
  the opening, not at the outer frame.

## Behavior contract (gate 3)

The item-categorization, force-limit, display-parameter, handle, and
maintenance-access logic is exercised by the gate 3 contract test:
scripts/test_e1011_hw_ergonomics.py against
scripts/e1011_hw_ergonomics_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_hw_ergonomics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
