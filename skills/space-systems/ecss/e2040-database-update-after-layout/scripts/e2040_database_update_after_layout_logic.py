"""Device database update at the close of the layout phase.

Anchor: ECSS-E-ST-20-40C clause 5.6.5 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Derive what the layout phase owes the device repository. Design-wide
   items are owed once. Technology-dependent items -- the post-layout
   netlist, the extracted layout timing data, the place-and-route
   record and, for a programmable device, the configuration bitstream
   -- are owed once for every implementation technology the device
   uses.
2. Validate each deposited item and match it against the owed set,
   pairing a technology-dependent deposit with its technology.
3. Check every matched deposit against the layout run the phase is
   closing on: a deposit from an earlier run is superseded, a deposit
   from a later run is out of phase.
4. Check configuration attributes: configuration identifier, integrity
   digest, and no second deposit of the same kind and technology.
5. Report completeness as the fraction of owed entries satisfied by a
   clean deposit, with the gaps and the findings named.

Stdlib only, offline, deterministic.
"""

KIND_POST_LAYOUT_NETLIST = "post-layout-netlist"
KIND_LAYOUT_TIMING_DATA = "layout-timing-data"
KIND_PLACE_AND_ROUTE_RECORD = "place-and-route-record"
KIND_CONFIGURATION_BITSTREAM = "configuration-bitstream"
KIND_LAYOUT_VERIFICATION_REPORT = "layout-verification-report"
KIND_CONSOLIDATED_VALIDATION_PLAN = "consolidated-validation-plan"
KIND_UPDATED_DEVICE_DATA_SHEET = "updated-device-data-sheet"

# Owed once per implementation technology.
TECHNOLOGY_DEPENDENT_KINDS = (
    KIND_POST_LAYOUT_NETLIST,
    KIND_LAYOUT_TIMING_DATA,
    KIND_PLACE_AND_ROUTE_RECORD,
)

# Owed once per implementation technology, and only for a device whose
# implementation is loaded rather than fabricated.
PROGRAMMABLE_ONLY_KINDS = (KIND_CONFIGURATION_BITSTREAM,)

# Owed once for the device, whatever the technology count.
DESIGN_WIDE_KINDS = (
    KIND_LAYOUT_VERIFICATION_REPORT,
    KIND_CONSOLIDATED_VALIDATION_PLAN,
    KIND_UPDATED_DEVICE_DATA_SHEET,
)

VALID_KINDS = (
    TECHNOLOGY_DEPENDENT_KINDS + PROGRAMMABLE_ONLY_KINDS + DESIGN_WIDE_KINDS
)

DEVICE_KIND_ASIC = "asic"
DEVICE_KIND_FPGA = "fpga"
DEVICE_KIND_IP_CORE = "ip-core"
VALID_DEVICE_KINDS = (DEVICE_KIND_ASIC, DEVICE_KIND_FPGA, DEVICE_KIND_IP_CORE)

# A loaded implementation carries a configuration bitstream; a
# fabricated one does not, and an IP core is delivered as source and
# has neither.
PROGRAMMABLE_DEVICE_KINDS = (DEVICE_KIND_FPGA,)

FINDING_MISSING_DEPOSIT = "owed-item-not-deposited"
FINDING_SUPERSEDED_RUN = "deposit-from-superseded-layout-run"
FINDING_OUT_OF_PHASE_RUN = "deposit-from-a-run-after-the-closing-run"
FINDING_NO_CONFIGURATION_ID = "deposit-without-configuration-identifier"
FINDING_NO_DIGEST = "deposit-without-integrity-digest"
FINDING_DUPLICATE_DEPOSIT = "second-deposit-for-the-same-owed-entry"
FINDING_UNEXPECTED_DEPOSIT = "deposit-outside-the-owed-set"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _sequence_number(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def validate_device(device):
    """Validate the device record and return a normalized copy."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping")
    device_id = _text("device id", device.get("id"))
    kind = device.get("kind")
    if kind not in VALID_DEVICE_KINDS:
        raise ValueError(
            "device %s has unknown kind %r (expected one of %s)"
            % (device_id, kind, ", ".join(VALID_DEVICE_KINDS))
        )
    technologies = device.get("technologies")
    if not isinstance(technologies, (list, tuple)) or not technologies:
        raise ValueError("device %s needs a non-empty technologies list" % device_id)
    normalized = []
    for item in technologies:
        name = _text("device %s technology" % device_id, item)
        if name in normalized:
            raise ValueError("device %s lists technology %r twice" % (device_id, name))
        normalized.append(name)
    closing_run = _sequence_number(
        "device %s closing_layout_run" % device_id, device.get("closing_layout_run", 1)
    )
    return {
        "id": device_id,
        "kind": kind,
        "technologies": normalized,
        "closing_layout_run": closing_run,
    }


def is_programmable(device):
    """True when the device is loaded with a configuration bitstream."""
    return validate_device(device)["kind"] in PROGRAMMABLE_DEVICE_KINDS


def owed_entries(device):
    """The (kind, technology) entries the layout phase owes."""
    norm = validate_device(device)
    entries = [(kind, None) for kind in DESIGN_WIDE_KINDS]
    per_technology = list(TECHNOLOGY_DEPENDENT_KINDS)
    if norm["kind"] in PROGRAMMABLE_DEVICE_KINDS:
        per_technology.extend(PROGRAMMABLE_ONLY_KINDS)
    for technology in norm["technologies"]:
        for kind in per_technology:
            entries.append((kind, technology))
    return entries


def validate_deposit(deposit, device):
    """Validate one deposited item against the device record."""
    norm_device = validate_device(device)
    if not isinstance(deposit, dict):
        raise ValueError("deposit must be a mapping")
    kind = deposit.get("kind")
    if kind not in VALID_KINDS:
        raise ValueError(
            "deposit has unknown kind %r (expected one of %s)"
            % (kind, ", ".join(VALID_KINDS))
        )
    technology = deposit.get("technology")
    needs_technology = kind in TECHNOLOGY_DEPENDENT_KINDS + PROGRAMMABLE_ONLY_KINDS
    if needs_technology:
        technology = _text("deposit %s technology" % kind, technology)
        if technology not in norm_device["technologies"]:
            raise ValueError(
                "deposit %s names technology %r which the device does not use"
                % (kind, technology)
            )
    elif technology is not None:
        raise ValueError(
            "deposit %s is design-wide and must not name a technology" % kind
        )
    run = _sequence_number("deposit %s layout_run" % kind, deposit.get("layout_run", 0))
    configuration_id = deposit.get("configuration_id")
    if configuration_id is not None:
        configuration_id = _text("deposit %s configuration_id" % kind, configuration_id)
    digest = deposit.get("digest")
    if digest is not None:
        digest = _text("deposit %s digest" % kind, digest)
    return {
        "kind": kind,
        "technology": technology,
        "layout_run": run,
        "configuration_id": configuration_id,
        "digest": digest,
    }


def check_deposit(deposit, device):
    """Findings about one deposit taken on its own."""
    norm_device = validate_device(device)
    norm = validate_deposit(deposit, norm_device)
    findings = []
    if norm["layout_run"] < norm_device["closing_layout_run"]:
        findings.append(FINDING_SUPERSEDED_RUN)
    elif norm["layout_run"] > norm_device["closing_layout_run"]:
        findings.append(FINDING_OUT_OF_PHASE_RUN)
    if norm["configuration_id"] is None:
        findings.append(FINDING_NO_CONFIGURATION_ID)
    if norm["digest"] is None:
        findings.append(FINDING_NO_DIGEST)
    return findings


def completeness_fraction(satisfied, owed):
    """Fraction of owed entries satisfied by a clean deposit."""
    owed_count = _sequence_number("owed", owed)
    satisfied_count = _sequence_number("satisfied", satisfied)
    if owed_count == 0:
        raise ValueError("owed must be > 0 to form a completeness fraction")
    if satisfied_count > owed_count:
        raise ValueError(
            "satisfied %d cannot exceed owed %d" % (satisfied_count, owed_count)
        )
    return satisfied_count / owed_count


def assess_database_update_after_layout(device, deposits):
    """Assess the post-layout repository update against clause 5.6.5."""
    norm_device = validate_device(device)
    if not isinstance(deposits, list):
        raise ValueError("deposits must be a list")
    owed = owed_entries(norm_device)
    by_entry = {}
    findings = []
    unexpected = []
    for deposit in deposits:
        norm = validate_deposit(deposit, norm_device)
        entry = (norm["kind"], norm["technology"])
        if entry not in owed:
            unexpected.append(entry)
            findings.append((entry, FINDING_UNEXPECTED_DEPOSIT))
            continue
        if entry in by_entry:
            findings.append((entry, FINDING_DUPLICATE_DEPOSIT))
            continue
        by_entry[entry] = norm
    gaps = []
    clean = 0
    for entry in owed:
        deposit = by_entry.get(entry)
        if deposit is None:
            gaps.append(entry)
            findings.append((entry, FINDING_MISSING_DEPOSIT))
            continue
        entry_findings = check_deposit(deposit, norm_device)
        if entry_findings:
            for name in entry_findings:
                findings.append((entry, name))
        else:
            clean += 1
    return {
        "device_id": norm_device["id"],
        "owed": owed,
        "owed_count": len(owed),
        "satisfied_count": clean,
        "completeness": completeness_fraction(clean, len(owed)),
        "gaps": gaps,
        "unexpected": unexpected,
        "findings": findings,
        "may_proceed": not findings,
    }
