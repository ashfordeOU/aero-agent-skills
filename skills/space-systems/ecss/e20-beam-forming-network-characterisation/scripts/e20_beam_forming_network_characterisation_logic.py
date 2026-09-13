#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 7.2.2.3.4 beam-forming-network circuit
characterisation (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard asks for the beam-forming network of an
antenna to be characterised as a circuit in its own right, independently
of the radiating aperture, and for the result of that characterisation
to be carried through into the antenna performance figures. This module
implements the checkable part of that clause: categorization of the
network topology, conversion of commanded element excitations plus
per-path amplitude and phase departures into the realized excitations
that actually reach the elements, the excitation-error statistics split
into a linear phase gradient (a beam-pointing shift) and a residual
(a gain loss), the quantisation floor of a digital phase shifter, the
dissipative insertion-loss chain against its allocation, and the
coherent recombination of element reflections at the input port.

It does not synthesise a network, does not compute a radiation pattern
from the excitations, and does not perform a thermal or a mechanical
assessment of the network hardware.
"""

import math

CORPORATE_TOPOLOGIES = frozenset(
    {
        "corporate_divider_tree",
        "reactive_power_divider_tree",
        "wilkinson_divider_tree",
    }
)
SERIES_TOPOLOGIES = frozenset(
    {
        "series_travelling_wave_feed",
        "coupled_line_series_feed",
        "waveguide_slotted_series_feed",
    }
)
MATRIX_TOPOLOGIES = frozenset(
    {
        "butler_matrix",
        "blass_matrix",
        "nolen_matrix",
    }
)
SWITCHED_TOPOLOGIES = frozenset(
    {
        "switched_beam_network",
        "switched_lens_network",
    }
)

_TOPOLOGY_FAMILIES = (
    ("corporate", CORPORATE_TOPOLOGIES),
    ("series", SERIES_TOPOLOGIES),
    ("matrix", MATRIX_TOPOLOGIES),
    ("switched", SWITCHED_TOPOLOGIES),
)

# Representation tolerance: a budget comparison whose two sides are sums
# of floating-point terms can land a few ULPs apart while the hardware is
# exactly on the allocation. The engineering limit is never widened; only
# the binary representation of an equal comparison is absorbed.
BUDGET_TOLERANCE_DB = 1e-9

# Reported floor for a level that is mathematically zero.
MINIMUM_REPORTED_LEVEL_DB = -200.0

MAX_PHASE_SHIFTER_BITS = 12


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _wrap_deg(angle_deg):
    """Fold an angle into the half-open interval [-180, 180) degrees."""
    return ((float(angle_deg) + 180.0) % 360.0) - 180.0


def categorize_network_topology(kind):
    """Return the family of a beam-forming-network topology.

    Families: corporate, series, matrix, switched. An unrecognized
    topology is a finding about the input, not a default.
    """
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("network topology must be a non-empty string")
    key = kind.strip().lower()
    for family, members in _TOPOLOGY_FAMILIES:
        if key in members:
            return family
    raise ValueError("unrecognized beam-forming-network topology: %r" % kind)


def realized_excitations(commanded, path_errors):
    """Apply per-path departures to the commanded element excitations.

    ``commanded`` is a list of mappings with ``amplitude_db`` and
    ``phase_deg``. ``path_errors`` is a same-length list of mappings with
    the optional keys ``insertion_loss_db`` (>= 0), ``amplitude_error_db``
    and ``phase_error_deg``. Returns the realized excitation of every
    element port.
    """
    if not isinstance(commanded, (list, tuple)) or not commanded:
        raise ValueError("commanded excitations must be a non-empty sequence")
    if not isinstance(path_errors, (list, tuple)) or not path_errors:
        raise ValueError("path errors must be a non-empty sequence")
    if len(commanded) != len(path_errors):
        raise ValueError(
            "commanded excitations (%d) and path errors (%d) must have the "
            "same length" % (len(commanded), len(path_errors))
        )
    out = []
    for index, (drive, error) in enumerate(zip(commanded, path_errors)):
        if not isinstance(drive, dict) or not isinstance(error, dict):
            raise ValueError("excitation entry %d must be a mapping" % index)
        amp_db = _as_float(drive.get("amplitude_db", 0.0), "amplitude_db[%d]" % index)
        phase_deg = _as_float(drive.get("phase_deg", 0.0), "phase_deg[%d]" % index)
        loss_db = _as_float(
            error.get("insertion_loss_db", 0.0), "insertion_loss_db[%d]" % index
        )
        if loss_db < 0.0:
            raise ValueError(
                "insertion_loss_db[%d] must be non-negative, got %r" % (index, loss_db)
            )
        amp_error_db = _as_float(
            error.get("amplitude_error_db", 0.0), "amplitude_error_db[%d]" % index
        )
        phase_error_deg = _as_float(
            error.get("phase_error_deg", 0.0), "phase_error_deg[%d]" % index
        )
        realized_db = amp_db - loss_db + amp_error_db
        realized_phase = _wrap_deg(phase_deg + phase_error_deg)
        out.append(
            {
                "index": index,
                "amplitude_db": realized_db,
                "amplitude_linear": 10.0 ** (realized_db / 20.0),
                "phase_deg": realized_phase,
                "commanded_amplitude_db": amp_db,
                "commanded_phase_deg": _wrap_deg(phase_deg),
            }
        )
    return out


def excitation_error_statistics(realized):
    """Split the realized-versus-commanded departure into its parts.

    A uniform amplitude offset is a dissipative loss, not an excitation
    error, so the amplitude statistic is taken about the mean. A linear
    phase gradient across the elements steers the beam rather than
    degrading it, so the phase statistic is the residual about a
    least-squares straight line; the fitted slope is reported separately
    because it feeds the beam-pointing check.
    """
    if not isinstance(realized, (list, tuple)) or not realized:
        raise ValueError("realized excitations must be a non-empty sequence")
    amp_errors = []
    phase_errors = []
    for index, item in enumerate(realized):
        if not isinstance(item, dict):
            raise ValueError("realized excitation %d must be a mapping" % index)
        amp = _as_float(item.get("amplitude_db"), "amplitude_db[%d]" % index)
        cmd_amp = _as_float(
            item.get("commanded_amplitude_db"), "commanded_amplitude_db[%d]" % index
        )
        phase = _as_float(item.get("phase_deg"), "phase_deg[%d]" % index)
        cmd_phase = _as_float(
            item.get("commanded_phase_deg"), "commanded_phase_deg[%d]" % index
        )
        amp_errors.append(amp - cmd_amp)
        phase_errors.append(_wrap_deg(phase - cmd_phase))

    count = len(amp_errors)
    mean_amp = sum(amp_errors) / count
    relative_amp = [10.0 ** ((e - mean_amp) / 20.0) - 1.0 for e in amp_errors]
    rms_amp_db = math.sqrt(sum((e - mean_amp) ** 2 for e in amp_errors) / count)
    rms_amp_linear = math.sqrt(sum(e * e for e in relative_amp) / count)

    indices = list(range(count))
    mean_index = sum(indices) / count
    mean_phase = sum(phase_errors) / count
    denominator = sum((i - mean_index) ** 2 for i in indices)
    if denominator == 0.0:
        slope = 0.0
    else:
        slope = (
            sum(
                (i - mean_index) * (e - mean_phase)
                for i, e in zip(indices, phase_errors)
            )
            / denominator
        )
    intercept = mean_phase - slope * mean_index
    residuals = [e - (intercept + slope * i) for i, e in zip(indices, phase_errors)]
    rms_phase_deg = math.sqrt(sum(r * r for r in residuals) / count)

    return {
        "element_count": count,
        "common_amplitude_offset_db": mean_amp,
        "rms_amplitude_error_db": rms_amp_db,
        "rms_relative_amplitude_error": rms_amp_linear,
        "phase_slope_deg_per_element": slope,
        "residual_rms_phase_error_deg": rms_phase_deg,
    }


def gain_loss_from_errors(rms_relative_amplitude_error, rms_phase_error_deg):
    """Aperture gain loss produced by random excitation errors, in dB.

    Amplitude scatter costs efficiency as 1/(1 + s^2); residual phase
    scatter costs the Ruze factor exp(-sigma^2) with sigma in radians.
    """
    amp = _as_float(rms_relative_amplitude_error, "rms_relative_amplitude_error")
    phase = _as_float(rms_phase_error_deg, "rms_phase_error_deg")
    if amp < 0.0:
        raise ValueError("rms relative amplitude error must be non-negative")
    if phase < 0.0:
        raise ValueError("rms phase error must be non-negative")
    sigma = math.radians(phase)
    efficiency = (1.0 / (1.0 + amp * amp)) * math.exp(-sigma * sigma)
    if efficiency <= 0.0:
        raise ValueError("excitation errors drive the aperture efficiency to zero")
    return -10.0 * math.log10(efficiency)


def phase_quantisation_effects(bits):
    """Floor imposed by an N-bit digital phase shifter.

    Least significant step 360/2^N degrees, uniform residual of
    step/sqrt(12), the Ruze gain loss that residual causes, and the peak
    quantisation lobe at 1/2^N of the main beam in amplitude.
    """
    if isinstance(bits, bool) or not isinstance(bits, int):
        raise ValueError("phase shifter resolution must be an integer bit count")
    if bits < 1 or bits > MAX_PHASE_SHIFTER_BITS:
        raise ValueError(
            "phase shifter resolution must be 1..%d bits, got %d"
            % (MAX_PHASE_SHIFTER_BITS, bits)
        )
    states = 2 ** bits
    step_deg = 360.0 / states
    residual_deg = step_deg / math.sqrt(12.0)
    return {
        "bits": bits,
        "state_count": states,
        "least_significant_step_deg": step_deg,
        "residual_rms_phase_error_deg": residual_deg,
        "gain_loss_db": gain_loss_from_errors(0.0, residual_deg),
        "peak_quantisation_lobe_db": -20.0 * math.log10(float(states)),
    }


def beam_pointing_shift_deg(
    phase_slope_deg_per_element, element_spacing_wavelengths, commanded_scan_deg=0.0
):
    """Boresight shift caused by a linear phase gradient across elements."""
    slope = _as_float(phase_slope_deg_per_element, "phase_slope_deg_per_element")
    spacing = _as_float(element_spacing_wavelengths, "element_spacing_wavelengths")
    scan = _as_float(commanded_scan_deg, "commanded_scan_deg")
    if spacing <= 0.0:
        raise ValueError("element spacing must be positive, got %r" % spacing)
    if not -90.0 <= scan <= 90.0:
        raise ValueError("commanded scan angle must lie within +/-90 deg")
    direction_error = math.radians(slope) / (2.0 * math.pi * spacing)
    total = math.sin(math.radians(scan)) + direction_error
    if abs(total) > 1.0:
        raise ValueError(
            "phase gradient steers the beam outside the visible region "
            "(sin theta = %.6f)" % total
        )
    return math.degrees(math.asin(total)) - scan


def insertion_loss_budget(stages, allocation_db):
    """Sum the dissipative stages of the network and judge the allocation."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("insertion loss stages must be a non-empty sequence")
    allocation = _as_float(allocation_db, "allocation_db")
    if allocation < 0.0:
        raise ValueError("insertion loss allocation must be non-negative")
    total = 0.0
    itemised = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            raise ValueError("insertion loss stage %d must be a mapping" % index)
        name = stage.get("name") or "stage-%d" % index
        loss = _as_float(stage.get("loss_db"), "loss_db[%s]" % name)
        if loss < 0.0:
            raise ValueError("loss_db[%s] must be non-negative, got %r" % (name, loss))
        total += loss
        itemised.append({"name": name, "loss_db": loss})
    compliant = total <= allocation or math.isclose(
        total, allocation, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE_DB
    )
    return {
        "stages": itemised,
        "total_loss_db": total,
        "allocation_db": allocation,
        "margin_db": allocation - total,
        "compliant": compliant,
    }


def input_port_match(element_reflections, vswr_limit=1.5):
    """Recombine element reflections coherently at the network input.

    An N-way divider brings every element reflection back to the input
    attenuated by the same split ratio, so the input reflection is the
    vector mean of the element reflections.
    """
    if not isinstance(element_reflections, (list, tuple)) or not element_reflections:
        raise ValueError("element reflections must be a non-empty sequence")
    limit = _as_float(vswr_limit, "vswr_limit")
    if limit < 1.0:
        raise ValueError("vswr limit must be at least 1.0, got %r" % limit)
    real = 0.0
    imag = 0.0
    for index, item in enumerate(element_reflections):
        if not isinstance(item, dict):
            raise ValueError("element reflection %d must be a mapping" % index)
        magnitude = _as_float(item.get("magnitude"), "magnitude[%d]" % index)
        if not 0.0 <= magnitude <= 1.0:
            raise ValueError(
                "reflection magnitude[%d] must lie in 0..1, got %r" % (index, magnitude)
            )
        phase = math.radians(_as_float(item.get("phase_deg", 0.0), "phase_deg[%d]" % index))
        real += magnitude * math.cos(phase)
        imag += magnitude * math.sin(phase)
    count = len(element_reflections)
    resultant = math.hypot(real, imag) / count
    if resultant >= 1.0:
        raise ValueError("input reflection magnitude reached unity; check the inputs")
    vswr = (1.0 + resultant) / (1.0 - resultant)
    if resultant == 0.0:
        return_loss_db = -MINIMUM_REPORTED_LEVEL_DB
    else:
        return_loss_db = -20.0 * math.log10(resultant)
    compliant = vswr <= limit or math.isclose(
        vswr, limit, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE_DB
    )
    return {
        "reflection_magnitude": resultant,
        "return_loss_db": return_loss_db,
        "vswr": vswr,
        "vswr_limit": limit,
        "compliant": compliant,
    }


def assess_beam_forming_network(spec):
    """Run the clause 7.2.2.3.4 characterisation end to end.

    Required keys: ``topology``, ``commanded``, ``path_errors``,
    ``element_spacing_wavelengths``, ``loss_stages``,
    ``loss_allocation_db``. Optional keys: ``phase_shifter_bits``,
    ``commanded_scan_deg``, ``element_reflections``, ``vswr_limit``,
    ``gain_loss_allocation_db``, ``pointing_allocation_deg``.
    """
    if not isinstance(spec, dict):
        raise ValueError("beam-forming-network spec must be a mapping")
    for key in (
        "topology",
        "commanded",
        "path_errors",
        "element_spacing_wavelengths",
        "loss_stages",
        "loss_allocation_db",
    ):
        if key not in spec:
            raise ValueError("beam-forming-network spec missing required key %r" % key)

    family = categorize_network_topology(spec["topology"])
    realized = realized_excitations(spec["commanded"], spec["path_errors"])
    statistics = excitation_error_statistics(realized)

    gain_loss_db = gain_loss_from_errors(
        statistics["rms_relative_amplitude_error"],
        statistics["residual_rms_phase_error_deg"],
    )
    quantisation = None
    if spec.get("phase_shifter_bits") is not None:
        quantisation = phase_quantisation_effects(spec["phase_shifter_bits"])
        gain_loss_db += quantisation["gain_loss_db"]

    pointing_shift_deg = beam_pointing_shift_deg(
        statistics["phase_slope_deg_per_element"],
        spec["element_spacing_wavelengths"],
        spec.get("commanded_scan_deg", 0.0),
    )
    budget = insertion_loss_budget(spec["loss_stages"], spec["loss_allocation_db"])
    match = None
    if spec.get("element_reflections"):
        match = input_port_match(
            spec["element_reflections"], spec.get("vswr_limit", 1.5)
        )

    findings = []
    if not budget["compliant"]:
        findings.append(
            "dissipative insertion loss %.3f dB exceeds the %.3f dB allocation"
            % (budget["total_loss_db"], budget["allocation_db"])
        )
    gain_allocation = spec.get("gain_loss_allocation_db")
    if gain_allocation is not None:
        gain_allocation = _as_float(gain_allocation, "gain_loss_allocation_db")
        if gain_allocation < 0.0:
            raise ValueError("gain loss allocation must be non-negative")
        exceeds = gain_loss_db > gain_allocation and not math.isclose(
            gain_loss_db, gain_allocation, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE_DB
        )
        if exceeds:
            findings.append(
                "excitation-error gain loss %.4f dB exceeds the %.4f dB allocation"
                % (gain_loss_db, gain_allocation)
            )
    pointing_allocation = spec.get("pointing_allocation_deg")
    if pointing_allocation is not None:
        pointing_allocation = _as_float(pointing_allocation, "pointing_allocation_deg")
        if pointing_allocation < 0.0:
            raise ValueError("pointing allocation must be non-negative")
        magnitude = abs(pointing_shift_deg)
        exceeds = magnitude > pointing_allocation and not math.isclose(
            magnitude, pointing_allocation, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE_DB
        )
        if exceeds:
            findings.append(
                "beam-pointing shift %.4f deg exceeds the %.4f deg allocation"
                % (magnitude, pointing_allocation)
            )
    if match is not None and not match["compliant"]:
        findings.append(
            "input-port vswr %.3f exceeds the %.3f limit"
            % (match["vswr"], match["vswr_limit"])
        )

    return {
        "topology_family": family,
        "statistics": statistics,
        "gain_loss_db": gain_loss_db,
        "quantisation": quantisation,
        "beam_pointing_shift_deg": pointing_shift_deg,
        "insertion_loss_budget": budget,
        "input_port_match": match,
        "findings": findings,
        "compliant": not findings,
    }
