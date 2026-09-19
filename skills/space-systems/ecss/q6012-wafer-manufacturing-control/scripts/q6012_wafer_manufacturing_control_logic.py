"""Process monitoring and wafer traceability held during die wafer fabrication.

Anchor: ECSS-Q-ST-60-12C clause 10.2.3 (the monitoring the foundry keeps over
its process, and the traceability it keeps over the wafers, for the whole time
the wafers carrying the dies are being built).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate and normalise the fabrication run record: the lot, the mask set it
   was patterned from, the wafers in it, the monitor readings taken at the
   process steps, the parent links that carry each wafer back to the mask set,
   and any excursions raised while the lot was running.
2. Confirm every step whose monitoring is mandatory actually carries a reading.
   A step with no reading is not an in-band step; it is an unmonitored one.
3. Place each reading in its own control band as a signed position, so a
   reading sitting on the band edge is reported as on the edge rather than
   silently counted as comfortable.
4. Walk every wafer back through its parent links to the mask set, refusing a
   link cycle and reporting a wafer whose chain breaks before it gets there.
5. Confirm every excursion raised during the run carries a recorded
   disposition, and that a disposition still under review is not read as
   closed.
6. Report the monitored and traceable fractions, the findings, and whether the
   lot may be released to acceptance measurement or has to be held.
"""

__all__ = [
    "MONITOR_KINDS",
    "EXCURSION_DISPOSITIONS",
    "OPEN_DISPOSITIONS",
    "STEP_KEYS",
    "MANDATORY_STEPS",
    "step_titles",
    "step_kinds",
    "band_position",
    "monitor_state",
    "validate_run",
    "monitor_report",
    "missing_mandatory_monitors",
    "monitored_fraction",
    "trace_path",
    "traceability_report",
    "traceable_fraction",
    "excursion_findings",
    "control_findings",
    "assess_manufacturing_control",
]

MONITOR_KINDS = (
    "film-thickness",
    "physical-dimension",
    "inline-electrical",
    "defect-density",
)

EXCURSION_DISPOSITIONS = (
    "accepted-as-is",
    "reworked",
    "scrapped",
    "under-review",
)

# A disposition that has not actually disposed of anything. An excursion left
# here is an open item, not a closed one.
OPEN_DISPOSITIONS = ("under-review",)

# key, title, monitor kind, monitoring mandatory on every lot.
_STEP_REGISTRY = (
    ("epitaxy", "Epitaxial layer growth", "film-thickness", True),
    ("lithography", "Mask level lithography", "physical-dimension", True),
    ("pattern-etch", "Pattern etch", "physical-dimension", True),
    ("metallization", "Metal deposition", "film-thickness", True),
    ("passivation", "Passivation deposition", "film-thickness", True),
    ("implant", "Ion implantation", "inline-electrical", False),
    ("backside-thinning", "Backside thinning", "physical-dimension", False),
    ("inline-defect-scan", "Inline defect scan", "defect-density", False),
)

STEP_KEYS = tuple(entry[0] for entry in _STEP_REGISTRY)
MANDATORY_STEPS = tuple(entry[0] for entry in _STEP_REGISTRY if entry[3])

_STEP_INDEX = {key: i for i, key in enumerate(STEP_KEYS)}

_REQUIRED_RUN_KEYS = ("lot_id", "mask_set_id", "wafer_ids", "monitors", "links")
_OPTIONAL_RUN_KEYS = ("excursions",)

# Relative slack used to decide that a reading sits ON a band edge rather than
# just inside or just outside it. The band position is already normalised to
# +/-1, so this is an absolute slack on a normalised quantity.
EDGE_TOLERANCE = 1e-9


def step_titles():
    """Return the process step registry as an ordered key to title mapping."""
    return {entry[0]: entry[1] for entry in _STEP_REGISTRY}


def step_kinds():
    """Return the monitor kind each process step is monitored with."""
    return {entry[0]: entry[2] for entry in _STEP_REGISTRY}


def _as_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number" % label)
    return float(value)


def band_position(value, lower, upper):
    """Return the reading's signed position in its control band.

    -1.0 is the lower control limit, +1.0 the upper, 0.0 the band centre.
    """
    value = _as_number(value, "reading")
    lower = _as_number(lower, "lower control limit")
    upper = _as_number(upper, "upper control limit")
    if not lower < upper:
        raise ValueError(
            "control band is inverted or empty: lower %r is not below upper %r"
            % (lower, upper)
        )
    centre = (lower + upper) / 2.0
    half_width = (upper - lower) / 2.0
    return (value - centre) / half_width


def monitor_state(value, lower, upper, tolerance=EDGE_TOLERANCE):
    """Return where a reading sits: in-band, on-band-edge, below or above band."""
    tolerance = _as_number(tolerance, "tolerance")
    if tolerance < 0.0:
        raise ValueError("tolerance must not be negative")
    position = band_position(value, lower, upper)
    if abs(abs(position) - 1.0) <= tolerance:
        return "on-band-edge"
    if position < -1.0:
        return "below-band"
    if position > 1.0:
        return "above-band"
    return "in-band"


def _validate_identifier(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % label)
    token = value.strip()
    if not token:
        raise ValueError("%s must not be empty" % label)
    return token


def validate_run(spec):
    """Return the normalised fabrication run record built from spec.

    Unknown keys are refused rather than ignored so a misspelt field cannot
    quietly remove a whole monitoring or traceability obligation from the run.
    """
    if not isinstance(spec, dict):
        raise ValueError("fabrication run record must be a mapping")
    for key in _REQUIRED_RUN_KEYS:
        if key not in spec:
            raise ValueError("run record missing required key '%s'" % key)
    allowed = set(_REQUIRED_RUN_KEYS) | set(_OPTIONAL_RUN_KEYS)
    for key in spec:
        if key not in allowed:
            raise ValueError("run record carries unknown key '%s'" % key)

    run = {
        "lot_id": _validate_identifier(spec["lot_id"], "lot_id"),
        "mask_set_id": _validate_identifier(spec["mask_set_id"], "mask_set_id"),
    }

    raw_wafers = spec["wafer_ids"]
    if not isinstance(raw_wafers, (list, tuple)) or not raw_wafers:
        raise ValueError("wafer_ids must be a non-empty sequence")
    wafers = []
    for item in raw_wafers:
        wafer = _validate_identifier(item, "wafer id")
        if wafer in wafers:
            raise ValueError("wafer id '%s' is listed more than once" % wafer)
        wafers.append(wafer)
    run["wafer_ids"] = tuple(wafers)

    raw_monitors = spec["monitors"]
    if not isinstance(raw_monitors, (list, tuple)):
        raise ValueError("monitors must be a sequence of monitor readings")
    monitors = []
    seen_steps = set()
    for entry in raw_monitors:
        if not isinstance(entry, dict):
            raise ValueError("each monitor reading must be a mapping")
        for field in ("step", "value", "lower", "upper"):
            if field not in entry:
                raise ValueError("monitor reading missing field '%s'" % field)
        for field in entry:
            if field not in ("step", "value", "lower", "upper"):
                raise ValueError("monitor reading carries unknown field '%s'" % field)
        step = _validate_identifier(entry["step"], "monitor step").lower()
        if step not in _STEP_INDEX:
            raise ValueError("unknown process step '%s'" % step)
        if step in seen_steps:
            raise ValueError("process step '%s' carries more than one reading" % step)
        seen_steps.add(step)
        lower = _as_number(entry["lower"], "lower control limit")
        upper = _as_number(entry["upper"], "upper control limit")
        if not lower < upper:
            raise ValueError("control band for '%s' is inverted or empty" % step)
        monitors.append(
            {
                "step": step,
                "value": _as_number(entry["value"], "monitor reading"),
                "lower": lower,
                "upper": upper,
            }
        )
    monitors.sort(key=lambda m: _STEP_INDEX[m["step"]])
    run["monitors"] = tuple(monitors)

    raw_links = spec["links"]
    if not isinstance(raw_links, (list, tuple)):
        raise ValueError("links must be a sequence of parent links")
    links = []
    children = set()
    for entry in raw_links:
        if not isinstance(entry, dict):
            raise ValueError("each parent link must be a mapping")
        for field in ("child", "parent"):
            if field not in entry:
                raise ValueError("parent link missing field '%s'" % field)
        for field in entry:
            if field not in ("child", "parent"):
                raise ValueError("parent link carries unknown field '%s'" % field)
        child = _validate_identifier(entry["child"], "link child")
        parent = _validate_identifier(entry["parent"], "link parent")
        if child == parent:
            raise ValueError("node '%s' is declared as its own parent" % child)
        if child in children:
            raise ValueError("node '%s' is given more than one parent" % child)
        children.add(child)
        links.append({"child": child, "parent": parent})
    run["links"] = tuple(links)

    raw_excursions = spec.get("excursions", ())
    if not isinstance(raw_excursions, (list, tuple)):
        raise ValueError("excursions must be a sequence of excursion records")
    excursions = []
    for entry in raw_excursions:
        if not isinstance(entry, dict):
            raise ValueError("each excursion must be a mapping")
        for field in ("step", "disposition"):
            if field not in entry:
                raise ValueError("excursion missing field '%s'" % field)
        for field in entry:
            if field not in ("step", "disposition", "reference"):
                raise ValueError("excursion carries unknown field '%s'" % field)
        step = _validate_identifier(entry["step"], "excursion step").lower()
        if step not in _STEP_INDEX:
            raise ValueError("unknown process step '%s'" % step)
        disposition = _validate_identifier(
            entry["disposition"], "excursion disposition"
        ).lower()
        if disposition not in EXCURSION_DISPOSITIONS:
            raise ValueError(
                "excursion disposition '%s' is not one of %s"
                % (disposition, ", ".join(EXCURSION_DISPOSITIONS))
            )
        reference = entry.get("reference", "")
        if not isinstance(reference, str):
            raise ValueError("excursion reference must be a string")
        excursions.append(
            {"step": step, "disposition": disposition, "reference": reference.strip()}
        )
    run["excursions"] = tuple(excursions)
    return run


def _require_run(run):
    """Refuse anything that is not the output of validate_run.

    A raw spec still carries the same key names, so the check is on the
    normalised shape (immutable sequences) rather than on the names alone.
    """
    if not isinstance(run, dict):
        raise ValueError("run must be a normalised fabrication run record")
    for key in ("lot_id", "mask_set_id", "wafer_ids", "monitors", "links",
                "excursions"):
        if key not in run:
            raise ValueError("run is not normalised: missing '%s'" % key)
    for key in ("wafer_ids", "monitors", "links", "excursions"):
        if not isinstance(run[key], tuple):
            raise ValueError(
                "run is not normalised: '%s' must come from validate_run" % key
            )
    return run


def monitor_report(run):
    """Return one record per monitor reading with its band position and state."""
    _require_run(run)
    titles = step_titles()
    kinds = step_kinds()
    report = []
    for entry in run["monitors"]:
        position = band_position(entry["value"], entry["lower"], entry["upper"])
        report.append(
            {
                "step": entry["step"],
                "title": titles[entry["step"]],
                "kind": kinds[entry["step"]],
                "value": entry["value"],
                "lower": entry["lower"],
                "upper": entry["upper"],
                "position": position,
                "state": monitor_state(entry["value"], entry["lower"], entry["upper"]),
                "mandatory": entry["step"] in MANDATORY_STEPS,
            }
        )
    return report


def missing_mandatory_monitors(run):
    """Return the mandatory process steps the run carries no reading for."""
    _require_run(run)
    present = {entry["step"] for entry in run["monitors"]}
    return [step for step in MANDATORY_STEPS if step not in present]


def monitored_fraction(run):
    """Return the fraction of mandatory steps that carry a reading."""
    _require_run(run)
    present = {entry["step"] for entry in run["monitors"]}
    covered = sum(1 for step in MANDATORY_STEPS if step in present)
    return covered / float(len(MANDATORY_STEPS))


def trace_path(node, parents, root):
    """Return the chain from node up to root, or None when the chain breaks.

    Raises on a link cycle rather than looping or returning a partial chain.
    """
    if not isinstance(parents, dict):
        raise ValueError("parents must be a mapping of child to parent")
    node = _validate_identifier(node, "node")
    root = _validate_identifier(root, "root")
    chain = [node]
    seen = {node}
    current = node
    while current != root:
        if current not in parents:
            return None
        current = parents[current]
        if current in seen:
            raise ValueError("parent links form a cycle at '%s'" % current)
        seen.add(current)
        chain.append(current)
    return chain


def traceability_report(run):
    """Return the wafers whose chain reaches the mask set, and those that break."""
    _require_run(run)
    parents = {link["child"]: link["parent"] for link in run["links"]}
    root = run["mask_set_id"]
    traceable = []
    broken = []
    paths = {}
    for wafer in run["wafer_ids"]:
        chain = trace_path(wafer, parents, root)
        if chain is None:
            broken.append(wafer)
        else:
            traceable.append(wafer)
            paths[wafer] = chain
    return {"traceable": traceable, "broken": broken, "paths": paths, "root": root}


def traceable_fraction(run):
    """Return the fraction of wafers whose chain reaches the mask set."""
    report = traceability_report(run)
    total = len(run["wafer_ids"])
    return len(report["traceable"]) / float(total)


def excursion_findings(run):
    """Return the findings the run's excursion records raise."""
    _require_run(run)
    titles = step_titles()
    findings = []
    monitored = {entry["step"] for entry in run["monitors"]}
    for excursion in run["excursions"]:
        if excursion["disposition"] in OPEN_DISPOSITIONS:
            findings.append(
                "excursion at '%s' is still under review; it is an open item, not a "
                "closed one" % titles[excursion["step"]]
            )
        elif not excursion["reference"]:
            findings.append(
                "excursion at '%s' is dispositioned '%s' with no record reference"
                % (titles[excursion["step"]], excursion["disposition"])
            )
        if excursion["step"] not in monitored:
            findings.append(
                "excursion raised at '%s', a step the run carries no monitor reading for"
                % titles[excursion["step"]]
            )
    return findings


def control_findings(run):
    """Return every finding a reviewer clears before the lot leaves fabrication."""
    _require_run(run)
    titles = step_titles()
    findings = []
    for step in missing_mandatory_monitors(run):
        findings.append(
            "mandatory step '%s' carries no monitor reading; it is unmonitored, "
            "not in band" % titles[step]
        )
    for record in monitor_report(run):
        if record["state"] in ("below-band", "above-band"):
            findings.append(
                "reading at '%s' is %s its control band (position %+0.3f)"
                % (record["title"], record["state"].replace("-band", " the band"),
                   record["position"])
            )
        elif record["state"] == "on-band-edge":
            findings.append(
                "reading at '%s' sits on the control band edge; confirm the "
                "disposition rather than reading it as comfortable" % record["title"]
            )
    trace = traceability_report(run)
    for wafer in trace["broken"]:
        findings.append(
            "wafer '%s' cannot be followed back to mask set '%s'; the traceability "
            "chain is broken" % (wafer, trace["root"])
        )
    findings.extend(excursion_findings(run))
    return findings


def assess_manufacturing_control(spec):
    """Run the full clause 10.2.3 fabrication monitoring and traceability check."""
    run = validate_run(spec)
    findings = control_findings(run)
    return {
        "run": run,
        "monitors": monitor_report(run),
        "missing_monitors": missing_mandatory_monitors(run),
        "traceability": traceability_report(run),
        "monitored_fraction": monitored_fraction(run),
        "traceable_fraction": traceable_fraction(run),
        "open_excursions": [
            e["step"] for e in run["excursions"]
            if e["disposition"] in OPEN_DISPOSITIONS
        ],
        "findings": findings,
        "disposition": "hold" if findings else "release-to-acceptance",
    }
