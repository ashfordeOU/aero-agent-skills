"""Which observed failure modes count against a hybrid lot.

Anchor: ECSS-Q-ST-60-05C clause 10.4.1 (naming the defect types that count
against a batch when rejection thresholds are tallied). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold a catalogue of named failure modes, each placed in a defect group and
   marked as either intrinsic to the delivered product -- its design,
   materials or assembly process -- or extrinsic to it, arising from the test
   setup or from handling after the unit left the process.
2. Charge an intrinsic mode to the lot unconditionally. Charge an extrinsic
   mode too, unless a completed failure analysis evidences the attribution:
   an unevidenced excuse is not an excuse, and an untallied failure quietly
   lowers the percentage the rejection thresholds are applied to.
3. Group a mode name that is not in the catalogue as unattributed and charge
   it, reporting it rather than dropping it.
4. Tally an observation set into charged and uncharged counts, by group and
   by mode, and report the observations still waiting on failure-analysis
   evidence.
"""

__all__ = [
    "DEFECT_GROUPS",
    "FAILURE_MODES",
    "UNATTRIBUTED_GROUP",
    "charged_count",
    "is_chargeable",
    "mode_group",
    "mode_is_intrinsic",
    "normalize_mode",
    "tally_failures",
    "unknown_modes",
    "validate_observations",
]

UNATTRIBUTED_GROUP = "unattributed"

# Catalogue of named failure modes: mode -> (defect group, intrinsic to the
# delivered product). An intrinsic mode is a property of the hardware that was
# built; an extrinsic mode arises from the measurement or from handling after
# the unit left the process.
FAILURE_MODES = {
    "wire-bond-lift": ("interconnection", True),
    "wire-bond-neck-break": ("interconnection", True),
    "wire-bond-intermetallic-void": ("interconnection", True),
    "die-attach-void": ("element-attachment", True),
    "die-attach-delamination": ("element-attachment", True),
    "die-crack": ("element-attachment", True),
    "chip-component-cracked-termination": ("element-attachment", True),
    "substrate-metallization-open": ("substrate", True),
    "substrate-dielectric-short": ("substrate", True),
    "thick-film-resistor-drift": ("substrate", True),
    "seal-fine-leak": ("hermeticity", True),
    "seal-gross-leak": ("hermeticity", True),
    "loose-particle": ("hermeticity", True),
    "electrical-parameter-out-of-limit": ("electrical", True),
    "electrical-functional-failure": ("electrical", True),
    "package-lead-corrosion": ("external", True),
    "test-equipment-fault": ("test-environment", False),
    "test-socket-contact-failure": ("test-environment", False),
    "test-program-error": ("test-environment", False),
    "handling-damage-after-screening": ("post-process-handling", False),
    "external-lead-bend-in-transit": ("post-process-handling", False),
    "marking-legibility-loss-in-transit": ("post-process-handling", False),
}

DEFECT_GROUPS = (
    "interconnection",
    "element-attachment",
    "substrate",
    "hermeticity",
    "electrical",
    "external",
    "test-environment",
    "post-process-handling",
    UNATTRIBUTED_GROUP,
)


def _require_positive_int(value, label):
    """Return value as a positive int, raising on anything that is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def normalize_mode(name):
    """Return a failure mode name normalised for case and separator."""
    if not isinstance(name, str):
        raise ValueError("failure mode must be a string, got %r" % (name,))
    token = name.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in token:
        token = token.replace("--", "-")
    if not token:
        raise ValueError("failure mode must not be blank")
    return token


def mode_group(name):
    """Return the defect group of a catalogued failure mode."""
    token = normalize_mode(name)
    if token not in FAILURE_MODES:
        raise ValueError("failure mode %r is not in the catalogue" % (name,))
    return FAILURE_MODES[token][0]


def mode_is_intrinsic(name):
    """Return whether a catalogued mode is intrinsic to the delivered product."""
    token = normalize_mode(name)
    if token not in FAILURE_MODES:
        raise ValueError("failure mode %r is not in the catalogue" % (name,))
    return FAILURE_MODES[token][1]


def is_chargeable(name, attribution_evidenced=False):
    """Return whether an observed failure counts against the lot.

    An intrinsic mode always counts. An extrinsic mode counts as well unless a
    completed failure analysis evidences the attribution, because an
    unevidenced excuse removes a failure from the tally on assertion alone.
    An uncatalogued mode counts and is reported.
    """
    if not isinstance(attribution_evidenced, bool):
        raise ValueError(
            "attribution_evidenced must be a boolean, got %r" % (attribution_evidenced,)
        )
    token = normalize_mode(name)
    if token not in FAILURE_MODES:
        return True
    if FAILURE_MODES[token][1]:
        return True
    return not attribution_evidenced


def validate_observations(observations):
    """Return the normalised observation records of a screened lot.

    Each observation names a failure mode, how many units showed it, and
    whether a completed failure analysis evidenced the attribution.
    """
    if isinstance(observations, dict) or not isinstance(observations, (list, tuple)):
        raise ValueError("observations must be a sequence of records")
    normalised = []
    for index, record in enumerate(observations):
        if not isinstance(record, dict):
            raise ValueError("observations[%d] must be a mapping" % index)
        if "mode" not in record:
            raise ValueError("observations[%d] needs a 'mode'" % index)
        mode = normalize_mode(record["mode"])
        count = _require_positive_int(record.get("count", 1), "observations[%d]['count']" % index)
        evidenced = record.get("attribution_evidenced", False)
        if not isinstance(evidenced, bool):
            raise ValueError(
                "observations[%d]['attribution_evidenced'] must be a boolean" % index
            )
        catalogued = mode in FAILURE_MODES
        normalised.append(
            {
                "mode": mode,
                "count": count,
                "catalogued": catalogued,
                "group": FAILURE_MODES[mode][0] if catalogued else UNATTRIBUTED_GROUP,
                "intrinsic": FAILURE_MODES[mode][1] if catalogued else None,
                "attribution_evidenced": evidenced,
                "chargeable": is_chargeable(mode, evidenced),
            }
        )
    return normalised


def unknown_modes(observations):
    """Return the observed mode names that are not in the catalogue."""
    seen = []
    for record in validate_observations(observations):
        if not record["catalogued"] and record["mode"] not in seen:
            seen.append(record["mode"])
    return seen


def charged_count(observations):
    """Return the number of failures that count against the lot."""
    return sum(r["count"] for r in validate_observations(observations) if r["chargeable"])


def tally_failures(observations):
    """Tally an observation set for the clause 10.4.1 rejection count.

    Returns the observed and charged totals, the charged count by defect group
    and by mode, the uncatalogued mode names, and the observations excused by
    an evidenced attribution -- so the number the thresholds are applied to can
    be reproduced from the record.
    """
    records = validate_observations(observations)
    by_group = {}
    by_mode = {}
    excused = []
    observed = 0
    charged = 0
    for record in records:
        observed += record["count"]
        if record["chargeable"]:
            charged += record["count"]
            by_group[record["group"]] = by_group.get(record["group"], 0) + record["count"]
            by_mode[record["mode"]] = by_mode.get(record["mode"], 0) + record["count"]
        else:
            excused.append({"mode": record["mode"], "count": record["count"]})
    findings = []
    uncatalogued = unknown_modes(observations)
    if uncatalogued:
        findings.append(
            "uncatalogued failure mode(s) charged pending attribution: %s"
            % ", ".join(uncatalogued)
        )
    unevidenced = [
        r["mode"]
        for r in records
        if r["catalogued"] and r["intrinsic"] is False and not r["attribution_evidenced"]
    ]
    if unevidenced:
        findings.append(
            "extrinsic mode(s) charged because no failure analysis evidenced the "
            "attribution: %s" % ", ".join(sorted(set(unevidenced)))
        )
    return {
        "observed_failures": observed,
        "charged_failures": charged,
        "excused_failures": observed - charged,
        "charged_by_group": sorted(by_group.items(), key=lambda i: (-i[1], i[0])),
        "charged_by_mode": sorted(by_mode.items(), key=lambda i: (-i[1], i[0])),
        "uncatalogued_modes": uncatalogued,
        "excused": excused,
        "findings": findings,
    }
