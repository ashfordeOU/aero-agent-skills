"""Test-sample representativeness for a photovoltaic assembly humidity test.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.4.3 (humidity test -- test sample: the
specimen is built from flight-equivalent materials using qualified processes).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the flight stack-up and the specimen stack-up of the photovoltaic
   assembly -- ordered layers, each carrying a material specification, a
   thickness and the process that lays it down.
2. Walk the two stack-ups layer by layer and record every deviation: a flight
   layer the specimen omits, a layer the specimen adds, a material swapped for
   one that is not an approved equivalent, a thickness outside the agreed
   relative band, and a layer built out of sequence.
3. Reduce the walk to a representativeness fraction: the share of flight layers
   the specimen reproduces with flight-equivalent material and thickness.
4. Check every process the specimen uses is on the qualified-process list and
   that its qualification was valid on the specimen build date.
5. Check the specimen count reaches the agreed minimum, so the humidity
   exposure is not judged on a single coupon.
6. Report the deviations, the approved substitutions, the process findings and
   a single verdict on whether the specimen may stand in for the flight build.
"""

import datetime
import math

__all__ = [
    "DEFAULT_THICKNESS_TOLERANCE_REL",
    "DEFAULT_MINIMUM_SPECIMENS",
    "DEFAULT_REQUIRED_REPRESENTATIVENESS",
    "REPRESENTATIVENESS_TOLERANCE",
    "validate_iso_date",
    "validate_layer",
    "validate_stackup",
    "normalize_equivalents",
    "thickness_within_band",
    "compare_stackups",
    "representativeness_fraction",
    "process_findings",
    "assess_test_sample",
]

# Agreed relative band on a layer thickness before the specimen stops standing
# in for the flight build; encapsulant and adhesive thickness drive moisture
# diffusion time, so the band is tight.
DEFAULT_THICKNESS_TOLERANCE_REL = 0.05

# A humidity verdict taken on one coupon has no spread; the agreed floor is a
# small population.
DEFAULT_MINIMUM_SPECIMENS = 3

# By default every flight layer has to be reproduced.
DEFAULT_REQUIRED_REPRESENTATIVENESS = 1.0

# The representativeness fraction is a ratio of small counts, and the band
# check is a product of floats. Both can land a few ULP either side of their
# limit, so the comparisons absorb that instead of moving the limit.
REPRESENTATIVENESS_TOLERANCE = 1e-9

_LAYER_KEYS = ("layer", "material_spec", "thickness_mm", "process")


def validate_iso_date(value, label):
    """Return an ISO-8601 calendar date parsed from value."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO-8601 date string (YYYY-MM-DD)" % label)
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not a valid ISO-8601 date: %r" % (label, value))


def validate_layer(layer, index, source):
    """Return one validated stack-up layer."""
    if not isinstance(layer, dict):
        raise ValueError("%s layer %d must be a mapping" % (source, index))
    for key in _LAYER_KEYS:
        if key not in layer:
            raise ValueError("%s layer %d is missing '%s'" % (source, index, key))
    for key in ("layer", "material_spec", "process"):
        value = layer[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "%s layer %d '%s' must be a non-empty identifier" % (source, index, key)
            )
    thickness = layer["thickness_mm"]
    if not isinstance(thickness, (int, float)) or isinstance(thickness, bool):
        raise ValueError("%s layer %d thickness_mm must be a real number" % (source, index))
    thickness = float(thickness)
    if not math.isfinite(thickness) or thickness <= 0.0:
        raise ValueError(
            "%s layer %d thickness_mm must be positive and finite, got %r"
            % (source, index, layer["thickness_mm"])
        )
    return {
        "layer": layer["layer"].strip(),
        "material_spec": layer["material_spec"].strip(),
        "thickness_mm": thickness,
        "process": layer["process"].strip(),
        "index": index,
    }


def validate_stackup(layers, source):
    """Return the validated, ordered stack-up of a build."""
    if not isinstance(layers, (list, tuple)) or not layers:
        raise ValueError("%s stack-up must be a non-empty sequence of layers" % source)
    validated = [validate_layer(item, i, source) for i, item in enumerate(layers)]
    names = [item["layer"] for item in validated]
    if len(set(names)) != len(names):
        raise ValueError("%s stack-up layer names must be unique, got %r" % (source, names))
    return validated


def normalize_equivalents(approved_equivalents):
    """Return the approved-equivalent map as flight spec -> set of specs."""
    if approved_equivalents is None:
        return {}
    if not isinstance(approved_equivalents, dict):
        raise ValueError("approved_equivalents must be a mapping of spec to specs")
    table = {}
    for flight_spec, alternatives in approved_equivalents.items():
        if not isinstance(flight_spec, str) or not flight_spec.strip():
            raise ValueError("approved_equivalents keys must be non-empty specs")
        if isinstance(alternatives, str):
            alternatives = [alternatives]
        if not isinstance(alternatives, (list, tuple, set)) or not alternatives:
            raise ValueError(
                "approved_equivalents['%s'] must list at least one alternative"
                % flight_spec
            )
        entries = set()
        for alternative in alternatives:
            if not isinstance(alternative, str) or not alternative.strip():
                raise ValueError(
                    "approved_equivalents['%s'] holds a non-string alternative"
                    % flight_spec
                )
            entries.add(alternative.strip())
        table[flight_spec.strip()] = entries
    return table


def thickness_within_band(specimen_mm, flight_mm, tolerance_rel=DEFAULT_THICKNESS_TOLERANCE_REL):
    """Return True when the specimen thickness sits inside the agreed band."""
    for label, value in (("specimen_mm", specimen_mm), ("flight_mm", flight_mm)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    if not isinstance(tolerance_rel, (int, float)) or isinstance(tolerance_rel, bool):
        raise ValueError("tolerance_rel must be a real number")
    tolerance_rel = float(tolerance_rel)
    if not math.isfinite(tolerance_rel) or tolerance_rel < 0.0:
        raise ValueError("tolerance_rel must be non-negative and finite")
    deviation = abs(float(specimen_mm) - float(flight_mm))
    limit = float(flight_mm) * tolerance_rel
    if math.isclose(deviation, limit, rel_tol=REPRESENTATIVENESS_TOLERANCE, abs_tol=0.0):
        return True
    return deviation < limit


def compare_stackups(flight_stackup, specimen_stackup, approved_equivalents=None,
                     thickness_tolerance_rel=DEFAULT_THICKNESS_TOLERANCE_REL):
    """Walk the two stack-ups and return the deviation and substitution records."""
    flight = validate_stackup(flight_stackup, "flight")
    specimen = validate_stackup(specimen_stackup, "specimen")
    equivalents = normalize_equivalents(approved_equivalents)
    specimen_by_name = dict((item["layer"], item) for item in specimen)

    deviations = []
    substitutions = []
    representative = 0
    for flight_layer in flight:
        name = flight_layer["layer"]
        match = specimen_by_name.get(name)
        if match is None:
            deviations.append(
                {"layer": name, "kind": "missing-layer",
                 "detail": "the specimen omits this flight layer"}
            )
            continue
        layer_ok = True
        if match["index"] != flight_layer["index"]:
            deviations.append(
                {"layer": name, "kind": "sequence-deviation",
                 "detail": "built at position %d against flight position %d"
                           % (match["index"], flight_layer["index"])}
            )
            layer_ok = False
        if match["material_spec"] != flight_layer["material_spec"]:
            if match["material_spec"] in equivalents.get(flight_layer["material_spec"], set()):
                substitutions.append(
                    {"layer": name, "flight_spec": flight_layer["material_spec"],
                     "specimen_spec": match["material_spec"]}
                )
            else:
                deviations.append(
                    {"layer": name, "kind": "material-substitution",
                     "detail": "%s built with %s, which is not an approved equivalent"
                               % (flight_layer["material_spec"], match["material_spec"])}
                )
                layer_ok = False
        if not thickness_within_band(
            match["thickness_mm"], flight_layer["thickness_mm"], thickness_tolerance_rel
        ):
            deviations.append(
                {"layer": name, "kind": "thickness-deviation",
                 "detail": "%.4f mm against a flight %.4f mm"
                           % (match["thickness_mm"], flight_layer["thickness_mm"])}
            )
            layer_ok = False
        if layer_ok:
            representative += 1

    flight_names = set(item["layer"] for item in flight)
    for specimen_layer in specimen:
        if specimen_layer["layer"] not in flight_names:
            deviations.append(
                {"layer": specimen_layer["layer"], "kind": "extra-layer",
                 "detail": "the specimen adds a layer the flight build does not carry"}
            )

    return {
        "flight_layer_count": len(flight),
        "representative_layer_count": representative,
        "deviations": deviations,
        "substitutions": substitutions,
    }


def representativeness_fraction(representative_layers, flight_layers):
    """Return the share of flight layers the specimen reproduces."""
    for label, value in (
        ("representative_layers", representative_layers),
        ("flight_layers", flight_layers),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer" % label)
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (label, value))
    if flight_layers == 0:
        raise ValueError("flight_layers must be positive to form a fraction")
    if representative_layers > flight_layers:
        raise ValueError(
            "representative_layers %d exceeds flight_layers %d"
            % (representative_layers, flight_layers)
        )
    return float(representative_layers) / float(flight_layers)


def process_findings(specimen_stackup, qualified_processes, build_date):
    """Return a finding for every specimen process that is not qualified on the build date."""
    specimen = validate_stackup(specimen_stackup, "specimen")
    if not isinstance(qualified_processes, dict) or not qualified_processes:
        raise ValueError("qualified_processes must be a non-empty mapping")
    built_on = validate_iso_date(build_date, "build_date")
    findings = []
    seen = set()
    for layer in specimen:
        process = layer["process"]
        if process in seen:
            continue
        seen.add(process)
        record = qualified_processes.get(process)
        if record is None:
            findings.append(
                {"process": process, "kind": "unqualified-process",
                 "detail": "no qualification record for the process laying '%s'"
                           % layer["layer"]}
            )
            continue
        if not isinstance(record, dict) or "valid_from" not in record or "valid_to" not in record:
            raise ValueError(
                "qualified_processes['%s'] must carry 'valid_from' and 'valid_to'" % process
            )
        valid_from = validate_iso_date(record["valid_from"], "valid_from of '%s'" % process)
        valid_to = validate_iso_date(record["valid_to"], "valid_to of '%s'" % process)
        if valid_to < valid_from:
            raise ValueError(
                "qualification window of '%s' ends before it starts" % process
            )
        if built_on < valid_from:
            findings.append(
                {"process": process, "kind": "premature-qualification",
                 "detail": "specimen built before the qualification of '%s' opened" % process}
            )
        elif built_on > valid_to:
            findings.append(
                {"process": process, "kind": "lapsed-qualification",
                 "detail": "qualification of '%s' had lapsed on the build date" % process}
            )
    return findings


def assess_test_sample(spec):
    """Run the full clause 5.5.1.4.3 test-sample assessment.

    spec keys: flight_stackup, specimen_stackup, qualified_processes, build_date,
    specimen_count, optional approved_equivalents, thickness_tolerance_rel,
    minimum_specimens and required_representativeness.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "flight_stackup",
        "specimen_stackup",
        "qualified_processes",
        "build_date",
        "specimen_count",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    count = spec["specimen_count"]
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("specimen_count must be an integer")
    if count <= 0:
        raise ValueError("specimen_count must be positive, got %d" % count)
    minimum = spec.get("minimum_specimens", DEFAULT_MINIMUM_SPECIMENS)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum <= 0:
        raise ValueError("minimum_specimens must be a positive integer")
    threshold = spec.get("required_representativeness", DEFAULT_REQUIRED_REPRESENTATIVENESS)
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ValueError("required_representativeness must be a real number")
    threshold = float(threshold)
    if not math.isfinite(threshold) or threshold <= 0.0 or threshold > 1.0:
        raise ValueError(
            "required_representativeness must sit in (0, 1], got %r"
            % (spec["required_representativeness"],)
        )

    walk = compare_stackups(
        spec["flight_stackup"],
        spec["specimen_stackup"],
        spec.get("approved_equivalents"),
        spec.get("thickness_tolerance_rel", DEFAULT_THICKNESS_TOLERANCE_REL),
    )
    fraction = representativeness_fraction(
        walk["representative_layer_count"], walk["flight_layer_count"]
    )
    processes = process_findings(
        spec["specimen_stackup"], spec["qualified_processes"], spec["build_date"]
    )

    findings = []
    for deviation in walk["deviations"]:
        findings.append("%s: %s (%s)" % (deviation["layer"], deviation["detail"],
                                         deviation["kind"]))
    for finding in processes:
        findings.append("%s: %s (%s)" % (finding["process"], finding["detail"],
                                         finding["kind"]))
    meets_fraction = fraction > threshold or math.isclose(
        fraction, threshold, rel_tol=REPRESENTATIVENESS_TOLERANCE, abs_tol=0.0
    )
    if not meets_fraction:
        findings.append(
            "specimen reproduces %.3f of the flight stack-up against a required %.3f"
            % (fraction, threshold)
        )
    if count < minimum:
        findings.append(
            "specimen count %d is below the agreed minimum of %d" % (count, minimum)
        )

    return {
        "flight_layer_count": walk["flight_layer_count"],
        "representative_layer_count": walk["representative_layer_count"],
        "representativeness": fraction,
        "required_representativeness": threshold,
        "deviations": walk["deviations"],
        "substitutions": walk["substitutions"],
        "process_findings": processes,
        "specimen_count": count,
        "flight_representative": not findings,
        "findings": findings,
    }
