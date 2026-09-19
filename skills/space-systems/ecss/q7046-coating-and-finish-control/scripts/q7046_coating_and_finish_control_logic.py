"""Coating and finish control for threaded fasteners.

Anchor: ECSS-Q-ST-70-46, materials clause, finish and lubricant control
(paraphrased into an implementable procedure; no standard text is
reproduced).

Procedure implemented here:

1. A finish is screened before it is engineered. Cadmium is barred
   outright for flight hardware, and pure zinc or pure tin deposits
   are barred as whisker sources unless the deposit carries enough
   alloying addition to suppress the growth. A barred finish is
   answered with the permitted substitutes for the same job rather
   than with a refusal.
2. A coating consumes thread clearance. On an external thread the
   pitch diameter grows by four times the deposit thickness, because
   the deposit lands on both flanks and the pitch diameter is measured
   across them; an internal thread shrinks by the same rule. The two
   together have to fit inside the allowance the thread class leaves,
   and the check is run before plating, not after a part will not
   assemble.
3. A lubricant that flies is a vacuum material. The declared mass loss
   and condensable fraction are judged against the outgassing limits,
   and the lubricant service band has to cover the mission band, since
   a dry film that is qualified warm is not qualified cold.
4. A finish is also a friction specification. The preload calculation
   assumed a band of nut factors, so the finish-plus-lubricant pair
   has to deliver one inside that band, and the resulting preload
   scatter is reported as the span it really is.
5. The worst finding on a finish schedule is the schedule
   disposition, because one barred deposit or one thread that will not
   gauge stops the whole build.

Stdlib only, offline, deterministic.
"""

ACCEPTED = "accepted"
ACCEPTED_WITH_CONTROLS = "accepted-with-controls"
REJECTED = "rejected"

_RANK = {ACCEPTED: 0, ACCEPTED_WITH_CONTROLS: 1, REJECTED: 2}

PERMITTED = "permitted"
RESTRICTED = "restricted"
BARRED = "barred"

# Finish register. "restricted" deposits are admissible only when the
# alloying addition reaches the declared minimum mass fraction.
FINISH_REGISTER = {
    "cadmium-plate": {
        "status": BARRED,
        "reason": "cadmium-deposit-barred-for-flight",
        "min_alloy_fraction": None,
    },
    "pure-zinc-plate": {
        "status": RESTRICTED,
        "reason": "zinc-whisker-risk",
        "min_alloy_fraction": 0.03,
    },
    "pure-tin-plate": {
        "status": RESTRICTED,
        "reason": "tin-whisker-risk",
        "min_alloy_fraction": 0.03,
    },
    "zinc-nickel-plate": {"status": PERMITTED, "reason": "", "min_alloy_fraction": None},
    "aluminium-ion-vapour-deposit": {
        "status": PERMITTED,
        "reason": "",
        "min_alloy_fraction": None,
    },
    "passivation-only": {"status": PERMITTED, "reason": "", "min_alloy_fraction": None},
    "chemical-conversion-coat": {
        "status": PERMITTED,
        "reason": "",
        "min_alloy_fraction": None,
    },
    "silver-plate": {"status": PERMITTED, "reason": "", "min_alloy_fraction": None},
    "dry-film-lubricant-coat": {
        "status": PERMITTED,
        "reason": "",
        "min_alloy_fraction": None,
    },
}

VALID_FINISHES = tuple(sorted(FINISH_REGISTER))

# Permitted substitutes offered when a screened finish is barred.
SUBSTITUTES = {
    "cadmium-plate": (
        "zinc-nickel-plate",
        "aluminium-ion-vapour-deposit",
    ),
    "pure-zinc-plate": ("zinc-nickel-plate",),
    "pure-tin-plate": ("silver-plate", "zinc-nickel-plate"),
}

# Lubricant register: service band and declared vacuum behaviour.
LUBRICANT_REGISTER = {
    "molybdenum-disulphide-dry-film": {
        "tml_percent": 0.35,
        "cvcm_percent": 0.01,
        "min_service_c": -200.0,
        "max_service_c": 400.0,
    },
    "ptfe-dry-film": {
        "tml_percent": 0.50,
        "cvcm_percent": 0.02,
        "min_service_c": -180.0,
        "max_service_c": 250.0,
    },
    "silver-film": {
        "tml_percent": 0.05,
        "cvcm_percent": 0.00,
        "min_service_c": -250.0,
        "max_service_c": 500.0,
    },
    "hydrocarbon-grease": {
        "tml_percent": 2.40,
        "cvcm_percent": 0.35,
        "min_service_c": -30.0,
        "max_service_c": 120.0,
    },
    "none": {
        "tml_percent": 0.0,
        "cvcm_percent": 0.0,
        "min_service_c": -273.0,
        "max_service_c": 1000.0,
    },
}

VALID_LUBRICANTS = tuple(sorted(LUBRICANT_REGISTER))

# Vacuum outgassing screening limits, in percent.
TML_LIMIT_PERCENT = 1.00
CVCM_LIMIT_PERCENT = 0.10

# A deposit lands on both flanks, so the pitch diameter moves by four
# times the thickness on each mating thread.
PITCH_DIAMETER_FACTOR = 4.0

# Thicknesses, fractions and nut factors are quotients of measured
# floats, so a case exactly on a limit can land a few units in the last
# place outside it. These absorb that without widening a limit.
LENGTH_TOLERANCE_UM = 1.0e-9
FRACTION_TOLERANCE = 1.0e-12
TEMPERATURE_TOLERANCE_C = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def finish_record(finish):
    """Return the register entry for one finish."""
    if not isinstance(finish, str) or finish not in FINISH_REGISTER:
        raise ValueError(
            "unknown finish %r (expected one of %s)"
            % (finish, ", ".join(VALID_FINISHES))
        )
    return dict(FINISH_REGISTER[finish])


def substitutes_for(finish):
    """Permitted substitutes offered for a screened-out finish."""
    finish_record(finish)
    return list(SUBSTITUTES.get(finish, ()))


def screen_finish(finish, alloy_fraction=0.0):
    """Screen one finish, using the alloying addition where it matters."""
    data = finish_record(finish)
    fraction = _numeric("alloy_fraction", alloy_fraction, 0.0)
    if fraction > 1.0:
        raise ValueError("alloy_fraction is a mass fraction in [0, 1]")
    status = data["status"]
    if status == BARRED:
        return {
            "finish": finish,
            "admissible": False,
            "reason": data["reason"],
            "substitutes": substitutes_for(finish),
        }
    if status == RESTRICTED:
        floor = data["min_alloy_fraction"]
        if fraction + FRACTION_TOLERANCE < floor:
            return {
                "finish": finish,
                "admissible": False,
                "reason": data["reason"],
                "substitutes": substitutes_for(finish),
            }
        return {
            "finish": finish,
            "admissible": True,
            "reason": "alloyed-above-the-whisker-suppression-floor",
            "substitutes": [],
        }
    return {"finish": finish, "admissible": True, "reason": "", "substitutes": []}


def pitch_diameter_consumption_um(external_thickness_um, internal_thickness_um=0.0):
    """Thread-clearance consumed by the two deposits, in micrometres."""
    external = _numeric("external_thickness_um", external_thickness_um, 0.0)
    internal = _numeric("internal_thickness_um", internal_thickness_um, 0.0)
    return PITCH_DIAMETER_FACTOR * (external + internal)


def max_external_thickness_um(allowance_um, internal_thickness_um=0.0):
    """Thickest external deposit the remaining allowance still admits."""
    allowance = _numeric("allowance_um", allowance_um, 0.0)
    internal = _numeric("internal_thickness_um", internal_thickness_um, 0.0)
    remaining = allowance - PITCH_DIAMETER_FACTOR * internal
    if remaining <= 0.0:
        return 0.0
    return remaining / PITCH_DIAMETER_FACTOR


def thread_fit_check(allowance_um, external_thickness_um, internal_thickness_um=0.0):
    """Whether the deposits fit inside the thread-class allowance."""
    allowance = _numeric("allowance_um", allowance_um, 0.0)
    if allowance <= 0.0:
        raise ValueError("allowance_um must be positive")
    consumed = pitch_diameter_consumption_um(
        external_thickness_um, internal_thickness_um
    )
    return {
        "allowance_um": allowance,
        "consumed_um": consumed,
        "remaining_um": allowance - consumed,
        "fits": consumed <= allowance + LENGTH_TOLERANCE_UM,
        "max_external_thickness_um": max_external_thickness_um(
            allowance, internal_thickness_um
        ),
    }


def lubricant_record(lubricant):
    """Return the register entry for one lubricant."""
    if not isinstance(lubricant, str) or lubricant not in LUBRICANT_REGISTER:
        raise ValueError(
            "unknown lubricant %r (expected one of %s)"
            % (lubricant, ", ".join(VALID_LUBRICANTS))
        )
    return dict(LUBRICANT_REGISTER[lubricant])


def outgassing_check(lubricant):
    """Judge a lubricant against the vacuum outgassing limits."""
    data = lubricant_record(lubricant)
    tml_ok = data["tml_percent"] <= TML_LIMIT_PERCENT + FRACTION_TOLERANCE
    cvcm_ok = data["cvcm_percent"] <= CVCM_LIMIT_PERCENT + FRACTION_TOLERANCE
    return {
        "lubricant": lubricant,
        "tml_percent": data["tml_percent"],
        "cvcm_percent": data["cvcm_percent"],
        "tml_within_limit": tml_ok,
        "cvcm_within_limit": cvcm_ok,
        "acceptable": tml_ok and cvcm_ok,
    }


def lubricant_temperature_coverage(lubricant, mission_min_c, mission_max_c):
    """Whether the lubricant band covers the mission band at both ends."""
    data = lubricant_record(lubricant)
    low = _numeric("mission_min_c", mission_min_c)
    high = _numeric("mission_max_c", mission_max_c)
    if high < low:
        raise ValueError("mission_max_c must not sit below mission_min_c")
    return {
        "cold_end_covered": low >= data["min_service_c"] - TEMPERATURE_TOLERANCE_C,
        "hot_end_covered": high <= data["max_service_c"] + TEMPERATURE_TOLERANCE_C,
    }


def preload_band_n(torque_nm, diameter_mm, nut_factor_min, nut_factor_max):
    """Preload span a torque delivers across the declared nut-factor band."""
    torque = _numeric("torque_nm", torque_nm, 0.0)
    if torque <= 0.0:
        raise ValueError("torque_nm must be positive")
    diameter = _numeric("diameter_mm", diameter_mm, 0.0)
    if diameter <= 0.0:
        raise ValueError("diameter_mm must be positive")
    k_min = _numeric("nut_factor_min", nut_factor_min, 0.0)
    k_max = _numeric("nut_factor_max", nut_factor_max, 0.0)
    if k_min <= 0.0 or k_max <= 0.0:
        raise ValueError("nut factors must be positive")
    if k_max < k_min:
        raise ValueError("nut_factor_max must not sit below nut_factor_min")
    diameter_m = diameter / 1000.0
    lowest = torque / (k_max * diameter_m)
    highest = torque / (k_min * diameter_m)
    mean = 0.5 * (lowest + highest)
    return {
        "preload_min_n": lowest,
        "preload_max_n": highest,
        "preload_mean_n": mean,
        "scatter_fraction": (highest - lowest) / (highest + lowest),
    }


def validate_finish_application(record):
    """Validate one finish application and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("finish application must be a mapping")
    part = record.get("part_number")
    if not isinstance(part, str) or not part.strip():
        raise ValueError("finish application needs a non-empty part_number")
    finish = record.get("finish")
    finish_record(finish)
    lubricant = record.get("lubricant", "none")
    lubricant_record(lubricant)
    return {
        "part_number": part.strip(),
        "finish": finish,
        "alloy_fraction": _numeric(
            "alloy_fraction", record.get("alloy_fraction", 0.0), 0.0
        ),
        "lubricant": lubricant,
        "allowance_um": _numeric(
            "allowance_um", record.get("allowance_um", 40.0), 0.0
        ),
        "external_thickness_um": _numeric(
            "external_thickness_um", record.get("external_thickness_um", 5.0), 0.0
        ),
        "internal_thickness_um": _numeric(
            "internal_thickness_um", record.get("internal_thickness_um", 0.0), 0.0
        ),
        "mission_min_c": _numeric("mission_min_c", record.get("mission_min_c", 20.0)),
        "mission_max_c": _numeric("mission_max_c", record.get("mission_max_c", 20.0)),
        "nut_factor_min": _numeric(
            "nut_factor_min", record.get("nut_factor_min", 0.15), 0.0
        ),
        "nut_factor_max": _numeric(
            "nut_factor_max", record.get("nut_factor_max", 0.22), 0.0
        ),
        "torque_nm": _numeric("torque_nm", record.get("torque_nm", 20.0), 0.0),
        "diameter_mm": _numeric("diameter_mm", record.get("diameter_mm", 8.0), 0.0),
        "assumed_scatter_fraction": _numeric(
            "assumed_scatter_fraction", record.get("assumed_scatter_fraction", 0.25), 0.0
        ),
    }


def assess_finish_application(record):
    """Assess one finish application end to end."""
    norm = validate_finish_application(record)
    findings = []
    controls = []
    disposition = ACCEPTED

    def escalate(level):
        if _RANK[level] > _RANK[disposition]:
            return level
        return disposition

    screen = screen_finish(norm["finish"], norm["alloy_fraction"])
    if not screen["admissible"]:
        findings.append("finish-screened-out-%s" % screen["reason"])
        disposition = escalate(REJECTED)
    elif screen["reason"]:
        controls.append("verify-the-alloying-addition-on-every-batch")
        disposition = escalate(ACCEPTED_WITH_CONTROLS)

    fit = thread_fit_check(
        norm["allowance_um"],
        norm["external_thickness_um"],
        norm["internal_thickness_um"],
    )
    if not fit["fits"]:
        findings.append("deposit-consumes-more-than-the-thread-allowance")
        disposition = escalate(REJECTED)

    outgassing = outgassing_check(norm["lubricant"])
    if not outgassing["acceptable"]:
        findings.append("lubricant-above-the-outgassing-limits")
        disposition = escalate(REJECTED)

    coverage = lubricant_temperature_coverage(
        norm["lubricant"], norm["mission_min_c"], norm["mission_max_c"]
    )
    if not coverage["cold_end_covered"]:
        findings.append("lubricant-cold-end-not-qualified")
        disposition = escalate(REJECTED)
    if not coverage["hot_end_covered"]:
        findings.append("lubricant-hot-end-not-qualified")
        disposition = escalate(REJECTED)

    preload = preload_band_n(
        norm["torque_nm"],
        norm["diameter_mm"],
        norm["nut_factor_min"],
        norm["nut_factor_max"],
    )
    if preload["scatter_fraction"] > norm["assumed_scatter_fraction"] + FRACTION_TOLERANCE:
        findings.append("preload-scatter-wider-than-the-joint-assumed")
        disposition = escalate(ACCEPTED_WITH_CONTROLS)
        controls.append("re-run-the-preload-window-on-the-measured-nut-factor")

    return {
        "part_number": norm["part_number"],
        "finish": norm["finish"],
        "lubricant": norm["lubricant"],
        "screen": screen,
        "thread_fit": fit,
        "outgassing": outgassing,
        "temperature_coverage": coverage,
        "preload": preload,
        "controls": controls,
        "findings": findings,
        "disposition": disposition,
    }


def assess_finish_schedule(records):
    """Assess every finish application on a build and roll them up."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_finish_application(record)
        if result["part_number"] in seen:
            raise ValueError("duplicate part %r" % (result["part_number"],))
        seen.add(result["part_number"])
        results.append(result)
    schedule = ACCEPTED
    for result in results:
        if _RANK[result["disposition"]] > _RANK[schedule]:
            schedule = result["disposition"]
    return {
        "applications": results,
        "schedule_disposition": schedule,
        "rejected_parts": [
            r["part_number"] for r in results if r["disposition"] == REJECTED
        ],
        "substitutions_offered": {
            r["part_number"]: r["screen"]["substitutes"]
            for r in results
            if r["screen"]["substitutes"]
        },
    }
