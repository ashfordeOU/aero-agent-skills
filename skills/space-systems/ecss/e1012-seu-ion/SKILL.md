---
name: e1012-seu-ion
description: "Use when calculating heavy-ion-induced single-event upset (SEU), multiple-cell upset (MCU), and single-word multiple-bit upset (SMU) rates for a space-qualified device under ECSS-E-ST-10-12C §9.4.1.2: fit the device cross-section versus LET curve with a Weibull model (LETth, W, s, σsat), integrate over the mission LET spectrum using the rectangular parallelepiped (RPP) method, optionally apply the integral RPP (IRPP) chord-length correction for sensitive-volume geometry, derive MCU and SMU rates from upset multiplicity and same-word fractions, and verify the predicted rate meets the system requirement with a 10× design margin. Trigger: ecss, e-st-10-12c, e-st-10-system-scope, seu, mcu, smu, heavy-ion, let-spectrum, rpp, irpp, weibull."
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
  tags: [ecss, e-st-10-12c, e-st-10-system-scope, seu, mcu, smu, heavy-ion, let-spectrum, rpp, irpp]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Heavy-Ion SEU/MCU/SMU Rate Prediction (space-systems/ecss/e1012-seu-ion)

Use when the task is predicting heavy-ion-induced single-event upset (SEU),
multiple-cell upset (MCU), and single-word multiple-bit upset (SMU) rates for
a device destined for a radiation environment, following the procedure in
ECSS-E-ST-10-12C §9.4.1.2 using the RPP and IRPP methods with a mission
LET spectrum.

## Domain quick reference

- A **Single-Event Upset (SEU)** is the inversion of a single stored bit caused
  by a heavy ion or cosmic-ray nucleus depositing charge above the device
  threshold as it traverses the sensitive volume.
- A **Multiple-Cell Upset (MCU)** occurs when one particle flips bits in more
  than one memory cell across different logical words. A **Single-word Multiple-
  bit Upset (SMU)** is the special case where all flipped bits belong to the
  same logical word; SMUs are more critical because standard single-bit error
  correction (EDAC) cannot correct them.
- The **LET threshold (LETth)** is the minimum linear energy transfer
  (MeV·cm²/mg) at which the device can be upset. Heavy ions with LET below
  LETth produce no upsets. The **saturated cross-section (σsat)** is the
  device's maximum upset cross-section area (cm²/device) reached at high LET.
- The **Weibull fit** describes how the cross-section rises from zero at LETth
  to σsat: σ(LET) = σsat × (1 − exp(−((LET − LETth)/W)^s)), where W is the
  width parameter and s is the shape exponent, both determined by fitting to
  heavy-ion test data.
- The **RPP (Rectangular Parallelepiped) method** computes the upset rate by
  numerically integrating σ(LET) × φ(LET) over the differential LET spectrum
  φ(LET) (ions/cm²/s per MeV·cm²/mg). The **IRPP** method extends RPP by
  applying a chord-length correction that accounts for the distribution of
  track lengths through the actual sensitive volume geometry, producing a more
  accurate effective LET for oblique incidence.
- The mission LET spectrum (GCR + trapped heavy ions at the shielded location)
  must span from below LETth to well above the Weibull saturation region for
  the integral to be accurate.

## Workflow

1. Obtain Weibull parameters (LETth, W, s, σsat) from the device's heavy-ion
   characterisation test report. Confirm that LETth > 0 and that the test LET
   range covers saturation (σ ≥ 0.99 σsat at the highest test point), then
   record the MCU fraction (fraction of upsets affecting more than one cell) and
   SMU fraction (fraction of MCU events where all upset bits share a word).

2. Obtain the differential heavy-ion LET spectrum for the shielded device
   location and mission duration. Verify that the spectrum maximum exceeds LETth;
   if it does not, the device cannot be upset by heavy ions in this environment
   and the predicted rate is zero — record this as an environment-limited result,
   not a device result.

3. Evaluate the Weibull cross-section at each LET point in the spectrum. For
   LET ≤ LETth, the cross-section is zero; for LET > LETth, apply the Weibull
   formula. Do not extrapolate the cross-section above σsat.

4. **RPP rate**: integrate σ(LET) × φ(LET) over LET using the trapezoidal rule
   across all spectrum points. The result is the SEU rate in upsets/device/s;
   convert to upsets/device/day by multiplying by 86 400.

5. **IRPP correction** (apply when RPP is deemed too conservative or when the
   sensitive volume geometry is well characterised): compute the mean chord
   length of the RPP sensitive volume via the Cauchy formula (4V/A), then scale
   the incident LET by the ratio of sensitive-volume depth to mean chord length
   to obtain the isotropic-equivalent LET used in the cross-section evaluation.
   Repeat step 4 with the corrected LET values.

6. Derive MCU and SMU rates from the SEU rate: MCU rate = SEU rate × MCU
   fraction; SMU rate = MCU rate × SMU fraction. For EDAC coverage assessment,
   the SMU rate is the uncorrectable upset rate.

7. Compare the predicted SEU rate (and SMU rate if EDAC is implemented) against
   the system requirement. A 10× design margin is standard: the predicted rate
   must be no greater than one-tenth of the requirement value. Flag any
   exceedance and flag any case where the margin is less than 10× even if the
   rate passes the requirement numerically.

8. Document all inputs (Weibull parameters, spectrum source, shielding
   thickness), the method applied (RPP or IRPP), the computed rates, and the
   margin result. Any assumption made when test data are incomplete (e.g.,
   extrapolating σsat from a partial curve) must be called out explicitly.

## Pitfalls

- Applying a flat worst-case cross-section equal to σsat across all LET bins
  instead of using the Weibull shape — this overstates the rate at low LET and
  can produce results that are orders of magnitude too conservative, masking
  the real design margin.
- Ignoring the LET threshold check: if the spectrum maximum is below LETth,
  no integration is needed — the rate is zero by physics, not a numerical
  artifact. Failing to record this explicitly can lead a reviewer to assume
  the calculation was skipped.
- Treating MCU and SEU as interchangeable: when EDAC corrects SEUs but not
  SMUs, the relevant rate for the reliability budget is the SMU rate, not the
  total SEU rate.
- Using an unshielded GCR spectrum at the device location when the device sits
  behind several millimetres of aluminium — shielding attenuates low-LET ions
  and modifies the spectral shape; always use the shielded spectrum computed
  for the actual location.
- Failing to verify that the Weibull fit saturates within the test data range:
  a fit that has not reached saturation contains an unconstrained σsat and can
  produce large errors at high LET.

## Behavior contract (gate 3)

The Weibull cross-section, RPP integration, IRPP chord-length correction, MCU/
SMU rate derivation, margin assessment, and upset-type categorization logic are
exercised by the gate 3 contract test: scripts/test_e1012_seu_ion.py against
scripts/e1012_seu_ion_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_seu_ion.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the standard and clause
  as anchor only — no verbatim reproduction.
- compliance: STANDARDS-REF, gated: false.
