"""Issue decision for a certificate of test covering a metallic material lot.

Anchor: ECSS-Q-ST-70-45 reporting clause (certificates of test issued per lot
or per heat once the mechanical testing behind them is complete). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Group the tested specimens by the heat they were cut from. A certificate
   covers exactly one heat, so a delivery spanning two heats owes two
   certificates and never one averaged over both.
2. Size the sampling each heat owes from the product form and the mass
   released: a base number of specimens per heat plus one more for every
   started mass increment, capped so a large release does not demand an
   unbounded programme.
3. Count only valid specimens towards that number. A specimen voided for an
   out-of-gauge fracture or a machine fault is a test that was run, not a test
   that counts.
4. Judge every counted specimen against the specification minimum rather than
   the heat mean, and report the governing (lowest) value alongside the mean
   so the reader can see how close the heat ran.
5. Build a deterministic certificate reference per heat and return one issue
   verdict per heat with the findings that block it.
"""

import math

__all__ = [
    "BASE_SPECIMENS_PER_HEAT",
    "MASS_INCREMENT_KG",
    "MAX_SPECIMENS_PER_HEAT",
    "PRODUCT_FORM_UPLIFT",
    "MARGIN_TOLERANCE_MPA",
    "product_forms",
    "required_specimen_count",
    "group_specimens_by_heat",
    "valid_specimens",
    "heat_statistics",
    "certificate_reference",
    "assess_heat",
    "assess_certificate_issue",
]

# A heat owes this many specimens before any mass uplift is applied.
BASE_SPECIMENS_PER_HEAT = 2

# One further specimen is owed for every started increment of released mass.
MASS_INCREMENT_KG = 1000.0

# The sampling is capped: past this point more specimens buy no more evidence
# about the heat than the scatter already shows.
MAX_SPECIMENS_PER_HEAT = 8

# Forms whose properties vary with position or direction owe extra specimens.
PRODUCT_FORM_UPLIFT = {
    "bar": 0,
    "rod": 0,
    "sheet": 1,
    "plate": 1,
    "extrusion": 1,
    "forging": 2,
    "casting": 2,
}

# A property landing exactly on the specification minimum passes; absorb the
# representation error here rather than by relaxing the specification.
MARGIN_TOLERANCE_MPA = 1e-9


def product_forms():
    """Return the sorted product forms this sampling rule is defined for."""
    return sorted(PRODUCT_FORM_UPLIFT)


def _clean_token(value, label):
    """Return a non-empty lowercase token, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _positive(value, label):
    """Return a strictly positive finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def required_specimen_count(product_form, released_mass_kg):
    """Return the number of valid specimens one heat of this release owes."""
    form = _clean_token(product_form, "product_form")
    if form not in PRODUCT_FORM_UPLIFT:
        raise ValueError(
            "unknown product form %r; known forms are %s"
            % (product_form, ", ".join(product_forms()))
        )
    mass = _positive(released_mass_kg, "released_mass_kg")
    uplift = int(math.ceil(mass / MASS_INCREMENT_KG)) - 1
    count = BASE_SPECIMENS_PER_HEAT + PRODUCT_FORM_UPLIFT[form] + uplift
    return min(count, MAX_SPECIMENS_PER_HEAT)


def group_specimens_by_heat(specimens):
    """Return the specimens grouped by heat identifier, order preserved."""
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("specimens must be a non-empty sequence of specimen records")
    grouped = {}
    order = []
    seen_ids = set()
    for index, record in enumerate(specimens):
        if not isinstance(record, dict):
            raise ValueError("specimens[%d] must be a mapping" % index)
        for key in ("id", "heat", "value_mpa"):
            if key not in record:
                raise ValueError("specimens[%d] missing required key '%s'" % (index, key))
        identifier = _clean_token(record["id"], "specimens[%d]['id']" % index)
        if identifier in seen_ids:
            raise ValueError("specimen identifier %r appears twice" % identifier)
        seen_ids.add(identifier)
        heat = _clean_token(record["heat"], "specimens[%d]['heat']" % index)
        value = _positive(record["value_mpa"], "specimens[%d]['value_mpa']" % index)
        valid = record.get("valid", True)
        if not isinstance(valid, bool):
            raise ValueError("specimens[%d]['valid'] must be a boolean" % index)
        entry = {"id": identifier, "heat": heat, "value_mpa": value, "valid": valid}
        if heat not in grouped:
            grouped[heat] = []
            order.append(heat)
        grouped[heat].append(entry)
    return [(heat, grouped[heat]) for heat in order]


def valid_specimens(entries):
    """Return only the entries whose test was not voided."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of specimen entries")
    kept = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or "valid" not in entry:
            raise ValueError("entries[%d] must be a specimen entry carrying 'valid'" % index)
        if entry["valid"]:
            kept.append(entry)
    return kept


def heat_statistics(entries):
    """Return the governing minimum, the mean and the count of valid entries."""
    kept = valid_specimens(entries)
    if not kept:
        raise ValueError("no valid specimen remains; nothing can be certified")
    values = [entry["value_mpa"] for entry in kept]
    total = 0.0
    for value in values:
        total += value
    return {
        "count": len(values),
        "minimum_mpa": min(values),
        "maximum_mpa": max(values),
        "mean_mpa": total / len(values),
        "governing_id": min(kept, key=lambda e: e["value_mpa"])["id"],
    }


def certificate_reference(laboratory_code, heat, issue_date):
    """Return the deterministic certificate reference for one heat.

    issue_date is an (year, month, day) triple.
    """
    lab = _clean_token(laboratory_code, "laboratory_code").upper()
    heat_token = _clean_token(heat, "heat").upper()
    if not isinstance(issue_date, (list, tuple)) or len(issue_date) != 3:
        raise ValueError("issue_date must be a (year, month, day) triple")
    year, month, day = issue_date
    for label, value, low, high in (
        ("year", year, 1957, 9999),
        ("month", month, 1, 12),
        ("day", day, 1, 31),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("issue_date %s must be an integer" % label)
        if value < low or value > high:
            raise ValueError("issue_date %s %d is out of range" % (label, value))
    safe_lab = "".join(ch for ch in lab if ch.isalnum())
    safe_heat = "".join(ch for ch in heat_token if ch.isalnum())
    if not safe_lab or not safe_heat:
        raise ValueError("laboratory code and heat must contain alphanumeric characters")
    return "COT-%s-%s-%04d%02d%02d" % (safe_lab, safe_heat, year, month, day)


def assess_heat(heat, entries, product_form, released_mass_kg,
                specified_minimum_mpa, laboratory_code, issue_date):
    """Return the certificate record and issue verdict for a single heat."""
    heat_token = _clean_token(heat, "heat")
    owed = required_specimen_count(product_form, released_mass_kg)
    minimum = _positive(specified_minimum_mpa, "specified_minimum_mpa")
    findings = []
    kept = valid_specimens(entries)
    voided = len(entries) - len(kept)
    if not kept:
        return {
            "heat": heat_token,
            "reference": None,
            "required_specimens": owed,
            "valid_specimens": 0,
            "voided_specimens": voided,
            "statistics": None,
            "specified_minimum_mpa": minimum,
            "findings": ["heat %s has no valid specimen; nothing can be certified"
                         % heat_token],
            "issuable": False,
        }
    stats = heat_statistics(entries)
    if stats["count"] < owed:
        findings.append(
            "heat %s carries %d valid specimens against the %d this release owes"
            % (heat_token, stats["count"], owed)
        )
    below = [
        entry["id"]
        for entry in kept
        if entry["value_mpa"] < minimum
        and not math.isclose(entry["value_mpa"], minimum,
                             rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_MPA)
    ]
    for identifier in below:
        findings.append(
            "specimen %s of heat %s is below the specified minimum %g MPa"
            % (identifier, heat_token, minimum)
        )
    return {
        "heat": heat_token,
        "reference": certificate_reference(laboratory_code, heat_token, issue_date),
        "required_specimens": owed,
        "valid_specimens": stats["count"],
        "voided_specimens": voided,
        "statistics": stats,
        "specified_minimum_mpa": minimum,
        "findings": findings,
        "issuable": not findings,
    }


def assess_certificate_issue(release):
    """Run the full per-heat certificate-of-test issue decision.

    release keys: specimens, product_form, released_mass_kg,
    specified_minimum_mpa, laboratory_code, issue_date.
    """
    if not isinstance(release, dict):
        raise ValueError("release must be a mapping")
    for key in ("specimens", "product_form", "released_mass_kg",
                "specified_minimum_mpa", "laboratory_code", "issue_date"):
        if key not in release:
            raise ValueError("release missing required key '%s'" % key)
    grouped = group_specimens_by_heat(release["specimens"])
    certificates = []
    for heat, entries in grouped:
        certificates.append(
            assess_heat(
                heat,
                entries,
                release["product_form"],
                release["released_mass_kg"],
                release["specified_minimum_mpa"],
                release["laboratory_code"],
                release["issue_date"],
            )
        )
    findings = []
    if len(certificates) > 1:
        findings.append(
            "release spans %d heats; each owes its own certificate and none may be "
            "averaged across them" % len(certificates)
        )
    for certificate in certificates:
        findings.extend(certificate["findings"])
    return {
        "heats": [certificate["heat"] for certificate in certificates],
        "certificates": certificates,
        "certificate_count": len(certificates),
        "findings": findings,
        "all_issuable": all(certificate["issuable"] for certificate in certificates),
    }
