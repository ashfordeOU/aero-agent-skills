"""Which items need an offgassing determination, and by which route.

Anchor: ECSS-Q-ST-70-29 scope -- offgassing screening of materials and
assembled articles that share their atmosphere with a crew. The purpose is not
the outgassing behaviour of a material in vacuum but what it releases into
breathable air at cabin temperature, and the scope therefore follows the
atmosphere the item is exposed to rather than the item's function.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the item shares the crew atmosphere at all. An item outside
   the pressurised volume releases into vacuum and belongs to a different
   standard; an item inside it is in scope whatever its function.
2. Allow for containment, but only real containment: a sealed enclosure with
   no vent path removes the exposure, while a ventilated or merely closed box
   does not.
3. Compute the loading the item puts into the cabin -- exposed mass over the
   free volume the crew breathes -- because a determination is about a
   concentration and the concentration depends on both.
4. Decide the route. A bulk material characterised for the database is tested
   at material level; an article that carries several materials, or a process
   applied during its build, is tested as the assembled article it will fly
   as, because the process is part of what offgasses.
5. Decide whether an existing report still covers the item, or whether a
   change of material, process or supplier has invalidated it.
6. Return the disposition with the requirement areas the item takes on.
"""

import math

__all__ = [
    "CREWED_LOCATIONS",
    "EXTERNAL_LOCATIONS",
    "SEALED_CONTAINMENTS",
    "VENTED_CONTAINMENTS",
    "MIN_LOADING_G_PER_M3",
    "ASSEMBLED_ARTICLE_MATERIAL_COUNT",
    "BUILD_PROCESSES",
    "MAX_REPORT_AGE_YEARS",
    "INVALIDATING_CHANGES",
    "REQUIREMENT_AREAS",
    "TOLERANCE",
    "exposure_disposition",
    "cabin_loading_g_per_m3",
    "loading_is_negligible",
    "test_route",
    "report_reuse_findings",
    "requirement_areas",
    "assess_offgassing_applicability",
]

# Locations that share the atmosphere the crew breathes.
CREWED_LOCATIONS = (
    "crew-compartment",
    "habitable-volume",
    "pressurised-module",
    "internal-stowage",
    "airlock-internal",
)

# Locations that do not. What these release goes to vacuum, and the vacuum
# outgassing standard governs it instead.
EXTERNAL_LOCATIONS = (
    "external-surface",
    "unpressurised-bay",
    "propulsion-module",
    "launch-fairing",
)

# Containment that actually removes the exposure, and containment that only
# looks like it does.
SEALED_CONTAINMENTS = ("hermetically-sealed", "welded-enclosure", "glass-to-metal-sealed")
VENTED_CONTAINMENTS = ("vented-enclosure", "closed-box", "gasketed-cover", "none")

# Below this loading an item may lean on an existing material database entry
# instead of carrying its own determination.
MIN_LOADING_G_PER_M3 = 1.0

# An article carrying at least this many materials is tested as an article.
ASSEMBLED_ARTICLE_MATERIAL_COUNT = 3

# Processes applied during the build that offgas in their own right, so the
# article rather than its materials is what has to be tested.
BUILD_PROCESSES = (
    "adhesive-bonding",
    "conformal-coating",
    "potting",
    "painting",
    "lubrication",
    "cleaning-agent-residue",
)

# An offgassing report ages out, and certain changes end it early.
MAX_REPORT_AGE_YEARS = 5.0
INVALIDATING_CHANGES = (
    "material-substitution",
    "process-change",
    "supplier-change",
    "cure-schedule-change",
    "surface-treatment-change",
)

# What an item inside scope takes on, in the order the determination runs.
REQUIREMENT_AREAS = (
    "specimen-preparation",
    "test-conditions",
    "product-identification",
    "concentration-determination",
    "toxicity-assessment",
    "odour-assessment",
    "acceptance-criteria",
    "test-report",
)

# Masses and volumes are measured quantities; a loading sitting exactly on the
# threshold is not negligible, and this absorbs representation error only.
TOLERANCE = 1e-9


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _positive(value, label):
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _sequence(value, label):
    if isinstance(value, (str, dict)) or not isinstance(value, (list, tuple, set)):
        raise ValueError("%s must be a sequence of tokens" % label)
    return tuple(_token(v, "%s entry" % label) for v in value)


def exposure_disposition(location, containment="none"):
    """Say whether an item shares the crew atmosphere, and why."""
    where = _token(location, "location")
    seal = _token(containment, "containment")
    if seal not in SEALED_CONTAINMENTS and seal not in VENTED_CONTAINMENTS:
        raise ValueError(
            "unknown containment '%s'; known: %s"
            % (seal, ", ".join(sorted(SEALED_CONTAINMENTS + VENTED_CONTAINMENTS)))
        )
    if where in EXTERNAL_LOCATIONS:
        return {
            "exposed": False,
            "reason": "location '%s' is outside the pressurised volume; what it "
            "releases goes to vacuum, not into breathable air" % where,
        }
    if where not in CREWED_LOCATIONS:
        raise ValueError(
            "unknown location '%s'; known: %s"
            % (where, ", ".join(sorted(CREWED_LOCATIONS + EXTERNAL_LOCATIONS)))
        )
    if seal in SEALED_CONTAINMENTS:
        return {
            "exposed": False,
            "reason": "'%s' containment leaves no vent path into the cabin "
            "atmosphere" % seal,
        }
    return {
        "exposed": True,
        "reason": "location '%s' with '%s' containment shares the crew atmosphere"
        % (where, seal),
    }


def cabin_loading_g_per_m3(exposed_mass_g, free_volume_m3):
    """Return the mass the item puts into each cubic metre of cabin volume."""
    mass = _positive(exposed_mass_g, "exposed_mass_g")
    volume = _positive(free_volume_m3, "free_volume_m3")
    return mass / volume


def loading_is_negligible(loading_g_per_m3):
    """Say whether a loading is small enough to lean on database data."""
    loading = _real(loading_g_per_m3, "loading_g_per_m3")
    if loading < 0.0:
        raise ValueError("loading_g_per_m3 must be non-negative, got %g" % loading)
    return loading < MIN_LOADING_G_PER_M3 - TOLERANCE


def test_route(item):
    """Return the route by which an item is tested, and the reasons for it.

    item keys: optionally materials (a sequence of designations) and
    processes (a sequence of build-process tokens).
    """
    _require_mapping(item, "item")
    materials = _sequence(item.get("materials", ()), "materials")
    processes = _sequence(item.get("processes", ()), "processes")
    unknown = sorted(set(processes) - set(BUILD_PROCESSES))
    if unknown:
        raise ValueError(
            "unknown build process(es) %s; known: %s"
            % (", ".join(unknown), ", ".join(sorted(BUILD_PROCESSES)))
        )
    reasons = []
    if len(materials) >= ASSEMBLED_ARTICLE_MATERIAL_COUNT:
        reasons.append(
            "the item carries %d materials, at or past the %d that make it an "
            "assembled article" % (len(materials), ASSEMBLED_ARTICLE_MATERIAL_COUNT)
        )
    if processes:
        reasons.append(
            "build process(es) %s offgas in their own right and only exist on the "
            "assembled article" % ", ".join(sorted(set(processes)))
        )
    if reasons:
        return {"route": "assembled-article", "reasons": reasons}
    return {
        "route": "material-level",
        "reasons": [
            "a single material with no build process applied is characterised at "
            "material level"
        ],
    }


def report_reuse_findings(prior_report):
    """Say why an existing offgassing report does or does not still cover the item."""
    if prior_report is None:
        return ["no prior offgassing report; a determination is required"]
    _require_mapping(prior_report, "prior_report")
    if "age_years" not in prior_report:
        raise ValueError("prior_report missing required key 'age_years'")
    age = _real(prior_report["age_years"], "age_years")
    if age < 0.0:
        raise ValueError("age_years must be non-negative, got %g" % age)
    changes = _sequence(prior_report.get("changes_since", ()), "changes_since")
    unknown = sorted(set(changes) - set(INVALIDATING_CHANGES))
    if unknown:
        raise ValueError(
            "unknown change(s) %s; known: %s"
            % (", ".join(unknown), ", ".join(sorted(INVALIDATING_CHANGES)))
        )
    findings = []
    if age > MAX_REPORT_AGE_YEARS + TOLERANCE:
        findings.append(
            "the prior report is %g years old, past the %g year validity"
            % (age, MAX_REPORT_AGE_YEARS)
        )
    for change in sorted(set(changes)):
        findings.append(
            "'%s' since the prior report ends its coverage; the article tested is "
            "not the article flying" % change
        )
    return findings


def requirement_areas():
    """Return the requirement areas an in-scope item takes on."""
    return REQUIREMENT_AREAS


def assess_offgassing_applicability(item):
    """Decide whether an item needs an offgassing determination and by what route.

    item keys: location, exposed_mass_g, free_volume_m3, and optionally
    containment, materials, processes, database_entry and prior_report.
    """
    _require_mapping(item, "item")
    for key in ("location", "exposed_mass_g", "free_volume_m3"):
        if key not in item:
            raise ValueError("item missing required key '%s'" % key)

    exposure = exposure_disposition(item["location"], item.get("containment", "none"))
    loading = cabin_loading_g_per_m3(item["exposed_mass_g"], item["free_volume_m3"])
    negligible = loading_is_negligible(loading)
    has_database_entry = bool(item.get("database_entry"))
    route = test_route(item)

    notes = []
    if not exposure["exposed"]:
        disposition = "outside-scope"
        notes.append(exposure["reason"])
        return {
            "disposition": disposition,
            "exposed": False,
            "loading_g_per_m3": loading,
            "loading_negligible": negligible,
            "route": None,
            "route_reasons": [],
            "requirement_areas": (),
            "reuse_findings": [],
            "notes": notes,
            "determination_required": False,
        }

    notes.append(exposure["reason"])
    reuse = report_reuse_findings(item.get("prior_report"))

    if negligible and has_database_entry:
        notes.append(
            "a loading of %.4f g/m3 is below the %g g/m3 threshold and the material "
            "carries a database entry, so the entry may stand in for a dedicated "
            "determination" % (loading, MIN_LOADING_G_PER_M3)
        )
        return {
            "disposition": "covered-by-database",
            "exposed": True,
            "loading_g_per_m3": loading,
            "loading_negligible": True,
            "route": route["route"],
            "route_reasons": route["reasons"],
            "requirement_areas": (),
            "reuse_findings": reuse,
            "notes": notes,
            "determination_required": False,
        }

    if negligible and not has_database_entry:
        notes.append(
            "the loading is below the %g g/m3 threshold but no database entry "
            "supports the material, so the threshold cannot be relied on"
            % MIN_LOADING_G_PER_M3
        )

    if not reuse:
        notes.append("the prior offgassing report still covers the item as flown")
        return {
            "disposition": "covered-by-prior-report",
            "exposed": True,
            "loading_g_per_m3": loading,
            "loading_negligible": negligible,
            "route": route["route"],
            "route_reasons": route["reasons"],
            "requirement_areas": (),
            "reuse_findings": [],
            "notes": notes,
            "determination_required": False,
        }

    notes.extend(route["reasons"])
    return {
        "disposition": "within-scope",
        "exposed": True,
        "loading_g_per_m3": loading,
        "loading_negligible": negligible,
        "route": route["route"],
        "route_reasons": route["reasons"],
        "requirement_areas": requirement_areas(),
        "reuse_findings": reuse,
        "notes": notes,
        "determination_required": True,
    }
