---
name: e2007-metallic-ground-plane-resistance
description: "Use when compute and cap the direct-current surface resistance of a metallic ground-plane placed under a unit on electromagnetic-compatibility test, per ECSS-E-ST-20-07C clause 5.2.3.2: derive sheet-resistance in milliohms-per-square from material resistivity corrected to the plane working-temperature and the conductive thickness, count the squares along the current-path, add welded, bolted, riveted and bond-strap joint resistances, reject a mating-face finish that is not conductive, compare the end-to-end path against the plane cap, derive the thinnest conductive plane that still meets the cap, and reconcile a measured reading against the computed one. Trigger: ecss, e-st-20-electrical-scope, metallic-ground-plane, dc-surface-resistance, sheet-resistance, milliohms-per-square, bond-strap-resistance, plane-thickness-sizing, emc-test-setup."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-metallic-ground-plane-resistance, metallic-ground-plane, dc-surface-resistance, sheet-resistance, milliohms-per-square, bond-strap-resistance, emc-test-setup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Metallic Ground-Plane Resistance (space-systems/ecss/e2007-metallic-ground-plane-resistance)

Use when the task is the metallic test ground-plane cap of
ECSS-E-ST-20-07C clause 5.2.3.2 -- showing that the direct-current
surface resistance of the plane a unit sits on during an
electromagnetic-compatibility test is low enough that the plane acts
as a reference rather than as a series impedance in the measurement.

## Domain quick reference

- The controlled quantity is sheet-resistance, expressed in milliohms
  per square: bulk resistivity divided by the conductive thickness of
  the plane. It is independent of how large a square is, which is why
  the cap can be written once and applied to any plane shape. The
  house cap this leaf applies is 0.1 milliohms per square.
- The end-to-end resistance of a current-path across the plane is the
  sheet-resistance multiplied by the number of squares along that
  path, where the square count is the path length divided by the path
  width. A long narrow run of the same plane is more resistive than a
  short wide one even though the sheet-resistance is identical.
- Resistivity is temperature dependent. A plane characterized on a
  cold bench and used in a hot chamber shifts by roughly four parts in
  a thousand per kelvin for aluminium and copper, so the working
  temperature is corrected from the twenty-degree value through the
  material's linear coefficient before any comparison is made.
- The plane is rarely one piece. Welded, bolted and riveted joints and
  every bond strap sit in series with the sheet contribution; this
  leaf applies a per-joint cap of 1.0 milliohms and an end-to-end
  path cap of 2.5 milliohms, and defaults an uncharacterized joint to
  a conservative value drawn from its kind.
- A surface finish decides whether the plane is reachable at all. A
  conversion coating or a plating adds a small contact penalty; an
  anodized, painted or primed mating face is not conductive and breaks
  the direct-current path however good the underlying metal is, so it
  is a major finding and not a penalty term.
- Inverting the cap gives the thinnest conductive plane that still
  meets it -- about 0.265 mm for aluminium and 0.168 mm for copper at
  room temperature. A plane that meets the cap with no margin over
  that minimum is flagged, because thickness tolerance and temperature
  both eat into it.
- A composite plane is out of scope here: it has to reproduce the
  surface-resistivity of the real installation per clause 5.2.3.3, and
  the overall arrangement is covered by clause 5.2.3.1.

## Workflow

1. Resolve the plane material and correct its bulk resistivity from
   the twenty-degree value to the plane working-temperature. Reject an
   uncategorized material, and reject a temperature at or below
   absolute zero or one that would drive the linear model to a
   non-physical resistivity.
2. Derive the sheet-resistance in milliohms per square from that
   resistivity and the conductive thickness, and compare it against
   the cap. Record the margin and the minimum conductive thickness the
   cap implies at that temperature.
3. Count the squares along the current-path from the path length and
   width, and multiply to get the sheet contribution of the run.
4. Resolve every joint in the chain -- measured resistance when it
   exists, otherwise the conservative default for its kind -- and flag
   any joint above the per-joint cap.
5. Resolve the mating-face finish. A non-conductive finish is a major
   finding; a conductive one contributes its contact penalty to the
   path total.
6. Sum the sheet contribution, the joint chain and the contact penalty
   and compare the total against the end-to-end path cap.
7. When a measured sheet-resistance exists, compare it against the
   computed value: a deviation beyond the reconciliation tolerance is
   a minor finding, and a measured value above the cap is a major one
   regardless of what the computation predicted.
8. Aggregate every finding. The plane is compliant when no major
   finding stands and clean only when the minor list is empty too.

## Pitfalls

- Comparing a point-to-point milliohm reading against a per-square cap
  -- the two differ by the square count of whatever path was probed,
  and a wide short path can read compliant while a long narrow one on
  the same plane does not.
- Taking the plane thickness from the drawing when the conductive
  layer is thinner than the panel -- the sheet-resistance follows the
  conductive cross-section, not the structural one.
- Reading a good bulk metal as a good reference through an anodized
  mating face -- the finish, not the metal, decides whether the
  current-path exists, and no thickness compensates for an insulating
  interface.
- Ignoring temperature because the plane is metal -- a hundred-kelvin
  rise adds over forty percent to aluminium resistivity, which turns a
  thin plane sitting just inside the cap into a violation.
- Accepting a measured value that disagrees with the computation
  because it happens to sit under the cap -- a large disagreement means
  the model or the measurement is wrong, and both are findings.
- Letting a boundary case fail on representation error -- a reading
  exactly at the reconciliation tolerance can evaluate a few units in
  the last place above it in binary, so the comparison absorbs that
  with a tolerance instead of the engineering cap being widened.

## Behavior contract (gate 3)

The resistivity-correction, sheet-resistance, square-count, joint
chain, surface-finish and measured-reconciliation logic is exercised
by the gate 3 contract test:
scripts/test_e2007_metallic_ground_plane_resistance.py against
scripts/e2007_metallic_ground_plane_resistance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_metallic_ground_plane_resistance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
