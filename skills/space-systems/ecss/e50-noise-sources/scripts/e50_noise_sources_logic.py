"""Noise sources on a space link, gathered at one reference plane.

Anchor: ECSS-E-ST-50C Rev.2 clause 5.6.6 -- noise sources. Paraphrased into an
implementable procedure; no standard text is reproduced.

The single normative item is that the noise sources acting on the link are
identified. Identification is only worth something once the sources are
carried to a common plane and added, so the procedure here does both:

  categories  -- the source groups a receiving chain always has (sky and
                 cosmic background, atmosphere, ground and spillover, feed
                 and line loss, receiver front end) are each present, or the
                 identification is short and says which group is missing;
  referral    -- a source stated at its own plane is divided by the loss
                 between that plane and the reference plane, because an
                 antenna-plane temperature and a receiver-input temperature
                 are not the same number;
  generation  -- a lossy element does not only attenuate what passes through
                 it, it generates noise of its own, T_phys (L - 1) / L, and a
                 budget that only attenuates is optimistic by exactly that;
  totals      -- the sum at the reference plane, the group that dominates it,
                 the figure of merit G/T it produces, and how it stands
                 against the allocation.

Naming the dominant group is the output an engineer acts on: a chain whose
total is set by feed loss is fixed with a shorter run, one set by the front
end with a better amplifier, and the total alone says neither.

Stdlib only, offline, deterministic.
"""

import math

__all__ = [
    "COMPLIANT",
    "INCOMPLETE",
    "OVER_ALLOCATION",
    "REL_TOL",
    "REFERENCE_PHYSICAL_TEMPERATURE_K",
    "REQUIRED_SOURCE_CATEGORIES",
    "validate_temperature_k",
    "validate_loss_db",
    "validate_gain_dbi",
    "loss_factor",
    "refer_through_loss",
    "loss_noise_temperature",
    "validate_source",
    "source_contribution_k",
    "identified_categories",
    "missing_categories",
    "system_noise_temperature",
    "dominant_source",
    "figure_of_merit_db",
    "allocation_margin_k",
    "assess_noise_budget",
]

COMPLIANT = "compliant"
INCOMPLETE = "incomplete"
OVER_ALLOCATION = "over-allocation"

# Relative tolerance on every allocation comparison, so a budget written to
# land exactly on its allocation is inside it on every machine.
REL_TOL = 1e-9

REFERENCE_PHYSICAL_TEMPERATURE_K = 290.0

# The source groups a receiving chain always has. A group absent from the
# identification is a gap in the identification, not a zero contribution.
REQUIRED_SOURCE_CATEGORIES = (
    "sky-and-cosmic-background",
    "atmospheric",
    "ground-and-spillover",
    "feed-and-line-loss",
    "receiver-front-end",
)


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return number


def validate_temperature_k(value, name="temperature_k"):
    """Return a non-negative noise temperature in kelvin."""
    temperature = _validate_number(value, name)
    if temperature < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return temperature


def validate_loss_db(value, name="loss_db"):
    """Return a non-negative loss in decibels."""
    loss = _validate_number(value, name)
    if loss < 0.0:
        raise ValueError(
            "%s must not be negative; a loss below zero is a gain, got %r"
            % (name, value)
        )
    return loss


def validate_gain_dbi(value, name="gain_dbi"):
    """Return an antenna gain in dBi."""
    return _validate_number(value, name)


def loss_factor(loss_db):
    """Return the linear loss factor for a loss in decibels."""
    return 10.0 ** (validate_loss_db(loss_db) / 10.0)


def refer_through_loss(temperature_k, loss_db):
    """Return a source temperature carried through a loss to the far side."""
    temperature = validate_temperature_k(temperature_k)
    return temperature / loss_factor(loss_db)


def loss_noise_temperature(loss_db, physical_temperature_k=REFERENCE_PHYSICAL_TEMPERATURE_K):
    """Return the noise a lossy element adds at its own output."""
    factor = loss_factor(loss_db)
    physical = validate_temperature_k(physical_temperature_k, "physical_temperature_k")
    return physical * (factor - 1.0) / factor


def validate_source(source):
    """Return one normalised noise source entry.

    A source is either stated as a noise temperature at its own plane, or as
    a lossy element with a physical temperature. Declaring both is refused:
    the two describe different things and adding them double counts the
    element.
    """
    if not isinstance(source, dict):
        raise ValueError("source must be a mapping")
    category = source.get("category")
    if isinstance(category, bool) or not isinstance(category, str) or not category.strip():
        raise ValueError("source needs a non-blank category, got %r" % (category,))
    category = category.strip()
    has_temperature = source.get("temperature_k") is not None
    has_loss = source.get("loss_db") is not None
    if has_temperature and has_loss:
        raise ValueError(
            "source %r declares both a noise temperature and a loss; a lossy "
            "element generates its own noise and must not also carry one" % category
        )
    if not has_temperature and not has_loss:
        raise ValueError(
            "source %r declares neither a noise temperature nor a loss" % category
        )
    referred = source.get("referred_through_loss_db", 0.0)
    entry = {
        "category": category,
        "referred_through_loss_db": validate_loss_db(referred, "referred_through_loss_db"),
    }
    if has_temperature:
        entry["temperature_k"] = validate_temperature_k(source["temperature_k"])
        entry["loss_db"] = None
        entry["physical_temperature_k"] = None
    else:
        entry["temperature_k"] = None
        entry["loss_db"] = validate_loss_db(source["loss_db"])
        entry["physical_temperature_k"] = validate_temperature_k(
            source.get("physical_temperature_k", REFERENCE_PHYSICAL_TEMPERATURE_K),
            "physical_temperature_k",
        )
    return entry


def source_contribution_k(source):
    """Return one source's contribution at the reference plane."""
    entry = validate_source(source)
    if entry["temperature_k"] is not None:
        at_own_plane = entry["temperature_k"]
    else:
        at_own_plane = loss_noise_temperature(
            entry["loss_db"], entry["physical_temperature_k"]
        )
    return refer_through_loss(at_own_plane, entry["referred_through_loss_db"])


def _normalize_sources(sources):
    if isinstance(sources, (str, bytes)) or not hasattr(sources, "__iter__"):
        raise ValueError("sources must be a sequence of source entries")
    entries = [validate_source(s) for s in sources]
    if not entries:
        raise ValueError("sources must name at least one noise source")
    return entries


def identified_categories(sources):
    """Return the source categories the identification names, sorted."""
    return tuple(sorted({e["category"] for e in _normalize_sources(sources)}))


def missing_categories(sources, required=REQUIRED_SOURCE_CATEGORIES):
    """Return required categories the identification does not name."""
    named = set(identified_categories(sources))
    return tuple(c for c in required if c not in named)


def system_noise_temperature(sources):
    """Return the total noise temperature at the reference plane."""
    total = 0.0
    for entry in _normalize_sources(sources):
        total += source_contribution_k(entry)
    return total


def dominant_source(sources):
    """Return the largest contributor as (category, kelvin).

    Ties break on the category name so the answer does not depend on the
    order the sources were listed in.
    """
    entries = _normalize_sources(sources)
    best = None
    for entry in entries:
        value = source_contribution_k(entry)
        key = (-value, entry["category"])
        if best is None or key < best[0]:
            best = (key, entry["category"], value)
    return (best[1], best[2])


def figure_of_merit_db(gain_dbi, system_temperature_k):
    """Return the receiving figure of merit G/T in dB/K."""
    gain = validate_gain_dbi(gain_dbi)
    temperature = validate_temperature_k(system_temperature_k, "system_temperature_k")
    if temperature <= 0.0:
        raise ValueError("system_temperature_k must be greater than zero for G/T")
    return gain - 10.0 * math.log10(temperature)


def allocation_margin_k(computed_k, allocation_k):
    """Return the kelvin still unspent against the allocation."""
    computed = validate_temperature_k(computed_k, "computed_k")
    allocation = validate_temperature_k(allocation_k, "allocation_k")
    return allocation - computed


def assess_noise_budget(sources, allocation_k, gain_dbi=None, required_gt_db=None):
    """Grade a noise source identification and the budget it produces."""
    entries = _normalize_sources(sources)
    absent = missing_categories(entries)
    total = system_noise_temperature(entries)
    allocation = validate_temperature_k(allocation_k, "allocation_k")
    margin = allocation_margin_k(total, allocation)
    scale = max(abs(total), abs(allocation), 1.0)
    inside = total <= allocation + REL_TOL * scale
    gt_db = None
    if gain_dbi is not None:
        gt_db = figure_of_merit_db(gain_dbi, total)
    findings = []
    for category in absent:
        findings.append("no %s source is identified" % category)
    if not inside:
        findings.append(
            "system noise temperature %.6g K exceeds the %.6g K allocation by %.6g K"
            % (total, allocation, -margin)
        )
    gt_short = False
    if gt_db is not None and required_gt_db is not None:
        required_gt = _validate_number(required_gt_db, "required_gt_db")
        gt_scale = max(abs(gt_db), abs(required_gt), 1.0)
        if gt_db < required_gt - REL_TOL * gt_scale:
            gt_short = True
            findings.append(
                "figure of merit %.6g dB/K is below the %.6g dB/K required"
                % (gt_db, required_gt)
            )
    leader, leader_k = dominant_source(entries)
    if absent or not inside or gt_short:
        findings.append(
            "%s dominates the budget at %.6g K; it is where a reduction pays"
            % (leader, leader_k)
        )
    if absent:
        verdict = INCOMPLETE
    elif not inside or gt_short:
        verdict = OVER_ALLOCATION
    else:
        verdict = COMPLIANT
    return {
        "identified_categories": identified_categories(entries),
        "missing_categories": absent,
        "system_noise_temperature_k": total,
        "allocation_k": allocation,
        "allocation_margin_k": margin,
        "dominant_category": leader,
        "dominant_contribution_k": leader_k,
        "figure_of_merit_db": gt_db,
        "within_allocation": inside,
        "figure_of_merit_short": gt_short,
        "verdict": verdict,
        "findings": tuple(findings),
    }
