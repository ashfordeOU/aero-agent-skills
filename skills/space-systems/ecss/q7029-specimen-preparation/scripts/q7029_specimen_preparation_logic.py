"""Preparing the test item for a crew-compartment offgassing determination.

Anchor: ECSS-Q-ST-70-29, test-item clause -- what goes into the chamber for an
offgassing determination, whether that is a quantity of a bulk material or a
whole assembled article, and in what condition it goes in. The governing idea
is representativeness: the chamber has to see at least the loading the cabin
will see, from an item in the state it will fly in. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Size the test item from the loading it has to represent: the cabin loading
   the item produces, times the chamber volume, times any conservatism the
   test request asks for.
2. Compare the loading the chamber will actually see against the cabin
   loading, because a chamber loaded below the cabin under-reports every
   concentration in direct proportion.
3. Keep the item small enough relative to the chamber that the atmosphere
   being sampled is still an atmosphere and not a packed volume.
4. Refuse any preparation that removes volatiles. A solvent wipe, a bake-out
   or a vacuum conditioning strips exactly the products the determination
   exists to find, and the result is a clean report about a different article.
5. Require the cure to be complete and the item to be tested inside a window
   after cure, so the article in the chamber matches the article at launch.
6. Count the test items: replicates for a bulk material, the single as-flown
   article for an assembled one.
7. Return the plan with every finding, and mark it ready only when clean.
"""

import math

__all__ = [
    "TEST_ROUTES",
    "MIN_SPECIMEN_MASS_G",
    "MAX_CHAMBER_FILL_FRACTION",
    "MATERIAL_LEVEL_REPLICATES",
    "ASSEMBLED_ARTICLE_REPLICATES",
    "MIN_CONSERVATISM_FACTOR",
    "BANNED_PREPARATIONS",
    "PERMITTED_PREPARATIONS",
    "MAX_DAYS_SINCE_CURE",
    "TOLERANCE",
    "required_specimen_mass_g",
    "chamber_loading_g_per_m3",
    "loading_findings",
    "chamber_fill_fraction",
    "fill_findings",
    "preparation_findings",
    "cure_findings",
    "replicate_count",
    "plan_offgassing_test_item",
]

# The two routes the test item can take, matching the scope decision.
TEST_ROUTES = ("material-level", "assembled-article")

# Below this the evolved quantity sits among the analytical blank.
MIN_SPECIMEN_MASS_G = 10.0

# Past this the chamber is packed rather than loaded, and the atmosphere being
# sampled is no longer well mixed.
MAX_CHAMBER_FILL_FRACTION = 0.5

# A bulk material is characterised across replicates; an assembled article is
# tested once, as the article that will fly.
MATERIAL_LEVEL_REPLICATES = 2
ASSEMBLED_ARTICLE_REPLICATES = 1

# A test may be run more heavily loaded than the cabin, never less.
MIN_CONSERVATISM_FACTOR = 1.0

# Preparations that remove the very products the determination looks for.
BANNED_PREPARATIONS = (
    "solvent-wipe",
    "bake-out",
    "vacuum-conditioning",
    "ultrasonic-clean",
    "abrasion",
    "thermal-precondition",
    "nitrogen-purge",
)

# Preparations that bring the item to its as-flown state without stripping it.
PERMITTED_PREPARATIONS = (
    "packaging-removed",
    "protective-film-removed",
    "gloved-handling",
    "as-flown-configuration",
    "ambient-storage",
)

# Past this age the item has already released what it would have released in
# the cabin, and the test understates the launch condition.
MAX_DAYS_SINCE_CURE = 90.0

# Masses, volumes and durations are measured quantities; a value sitting on a
# bound meets it, and this absorbs representation error only.
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


def _non_negative(value, label):
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _route(value):
    name = _token(value, "route")
    if name not in TEST_ROUTES:
        raise ValueError(
            "unknown test route '%s'; known: %s" % (name, ", ".join(TEST_ROUTES))
        )
    return name


def required_specimen_mass_g(
    cabin_loading_g_per_m3, chamber_volume_m3, conservatism=MIN_CONSERVATISM_FACTOR
):
    """Return the mass the chamber needs to reproduce the cabin loading."""
    loading = _positive(cabin_loading_g_per_m3, "cabin_loading_g_per_m3")
    volume = _positive(chamber_volume_m3, "chamber_volume_m3")
    factor = _real(conservatism, "conservatism")
    if factor < MIN_CONSERVATISM_FACTOR - TOLERANCE:
        raise ValueError(
            "conservatism of %g would load the chamber below the cabin; %g is the "
            "minimum" % (factor, MIN_CONSERVATISM_FACTOR)
        )
    return loading * volume * factor


def chamber_loading_g_per_m3(mass_g, chamber_volume_m3):
    """Return the loading the chamber actually sees."""
    mass = _positive(mass_g, "mass_g")
    volume = _positive(chamber_volume_m3, "chamber_volume_m3")
    return mass / volume


def loading_findings(achieved_g_per_m3, cabin_g_per_m3):
    """Report a chamber loaded below the cabin it is standing in for."""
    achieved = _non_negative(achieved_g_per_m3, "achieved_g_per_m3")
    cabin = _positive(cabin_g_per_m3, "cabin_g_per_m3")
    if achieved < cabin - TOLERANCE:
        return [
            "the chamber is loaded at %.4f g/m3 against a cabin loading of %.4f "
            "g/m3; every concentration is understated by that ratio"
            % (achieved, cabin)
        ]
    return []


def chamber_fill_fraction(item_volume_m3, chamber_volume_m3):
    """Return the fraction of the chamber the test item occupies."""
    item = _positive(item_volume_m3, "item_volume_m3")
    chamber = _positive(chamber_volume_m3, "chamber_volume_m3")
    return item / chamber


def fill_findings(item_volume_m3, chamber_volume_m3):
    """Report a test item that packs the chamber rather than loading it."""
    fraction = chamber_fill_fraction(item_volume_m3, chamber_volume_m3)
    if fraction > MAX_CHAMBER_FILL_FRACTION + TOLERANCE:
        return [
            "the item fills %.3f of the chamber, past the %.3f at which the "
            "atmosphere is no longer well mixed"
            % (fraction, MAX_CHAMBER_FILL_FRACTION)
        ]
    return []


def preparation_findings(preparations):
    """Report preparations that strip the item of what the test looks for."""
    if isinstance(preparations, (str, dict)) or not isinstance(
        preparations, (list, tuple, set)
    ):
        raise ValueError("preparations must be a sequence of tokens")
    findings = []
    for raw in preparations:
        action = _token(raw, "preparation")
        if action in BANNED_PREPARATIONS:
            findings.append(
                "'%s' removes volatiles before the test and invalidates the result; "
                "the item goes in as it flies" % action
            )
        elif action not in PERMITTED_PREPARATIONS:
            raise ValueError(
                "unknown preparation '%s'; permitted: %s"
                % (action, ", ".join(PERMITTED_PREPARATIONS))
            )
    return findings


def cure_findings(cure):
    """Grade the cure state and the age of the item against the launch condition.

    cure keys: required_hours, achieved_hours, days_since_cure.
    """
    _require_mapping(cure, "cure")
    for key in ("required_hours", "achieved_hours", "days_since_cure"):
        if key not in cure:
            raise ValueError("cure state missing required key '%s'" % key)
    required = _positive(cure["required_hours"], "required_hours")
    achieved = _non_negative(cure["achieved_hours"], "achieved_hours")
    age = _non_negative(cure["days_since_cure"], "days_since_cure")
    findings = []
    if achieved < required - TOLERANCE:
        findings.append(
            "the cure ran %g h against the %g h specified; an incompletely cured "
            "item offgasses its unreacted fraction and is not the flight article"
            % (achieved, required)
        )
    if age > MAX_DAYS_SINCE_CURE + TOLERANCE:
        findings.append(
            "the item is %g days past cure, beyond the %g day window; it has "
            "already released what the cabin would have seen"
            % (age, MAX_DAYS_SINCE_CURE)
        )
    return findings


def replicate_count(route):
    """Return how many test items the route calls for."""
    if _route(route) == "material-level":
        return MATERIAL_LEVEL_REPLICATES
    return ASSEMBLED_ARTICLE_REPLICATES


def plan_offgassing_test_item(request):
    """Build the test-item plan for one offgassing determination.

    request keys: route, cabin_loading_g_per_m3, chamber_volume_m3, and
    optionally conservatism, available_mass_g, item_volume_m3, preparations
    and cure.
    """
    _require_mapping(request, "request")
    for key in ("route", "cabin_loading_g_per_m3", "chamber_volume_m3"):
        if key not in request:
            raise ValueError("request missing required key '%s'" % key)

    route = _route(request["route"])
    cabin = _positive(request["cabin_loading_g_per_m3"], "cabin_loading_g_per_m3")
    chamber = _positive(request["chamber_volume_m3"], "chamber_volume_m3")
    conservatism = request.get("conservatism", MIN_CONSERVATISM_FACTOR)
    required_mass = required_specimen_mass_g(cabin, chamber, conservatism)

    planned_mass = request.get("available_mass_g")
    if planned_mass is None:
        planned_mass = required_mass
    planned_mass = _positive(planned_mass, "available_mass_g")

    findings = []
    achieved_loading = chamber_loading_g_per_m3(planned_mass, chamber)
    findings.extend(loading_findings(achieved_loading, cabin))

    if planned_mass < MIN_SPECIMEN_MASS_G - TOLERANCE:
        findings.append(
            "a test item of %g g is below the %g g the analysis needs to lift the "
            "evolved quantity clear of the blank; use a smaller chamber"
            % (planned_mass, MIN_SPECIMEN_MASS_G)
        )

    item_volume = request.get("item_volume_m3")
    fill = None
    if item_volume is not None:
        fill = chamber_fill_fraction(item_volume, chamber)
        findings.extend(fill_findings(item_volume, chamber))

    findings.extend(preparation_findings(request.get("preparations", ())))

    cure = request.get("cure")
    if cure is not None:
        findings.extend(cure_findings(cure))

    replicates = replicate_count(route)
    return {
        "route": route,
        "cabin_loading_g_per_m3": cabin,
        "chamber_volume_m3": chamber,
        "conservatism": _real(conservatism, "conservatism"),
        "required_mass_g": required_mass,
        "planned_mass_g": planned_mass,
        "achieved_loading_g_per_m3": achieved_loading,
        "loading_ratio": achieved_loading / cabin,
        "chamber_fill_fraction": fill,
        "test_items": replicates,
        "total_material_g": planned_mass * replicates,
        "findings": findings,
        "ready": not findings,
    }
