#!/usr/bin/env python3
"""Antenna feed-chain characterisation (ECSS-E-ST-20C clause 7.2.2.3.5).

Deterministic, offline, stdlib-only engineering logic for the clause
7.2.2.3.5 case: the passive circuit between the transceiver port and the
radiating aperture -- runs, filters, diplexers, transducers, rotary joints,
couplers, switches -- is characterised as a circuit in its own right, and its
characterisation is then folded into the performance of the antenna as a
whole.

The procedure implemented here is a paraphrase of the clause intent, not a
reproduction of the standard: the clause is cited as the traceability anchor
only.

Pipeline
--------
1. Stage list -> stage kind categorisation and per-stage validation.
2. Per-stage dissipation -> cascaded insertion-loss against its allocation.
3. Per-stage dissipation + physical temperature -> cascaded noise
   temperature referred to the chain input (Friis).
4. Per-stage reflection -> adjacent-interface mismatch ripple and the
   worst-case input-port reflection and standing-wave-ratio.
5. Transmit direction -> per-stage forward power and handling margin.
6. Per-stage delay ripple -> chain delay ripple against its allocation.
7. Receive direction -> figure-of-merit penalty charged to the antenna.
8. All results vs the chain allocation -> findings and a verdict.
"""

from __future__ import annotations

import math

__all__ = [
    "STAGE_KINDS",
    "DIRECTIONS",
    "categorize_stage",
    "validate_chain",
    "reflection_from_return_loss",
    "stage_loss_factor",
    "cascade_insertion_loss_db",
    "cascade_noise_temperature_k",
    "mismatch_ripple_db",
    "worst_interface_ripple",
    "input_port_reflection",
    "input_port_standing_wave_ratio",
    "forward_power_profile",
    "power_handling_margins",
    "chain_group_delay_ns",
    "group_delay_ripple_ns",
    "figure_of_merit_penalty_db",
    "assess_rf_chain",
]

STAGE_KINDS = (
    "waveguide-run",
    "coaxial-run",
    "filter",
    "diplexer",
    "orthomode-transducer",
    "rotary-joint",
    "directional-coupler",
    "polariser",
    "switch",
)

DIRECTIONS = ("transmit", "receive")

STANDARD_PHYSICAL_TEMPERATURE_K = 290.0
MAX_STAGE_INSERTION_LOSS_DB = 40.0

REL_TOL = 1e-9
ABS_TOL = 1e-12


# --- small helpers ---------------------------------------------------------


def _as_float(value, name):
    """Coerce to a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _le(value, limit):
    """True when value <= limit, absorbing float representation error.

    A cascaded budget is a sum of dB terms, so a chain that is exactly on
    its allocation can land a few ULPs above it. The allocation is never
    widened; only the binary representation of an equal value is tolerated.
    """
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _ge(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


# --- 1. stage validation ---------------------------------------------------


def categorize_stage(stage):
    """Validate one feed-chain stage and return its categorized kind."""
    if not isinstance(stage, dict):
        raise ValueError("each stage must be a mapping, got %r" % (stage,))
    ident = stage.get("id")
    if not isinstance(ident, str) or not ident:
        raise ValueError("each stage needs a non-empty string id, got %r" % (ident,))
    kind = stage.get("kind")
    if kind not in STAGE_KINDS:
        raise ValueError(
            "stage %s has kind %r; expected one of %s" % (ident, kind, list(STAGE_KINDS))
        )
    loss = _as_float(stage.get("insertion_loss_db"), "stage %s insertion_loss_db" % ident)
    if loss < 0.0:
        raise ValueError("stage %s: a passive stage cannot have gain (%.3f dB)" % (ident, loss))
    if loss > MAX_STAGE_INSERTION_LOSS_DB:
        raise ValueError(
            "stage %s: %.1f dB exceeds the %.0f dB ceiling of a feed-chain stage; "
            "a stage this lossy is a termination, not a through path"
            % (ident, loss, MAX_STAGE_INSERTION_LOSS_DB)
        )
    reflection_from_return_loss(stage.get("return_loss_db"), "stage %s return_loss_db" % ident)
    return kind


def validate_chain(chain):
    """Validate the whole ordered stage list; return the categorized kinds."""
    if not isinstance(chain, (list, tuple)):
        raise ValueError("chain must be a list of stage mappings")
    if not chain:
        raise ValueError("chain must contain at least one stage")
    kinds = []
    seen = []
    for stage in chain:
        kind = categorize_stage(stage)
        if stage["id"] in seen:
            raise ValueError("duplicate stage id %r in the chain" % (stage["id"],))
        seen.append(stage["id"])
        kinds.append(kind)
    return kinds


def reflection_from_return_loss(return_loss_db, name="return_loss_db"):
    """Reflection magnitude implied by a return loss in dB."""
    value = _as_float(return_loss_db, name)
    if value <= 0.0:
        raise ValueError("%s must be > 0 dB, got %r" % (name, return_loss_db))
    return 10.0 ** (-value / 20.0)


def stage_loss_factor(insertion_loss_db):
    """Linear dissipation factor of a stage: the power ratio in over out."""
    value = _as_float(insertion_loss_db, "insertion_loss_db")
    if value < 0.0:
        raise ValueError("insertion_loss_db must be >= 0 for a passive stage, got %r" % (value,))
    return 10.0 ** (value / 10.0)


# --- 2/3. dissipation and noise --------------------------------------------


def cascade_insertion_loss_db(chain):
    """Total dissipation of the chain, in dB."""
    validate_chain(chain)
    return sum(float(stage["insertion_loss_db"]) for stage in chain)


def cascade_noise_temperature_k(chain, physical_temperature_k=STANDARD_PHYSICAL_TEMPERATURE_K):
    """Noise temperature of the passive chain referred to its input port.

    Each stage contributes (L-1)*T_phys at its own input; the Friis cascade
    refers every contribution back through the gain of the stages ahead of
    it. For an all-passive chain this collapses to (L_total - 1)*T_phys,
    which is the identity the contract test pins.
    """
    validate_chain(chain)
    temperature = _as_float(physical_temperature_k, "physical_temperature_k")
    if temperature <= 0.0:
        raise ValueError("physical_temperature_k must be > 0 K, got %r" % (physical_temperature_k,))
    total = 0.0
    upstream_loss_factor = 1.0
    for stage in chain:
        factor = stage_loss_factor(stage["insertion_loss_db"])
        total += (factor - 1.0) * temperature * upstream_loss_factor
        upstream_loss_factor *= factor
    return total


# --- 4. mismatch -----------------------------------------------------------


def mismatch_ripple_db(gamma_a, gamma_b):
    """Peak-to-peak transmission ripple between two reflecting interfaces."""
    a = abs(_as_float(gamma_a, "gamma_a"))
    b = abs(_as_float(gamma_b, "gamma_b"))
    if a >= 1.0 or b >= 1.0:
        raise ValueError("a reflection magnitude must be < 1 for a passive interface")
    product = a * b
    if product >= 1.0:
        raise ValueError("the interface pair is not passive: |gamma_a||gamma_b| >= 1")
    return 20.0 * math.log10((1.0 + product) / (1.0 - product))


def worst_interface_ripple(chain):
    """Worst adjacent-stage mismatch ripple in the chain."""
    validate_chain(chain)
    if len(chain) < 2:
        return {"pair": None, "ripple_db": 0.0}
    worst_pair = None
    worst_value = 0.0
    for upstream, downstream in zip(chain[:-1], chain[1:]):
        ripple = mismatch_ripple_db(
            reflection_from_return_loss(upstream["return_loss_db"]),
            reflection_from_return_loss(downstream["return_loss_db"]),
        )
        if ripple > worst_value:
            worst_value = ripple
            worst_pair = (upstream["id"], downstream["id"])
    return {"pair": worst_pair, "ripple_db": worst_value}


def input_port_reflection(chain):
    """Worst-case reflection at the chain input: every stage adding in phase.

    A stage reflection returns to the input port through the dissipation of
    everything ahead of it, twice, so a deep stage contributes far less than
    a shallow one. Summing the attenuated magnitudes is the worst case the
    phases can produce.
    """
    validate_chain(chain)
    total = 0.0
    upstream_loss_db = 0.0
    for stage in chain:
        magnitude = reflection_from_return_loss(stage["return_loss_db"])
        total += magnitude * 10.0 ** (-upstream_loss_db / 10.0)
        upstream_loss_db += float(stage["insertion_loss_db"])
    return total


def input_port_standing_wave_ratio(chain):
    """Standing-wave-ratio implied by the worst-case input-port reflection."""
    magnitude = input_port_reflection(chain)
    if magnitude >= 1.0 or math.isclose(magnitude, 1.0, rel_tol=REL_TOL):
        raise ValueError(
            "worst-case input reflection is %.4f: the stage return losses as declared "
            "cannot describe a passive chain" % magnitude
        )
    return (1.0 + magnitude) / (1.0 - magnitude)


# --- 5. transmit-direction handling ----------------------------------------


def forward_power_profile(chain, input_power_w):
    """Forward power arriving at the input of each stage, in watts."""
    validate_chain(chain)
    power = _as_float(input_power_w, "input_power_w")
    if power <= 0.0:
        raise ValueError("input_power_w must be > 0, got %r" % (input_power_w,))
    profile = []
    upstream_loss_db = 0.0
    for stage in chain:
        profile.append((stage["id"], power * 10.0 ** (-upstream_loss_db / 10.0)))
        upstream_loss_db += float(stage["insertion_loss_db"])
    return profile


def power_handling_margins(chain, input_power_w):
    """Handling margin in dB of every stage that declares a rating."""
    profile = dict(forward_power_profile(chain, input_power_w))
    margins = []
    for stage in chain:
        rating = stage.get("power_rating_w")
        if rating is None:
            continue
        value = _as_float(rating, "stage %s power_rating_w" % stage["id"])
        if value <= 0.0:
            raise ValueError("stage %s power_rating_w must be > 0" % (stage["id"],))
        arriving = profile[stage["id"]]
        margins.append(
            {
                "stage": stage["id"],
                "forward_power_w": arriving,
                "rating_w": value,
                "margin_db": 10.0 * math.log10(value / arriving),
            }
        )
    return margins


# --- 6. delay --------------------------------------------------------------


def chain_group_delay_ns(chain):
    """Sum of the stage delays through the chain, in nanoseconds."""
    validate_chain(chain)
    total = 0.0
    for stage in chain:
        delay = _as_float(stage.get("group_delay_ns", 0.0), "stage %s group_delay_ns" % stage["id"])
        if delay < 0.0:
            raise ValueError("stage %s group_delay_ns must be >= 0" % (stage["id"],))
        total += delay
    return total


def group_delay_ripple_ns(chain):
    """Root-sum-square of the independent stage delay ripples."""
    validate_chain(chain)
    total = 0.0
    for stage in chain:
        ripple = _as_float(
            stage.get("group_delay_ripple_ns", 0.0), "stage %s group_delay_ripple_ns" % stage["id"]
        )
        if ripple < 0.0:
            raise ValueError("stage %s group_delay_ripple_ns must be >= 0" % (stage["id"],))
        total += ripple * ripple
    return math.sqrt(total)


# --- 7. effect on the antenna as a whole -----------------------------------


def figure_of_merit_penalty_db(
    chain,
    antenna_noise_temperature_k,
    receiver_noise_temperature_k,
    physical_temperature_k=STANDARD_PHYSICAL_TEMPERATURE_K,
):
    """Receive figure-of-merit lost to the chain, in dB.

    The chain costs twice: its dissipation removes signal gain, and it adds
    its own noise while lifting the receiver contribution referred to the
    antenna port.
    """
    antenna = _as_float(antenna_noise_temperature_k, "antenna_noise_temperature_k")
    receiver = _as_float(receiver_noise_temperature_k, "receiver_noise_temperature_k")
    if antenna <= 0.0:
        raise ValueError("antenna_noise_temperature_k must be > 0 K")
    if receiver <= 0.0:
        raise ValueError("receiver_noise_temperature_k must be > 0 K")
    loss_db = cascade_insertion_loss_db(chain)
    loss_factor = 10.0 ** (loss_db / 10.0)
    chain_noise = cascade_noise_temperature_k(chain, physical_temperature_k)
    without_chain = antenna + receiver
    with_chain = antenna + chain_noise + loss_factor * receiver
    return loss_db + 10.0 * math.log10(with_chain / without_chain)


# --- 8. aggregate assessment ------------------------------------------------

_DEFAULT_LIMITS = {
    "max_insertion_loss_db": 1.0,
    "max_input_standing_wave_ratio": 1.5,
    "max_interface_ripple_db": 0.4,
    "min_power_handling_margin_db": 3.0,
    "max_group_delay_ripple_ns": 2.0,
    "max_figure_of_merit_penalty_db": 1.5,
}


def assess_rf_chain(config):
    """Full clause 7.2.2.3.5 characterisation of one antenna feed chain."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    chain = config.get("chain")
    kinds = validate_chain(chain)
    direction = config.get("direction")
    if direction not in DIRECTIONS:
        raise ValueError("direction must be one of %s, got %r" % (list(DIRECTIONS), direction))

    limits = dict(_DEFAULT_LIMITS)
    supplied = config.get("limits", {})
    if not isinstance(supplied, dict):
        raise ValueError("config['limits'] must be a mapping")
    for key in supplied:
        if key not in _DEFAULT_LIMITS:
            raise ValueError("unknown allocation key %r" % (key,))
        limits[key] = _as_float(supplied[key], "limits[%r]" % (key,))

    physical = _as_float(
        config.get("physical_temperature_k", STANDARD_PHYSICAL_TEMPERATURE_K),
        "physical_temperature_k",
    )
    insertion_loss = cascade_insertion_loss_db(chain)
    noise_temperature = cascade_noise_temperature_k(chain, physical)
    ripple = worst_interface_ripple(chain)
    standing_wave = input_port_standing_wave_ratio(chain)
    delay = chain_group_delay_ns(chain)
    delay_ripple = group_delay_ripple_ns(chain)

    margins = []
    penalty = None
    if direction == "transmit":
        input_power = config.get("input_power_w")
        if input_power is None:
            raise ValueError("a transmit chain assessment requires config['input_power_w']")
        margins = power_handling_margins(chain, input_power)
    else:
        penalty = figure_of_merit_penalty_db(
            chain,
            config.get("antenna_noise_temperature_k", 50.0),
            config.get("receiver_noise_temperature_k", 120.0),
            physical,
        )

    findings = []
    if not _le(insertion_loss, limits["max_insertion_loss_db"]):
        findings.append(
            "cascaded insertion loss is %.3f dB, above the %.3f dB allocation"
            % (insertion_loss, limits["max_insertion_loss_db"])
        )
    if not _le(standing_wave, limits["max_input_standing_wave_ratio"]):
        findings.append(
            "input-port standing-wave-ratio is %.3f, above the %.3f allocation"
            % (standing_wave, limits["max_input_standing_wave_ratio"])
        )
    if not _le(ripple["ripple_db"], limits["max_interface_ripple_db"]):
        pair = ripple["pair"]
        label = "%s-%s" % pair if pair else "the single-stage chain"
        findings.append(
            "interface %s ripples %.3f dB, above the %.3f dB allocation"
            % (label, ripple["ripple_db"], limits["max_interface_ripple_db"])
        )
    if not _le(delay_ripple, limits["max_group_delay_ripple_ns"]):
        findings.append(
            "chain delay ripple is %.3f ns, above the %.3f ns allocation"
            % (delay_ripple, limits["max_group_delay_ripple_ns"])
        )
    for entry in margins:
        if not _ge(entry["margin_db"], limits["min_power_handling_margin_db"]):
            findings.append(
                "stage %s holds only %.2f dB of handling margin, below the %.2f dB allocation"
                % (entry["stage"], entry["margin_db"], limits["min_power_handling_margin_db"])
            )
    if penalty is not None and not _le(penalty, limits["max_figure_of_merit_penalty_db"]):
        findings.append(
            "the chain costs %.3f dB of receive figure-of-merit, above the %.3f dB allocation"
            % (penalty, limits["max_figure_of_merit_penalty_db"])
        )

    return {
        "direction": direction,
        "stage_kinds": dict(zip([stage["id"] for stage in chain], kinds)),
        "insertion_loss_db": insertion_loss,
        "noise_temperature_k": noise_temperature,
        "input_reflection_magnitude": input_port_reflection(chain),
        "input_standing_wave_ratio": standing_wave,
        "worst_interface": ripple,
        "group_delay_ns": delay,
        "group_delay_ripple_ns": delay_ripple,
        "power_handling_margins": margins,
        "figure_of_merit_penalty_db": penalty,
        "findings": findings,
        "compliant": not findings,
    }
