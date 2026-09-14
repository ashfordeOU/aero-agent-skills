"""Coverglass proton irradiation: reaching the coating and the glass under it.

Anchor: ECSS-E-ST-20-08C clause 8.7.14 (accelerated ageing of a coverglass
under proton bombardment, covering both the glass substrate and the coatings
on it). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Turn each energy line of the exposure matrix into a stopping depth in the
   coverglass. A proton does not pass through and leave a trail the way an
   electron does; it stops, and where it stops is where its damage lands.
2. Group each line by where it stopped -- inside the coating, inside the glass
   beneath it, or clean through and out the back -- since that is the only
   thing that decides which part of the article that line actually aged.
3. Refuse a matrix that leaves either the coating or the substrate unexposed.
   The clause covers both, and a matrix of megaelectronvolt lines ages the
   glass while the coating it has to see through is never touched.
4. Report a line that crosses the whole coverglass. It deposits its damage in
   whatever sits behind the glass, so it belongs in the cell's exposure record
   rather than in the coverglass darkening figure.
5. Divide each line's fluence by its beam-on time and hold the flux under the
   cap, because a proton beam delivered too fast heats and charges an
   insulating coverglass rather than ageing it.
6. Turn each line's post-exposure band transmittance into an optical density
   against the unirradiated scan of the same specimen.
7. Add the per-line densities into one darkening figure per band. Damage adds
   in density, so a spectrum flown as separate lines superposes there and
   nowhere else.
8. Convert the combined density back into a transmittance and judge it against
   what the array power budget requires.
9. Report depths, grouping, densities, the combined figure, findings and the
   verdict; the run is conformant only with no finding.
"""

import math

__all__ = [
    "BANDS",
    "ZONES",
    "REQUIRED_ZONES",
    "TOLERANCE",
    "DENSITY_NOISE_ALLOWANCE",
    "MAX_FLUX_P_PER_CM2_S",
    "RANGE_COEFFICIENT_UM",
    "RANGE_EXPONENT",
    "proton_range_um",
    "deposition_zone",
    "validate_energy_lines",
    "zone_coverage",
    "coverage_findings",
    "beam_flux",
    "flux_findings",
    "optical_density",
    "line_densities",
    "brightening_findings",
    "combined_density",
    "transmittance_after",
    "assess_coverglass_proton_irradiation",
]

# The bands the coverglass optics are read on.
BANDS = ("ultraviolet", "visible", "near-infrared")

# Where a line's protons came to rest.
ZONES = ("coating", "substrate", "beyond")

# The clause covers the glass and the coatings on it, so both must be reached.
REQUIRED_ZONES = ("coating", "substrate")

# A value sitting exactly on a declared bound is conformant; the comparison
# absorbs representation error and the bound itself never moves.
TOLERANCE = 1e-9

# A per-line density may sit this far below zero before the specimen is
# reading brighter than it started rather than merely noisy.
DENSITY_NOISE_ALLOWANCE = 0.0005

# Above this flux the beam heats and charges the glass instead of ageing it.
MAX_FLUX_P_PER_CM2_S = 1.0e9

# Empirical range law for protons in a fused-silica-like coverglass: the depth
# in micrometres at one megaelectronvolt, and the power the energy is raised
# to. Override both for a doped or a markedly denser glass.
RANGE_COEFFICIENT_UM = 11.0
RANGE_EXPONENT = 1.72


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _name(value, label):
    """Return a trimmed, non-empty identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("%s must not be empty" % label)
    return cleaned


def _band(value):
    """Return a validated optical band name."""
    name = _name(value, "band")
    if name not in BANDS:
        raise ValueError(
            "band must be one of %s, got '%s'" % (", ".join(BANDS), name)
        )
    return name


def _transmittance(value, label):
    """Return a transmittance as a fraction above zero and at most one."""
    number = _positive(value, label)
    if number > 1.0 + TOLERANCE:
        raise ValueError(
            "%s must be a fraction at or below one, got %g" % (label, number)
        )
    return min(number, 1.0)


def _scan(mapping, label):
    """Return a validated mapping of every band to a transmittance."""
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping of band to transmittance" % label)
    for key in mapping:
        _band(key)
    result = {}
    for key in BANDS:
        if key not in mapping:
            raise ValueError("%s is missing the '%s' band" % (label, key))
        result[key] = _transmittance(mapping[key], "%s '%s'" % (label, key))
    return result


def proton_range_um(energy_mev, coefficient_um=RANGE_COEFFICIENT_UM,
                    exponent=RANGE_EXPONENT):
    """Return the depth at which a proton of this energy comes to rest."""
    energy = _positive(energy_mev, "energy_mev")
    coefficient = _positive(coefficient_um, "coefficient_um")
    power = _positive(exponent, "exponent")
    return coefficient * math.pow(energy, power)


def deposition_zone(energy_mev, coating_thickness_um, glass_thickness_um,
                    coefficient_um=RANGE_COEFFICIENT_UM,
                    exponent=RANGE_EXPONENT):
    """Return where in the coverglass a given energy line comes to rest."""
    coating = _positive(coating_thickness_um, "coating_thickness_um")
    glass = _positive(glass_thickness_um, "glass_thickness_um")
    depth = proton_range_um(energy_mev, coefficient_um, exponent)
    if depth <= coating + TOLERANCE:
        return "coating"
    if depth <= coating + glass + TOLERANCE:
        return "substrate"
    return "beyond"


def validate_energy_lines(energies):
    """Return the validated, strictly rising set of exposure energies."""
    if not isinstance(energies, (list, tuple)) or len(energies) < 2:
        raise ValueError(
            "the matrix needs at least two energy lines to reach both layers"
        )
    lines = [_positive(value, "energy_mev") for value in energies]
    for earlier, later in zip(lines, lines[1:]):
        if later <= earlier:
            raise ValueError(
                "energy lines must strictly rise, got %g after %g"
                % (later, earlier)
            )
    return lines


def zone_coverage(energies, coating_thickness_um, glass_thickness_um,
                  coefficient_um=RANGE_COEFFICIENT_UM,
                  exponent=RANGE_EXPONENT):
    """Return the energy lines grouped by where their protons stopped."""
    lines = validate_energy_lines(energies)
    coverage = {zone: [] for zone in ZONES}
    for energy in lines:
        zone = deposition_zone(
            energy, coating_thickness_um, glass_thickness_um,
            coefficient_um, exponent,
        )
        coverage[zone].append(energy)
    return coverage


def coverage_findings(coverage):
    """Return findings where the matrix misses a layer or overshoots it."""
    if not isinstance(coverage, dict):
        raise ValueError("coverage must be a mapping of zone to energy lines")
    for key in coverage:
        if key not in ZONES:
            raise ValueError(
                "zone must be one of %s, got '%s'" % (", ".join(ZONES), key)
            )
    for zone in ZONES:
        if zone not in coverage:
            raise ValueError("coverage is missing the '%s' zone" % zone)
        if not isinstance(coverage[zone], (list, tuple)):
            raise ValueError("coverage '%s' must list its energy lines" % zone)
    findings = []
    for zone in REQUIRED_ZONES:
        if not coverage[zone]:
            findings.append(
                "no energy line stops in the %s, so the clause's %s is never "
                "aged by this matrix" % (zone, zone)
            )
    for energy in coverage["beyond"]:
        findings.append(
            "the %g MeV line crosses the whole coverglass, so its damage lands "
            "behind the glass rather than in it" % _positive(energy, "energy_mev")
        )
    return findings


def beam_flux(fluence_p_per_cm2, duration_s):
    """Return the delivered proton flux of one energy line."""
    fluence = _positive(fluence_p_per_cm2, "fluence_p_per_cm2")
    duration = _positive(duration_s, "duration_s")
    return fluence / duration


def flux_findings(label, fluence_p_per_cm2, duration_s,
                  max_flux=MAX_FLUX_P_PER_CM2_S):
    """Return findings where a line was delivered faster than the cap."""
    tag = _name(label, "label")
    cap = _positive(max_flux, "max_flux")
    flux = beam_flux(fluence_p_per_cm2, duration_s)
    if flux > cap + TOLERANCE:
        return [
            "line '%s' ran at %.3g p/cm2/s against the %.3g p/cm2/s cap, fast "
            "enough to heat and charge the glass rather than age it"
            % (tag, flux, cap)
        ]
    return []


def optical_density(transmittance, reference_transmittance):
    """Return the darkening of one reading against the unirradiated scan."""
    measured = _transmittance(transmittance, "transmittance")
    base = _transmittance(reference_transmittance, "reference_transmittance")
    return -math.log10(measured / base)


def line_densities(reference_scan, line_scans):
    """Return each band's optical density for every energy line."""
    base = _scan(reference_scan, "reference_scan")
    if not isinstance(line_scans, (list, tuple)) or not line_scans:
        raise ValueError("line_scans must be a non-empty sequence of scans")
    series = {key: [] for key in BANDS}
    for index, scan in enumerate(line_scans):
        values = _scan(scan, "line %d scan" % (index + 1))
        for key in BANDS:
            series[key].append(optical_density(values[key], base[key]))
    return series


def brightening_findings(band, energies, densities,
                         noise_allowance=DENSITY_NOISE_ALLOWANCE):
    """Return findings where a line left its specimen clearer than it began."""
    name = _band(band)
    lines = validate_energy_lines(energies)
    if not isinstance(densities, (list, tuple)) or len(densities) != len(lines):
        raise ValueError("one optical density is needed per energy line")
    allowance = _positive(noise_allowance, "noise_allowance")
    findings = []
    for energy, value in zip(lines, densities):
        density = _real(value, "optical density")
        if density < -allowance - TOLERANCE:
            findings.append(
                "the %g MeV line left the %s band %.4f in density below its "
                "unirradiated scan, which proton damage does not do"
                % (energy, name, density)
            )
    return findings


def combined_density(densities):
    """Return the darkening of a whole matrix as the sum of its lines."""
    if not isinstance(densities, (list, tuple)) or not densities:
        raise ValueError("densities must be a non-empty sequence")
    return sum(_real(value, "optical density") for value in densities)


def transmittance_after(reference_transmittance, density):
    """Return the transmittance left once a darkening density is applied."""
    base = _transmittance(reference_transmittance, "reference_transmittance")
    amount = _real(density, "density")
    return base * math.pow(10.0, -amount)


def assess_coverglass_proton_irradiation(spec):
    """Run the full clause 8.7.14 coverglass proton irradiation assessment.

    spec keys: reference_scan, lines (label, energy_mev, fluence_p_per_cm2,
    duration_s, scan), coating_thickness_um, glass_thickness_um,
    required_transmittance (band to fraction); optional max_flux,
    noise_allowance, range_coefficient_um, range_exponent.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("reference_scan", "lines", "coating_thickness_um",
                "glass_thickness_um", "required_transmittance"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lines = spec["lines"]
    if not isinstance(lines, (list, tuple)) or len(lines) < 2:
        raise ValueError("lines must carry at least two energy lines")
    required = spec["required_transmittance"]
    if not isinstance(required, dict) or not required:
        raise ValueError("required_transmittance must name at least one band")
    for key in required:
        _band(key)

    reference = _scan(spec["reference_scan"], "reference_scan")
    coefficient = spec.get("range_coefficient_um", RANGE_COEFFICIENT_UM)
    exponent = spec.get("range_exponent", RANGE_EXPONENT)

    energies = []
    scans = []
    findings = []
    depths = []
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            raise ValueError("each line must be a mapping")
        for key in ("label", "energy_mev", "fluence_p_per_cm2", "duration_s",
                    "scan"):
            if key not in line:
                raise ValueError("line %d missing key '%s'" % (index + 1, key))
        energies.append(line["energy_mev"])
        scans.append(line["scan"])
        depths.append(
            proton_range_um(line["energy_mev"], coefficient, exponent)
        )
        findings.extend(
            flux_findings(
                line["label"], line["fluence_p_per_cm2"], line["duration_s"],
                spec.get("max_flux", MAX_FLUX_P_PER_CM2_S),
            )
        )
    energies = validate_energy_lines(energies)
    coverage = zone_coverage(
        energies, spec["coating_thickness_um"], spec["glass_thickness_um"],
        coefficient, exponent,
    )
    findings.extend(coverage_findings(coverage))

    series = line_densities(reference, scans)
    report = {}
    for band in BANDS:
        densities = series[band]
        band_findings = brightening_findings(
            band, energies, densities,
            spec.get("noise_allowance", DENSITY_NOISE_ALLOWANCE),
        )
        total = combined_density(densities)
        left = transmittance_after(reference[band], total)
        if band in required:
            floor = _transmittance(
                required[band], "required_transmittance '%s'" % band
            )
            if left < floor - TOLERANCE:
                band_findings.append(
                    "the %s band is left at %.4f transmittance by the whole "
                    "matrix, under the %.4f the budget asks for"
                    % (band, left, floor)
                )
        report[band] = {
            "line_densities": densities,
            "combined_density": total,
            "transmittance_after": left,
            "findings": band_findings,
        }
        findings.extend(band_findings)

    return {
        "energies_mev": energies,
        "stopping_depths_um": depths,
        "zone_coverage": coverage,
        "line_count": len(energies),
        "bands": report,
        "findings": findings,
        "run_conformant": not findings,
    }
