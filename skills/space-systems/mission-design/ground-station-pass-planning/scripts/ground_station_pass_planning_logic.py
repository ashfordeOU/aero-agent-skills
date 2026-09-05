"""Ground station pass planning logic (space-systems/mission-design).

Pure stdlib daily ground station contact schedule for a low-Earth
satellite on a circular two-body orbit: propagate the sub-satellite
point over the planning horizon, compute the elevation of the satellite
above each ground station, detect the contiguous passes above the
station elevation mask, aggregate the daily contact schedule with its
downlink gaps, and merge the contacts of several ground stations into
one multi-station contact plan.

Spherical Earth, no J2, no drag. The sub-satellite propagation is a
simple circular two-body ground track rotated by the Earth rotation at
OMEGA_E; the orbit elements are taken as inputs (see kepler-orbit-
propagation and orbital-perturbations for physical propagation).

Module constants (fixed-step planner defaults):
RE_KM = 6371.0 (km), MU = 398600.4418 (km^3/s^2), OMEGA_E =
7.2921159e-5 (rad/s), STEP_S = 30.0 (s), GAP_THRESHOLD_S = 600.0 (s).
"""

import math

RE_KM = 6371.0
MU = 398600.4418
OMEGA_E = 7.2921159e-5
STEP_S = 30.0
GAP_THRESHOLD_S = 600.0

_DEG = 180.0 / math.pi


def orbital_period_s(altitude_km):
    """Orbital period of a circular orbit at altitude_km above the
    spherical Earth: T = 2 pi sqrt(a^3 / mu) with a = RE_KM +
    altitude_km. Rejects negative altitudes with ValueError."""
    if altitude_km < 0.0:
        raise ValueError("altitude_km must be >= 0")
    a_km = RE_KM + altitude_km
    return 2.0 * math.pi * math.sqrt(a_km ** 3 / MU)


def _mean_motion(altitude_km):
    """Mean motion of the circular orbit, sqrt(mu / a^3) in rad/s."""
    a_km = RE_KM + altitude_km
    return math.sqrt(MU / a_km ** 3)


def subsatellite_point(altitude_km, inclination_deg, raan_deg,
                       argument_of_latitude_0_deg, greenwich_0_deg, t_s):
    """Sub-satellite point at time t_s as {"lat_deg", "lon_deg"}.

    Circular-orbit inertial position at argument of latitude u(t) = u0
    + n t rotated from the RAAN/inclination frame, then rotated by the
    Earth rotation greenwich_0 + OMEGA_E t. No J2. Longitude is
    wrapped to [-180, 180]. Rejects negative altitude, inclinations
    outside [0, 180] and negative times with ValueError.
    """
    if altitude_km < 0.0:
        raise ValueError("altitude_km must be >= 0")
    if not 0.0 <= inclination_deg <= 180.0:
        raise ValueError("inclination_deg must be within [0, 180]")
    if t_s < 0.0:
        raise ValueError("t_s must be >= 0")
    inc = math.radians(inclination_deg)
    raan = math.radians(raan_deg)
    u0 = math.radians(argument_of_latitude_0_deg)
    r_km = RE_KM + altitude_km
    u = u0 + _mean_motion(altitude_km) * t_s
    cos_u = math.cos(u)
    sin_u = math.sin(u)
    x = r_km * (math.cos(raan) * cos_u
                - math.sin(raan) * sin_u * math.cos(inc))
    y = r_km * (math.sin(raan) * cos_u
                + math.cos(raan) * sin_u * math.cos(inc))
    z = r_km * (sin_u * math.sin(inc))
    lat_deg = math.degrees(math.asin(z / r_km))
    greenwich_deg = greenwich_0_deg + math.degrees(OMEGA_E * t_s)
    lon_deg = math.degrees(math.atan2(y, x)) - greenwich_deg
    lon_deg = ((lon_deg + 180.0) % 360.0) - 180.0
    return {"lat_deg": lat_deg, "lon_deg": lon_deg}


def elevation_angle(station_lat_deg, station_lon_deg, lat_deg, lon_deg,
                    altitude_km):
    """Elevation of the satellite above the station in degrees.

    Central angle lam between the station and the sub-satellite point,
    then elevation = atan2(cos(lam) - RE_KM / r, sin(lam)) with r =
    RE_KM + altitude_km; 90 degrees at the station zenith, 0 at the
    horizon central angle. Rejects negative altitude with ValueError.
    """
    if altitude_km < 0.0:
        raise ValueError("altitude_km must be >= 0")
    r_km = RE_KM + altitude_km
    phi_s = math.radians(station_lat_deg)
    lam_s = math.radians(station_lon_deg)
    phi = math.radians(lat_deg)
    lam = math.radians(lon_deg)
    cos_lam = (math.sin(phi_s) * math.sin(phi)
               + math.cos(phi_s) * math.cos(phi)
               * math.cos(lam - lam_s))
    cos_lam = max(-1.0, min(1.0, cos_lam))
    sin_lam = math.sqrt(max(0.0, 1.0 - cos_lam * cos_lam))
    return math.degrees(math.atan2(cos_lam - RE_KM / r_km, sin_lam))


def detect_passes(altitude_km, inclination_deg, raan_deg,
                  argument_of_latitude_0_deg, greenwich_0_deg,
                  station_lat_deg, station_lon_deg, min_elevation_deg,
                  horizon_h):
    """Detect the contiguous passes above the station elevation mask.

    Step t from 0 to horizon_h * 3600 in STEP_S increments, accumulate
    contiguous samples with elevation >= min_elevation_deg into passes,
    and return a list of {"start_s", "end_s", "duration_s",
    "max_elevation_deg"} dicts. duration = end - start + STEP_S for the
    inclusive sample run. Rejects negative masks and non-positive
    horizons with ValueError.
    """
    if min_elevation_deg < 0.0:
        raise ValueError("min_elevation_deg must be >= 0")
    if horizon_h <= 0.0:
        raise ValueError("horizon_h must be > 0")
    horizon_s = horizon_h * 3600.0
    n_steps = int(round(horizon_s / STEP_S))
    passes = []
    current = None
    for k in range(n_steps + 1):
        t_s = k * STEP_S
        point = subsatellite_point(altitude_km, inclination_deg, raan_deg,
                                   argument_of_latitude_0_deg,
                                   greenwich_0_deg, t_s)
        elev_deg = elevation_angle(station_lat_deg, station_lon_deg,
                                   point["lat_deg"], point["lon_deg"],
                                   altitude_km)
        if elev_deg >= min_elevation_deg:
            if current is None:
                current = {"start_s": t_s, "end_s": t_s,
                           "max_elevation_deg": elev_deg}
            else:
                current["end_s"] = t_s
                if elev_deg > current["max_elevation_deg"]:
                    current["max_elevation_deg"] = elev_deg
        elif current is not None:
            current["duration_s"] = (current["end_s"] - current["start_s"]
                                     + STEP_S)
            passes.append(current)
            current = None
    if current is not None:
        current["duration_s"] = (current["end_s"] - current["start_s"]
                                 + STEP_S)
        passes.append(current)
    return passes


def daily_contact_schedule(passes, gap_threshold_s=GAP_THRESHOLD_S):
    """Aggregate the daily contact schedule of one ground station.

    Returns {"n_passes", "total_contact_s", "contacts", "gaps"} with
    contacts the pass dicts and gaps the inter-pass downlink gaps of at
    least gap_threshold_s as {"start_s", "end_s", "duration_s"}, where
    a gap runs from the previous pass end plus STEP_S to the next pass
    start.
    """
    total_contact_s = sum(p["duration_s"] for p in passes)
    gaps = []
    for i in range(len(passes) - 1):
        duration_s = passes[i + 1]["start_s"] - passes[i]["end_s"] - STEP_S
        if duration_s >= gap_threshold_s:
            gaps.append({"start_s": passes[i]["end_s"] + STEP_S,
                         "end_s": passes[i + 1]["start_s"],
                         "duration_s": duration_s})
    return {"n_passes": len(passes), "total_contact_s": total_contact_s,
            "contacts": [dict(p) for p in passes], "gaps": gaps}


def max_downlink_gap(passes, horizon_h):
    """Longest interval with no contact over the horizon.

    Includes the horizon boundaries: before the first pass, between the
    passes (next start minus previous end minus STEP_S) and after the
    last pass (horizon minus last end minus STEP_S). A satellite with
    no passes returns the whole horizon in seconds.
    """
    horizon_s = horizon_h * 3600.0
    if not passes:
        return horizon_s
    gap_durations = [passes[0]["start_s"]]
    for i in range(len(passes) - 1):
        gap_durations.append(passes[i + 1]["start_s"]
                             - passes[i]["end_s"] - STEP_S)
    gap_durations.append(horizon_s - passes[-1]["end_s"] - STEP_S)
    return max(gap_durations)


def _merge_contacts(all_contacts):
    """Sort contacts by start and merge contacts whose start is within
    STEP_S of the previous contact end into one contiguous contact."""
    ordered = sorted(all_contacts, key=lambda c: c["start_s"])
    merged = []
    for contact in ordered:
        if merged and contact["start_s"] <= merged[-1]["end_s"] + STEP_S:
            last = merged[-1]
            if contact["end_s"] > last["end_s"]:
                last["end_s"] = contact["end_s"]
            if contact["max_elevation_deg"] > last["max_elevation_deg"]:
                last["max_elevation_deg"] = contact["max_elevation_deg"]
            last["duration_s"] = last["end_s"] - last["start_s"] + STEP_S
        else:
            merged.append(dict(contact))
    return merged


def ground_station_contact_plan(stations, altitude_km, inclination_deg,
                                raan_deg, argument_of_latitude_0_deg,
                                greenwich_0_deg, horizon_h):
    """Merge the contacts of several ground stations into one plan.

    stations is a list of {"lat_deg", "lon_deg", "min_elevation_deg"}
    dicts. Runs detect_passes for every station, sorts all contacts by
    start, and merges contacts whose start is within STEP_S of the
    previous contact end. Returns {"contacts", "total_contact_s",
    "max_gap_s"}: each merged contact carries station_idx (the station
    whose pass opened the merged interval), start_s, end_s,
    duration_s and the highest max_elevation_deg of the merged passes.
    """
    all_contacts = []
    for station_idx, station in enumerate(stations):
        passes = detect_passes(altitude_km, inclination_deg, raan_deg,
                               argument_of_latitude_0_deg,
                               greenwich_0_deg, station["lat_deg"],
                               station["lon_deg"],
                               station["min_elevation_deg"], horizon_h)
        for p in passes:
            all_contacts.append({"start_s": p["start_s"],
                                 "end_s": p["end_s"],
                                 "duration_s": p["duration_s"],
                                 "max_elevation_deg": p["max_elevation_deg"],
                                 "station_idx": station_idx})
    merged = _merge_contacts(all_contacts)
    total_contact_s = sum(c["duration_s"] for c in merged)
    return {"contacts": merged, "total_contact_s": total_contact_s,
            "max_gap_s": max_downlink_gap(merged, horizon_h)}
