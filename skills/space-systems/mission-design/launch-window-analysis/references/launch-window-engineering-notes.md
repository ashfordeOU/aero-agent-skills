# Launch window engineering notes

Derivations behind scripts/launch_window_logic.py. Offline companion
document; the code is the source of truth.

## 1. Launch azimuth for direct injection

The launch velocity vector lies in the plane spanned by the site radius
vector and the launch azimuth direction. The orbit plane normal makes
the inclination angle with the equatorial plane. Equating the two
constraints gives the standard relation:

    cos(inc) = cos(lat) * sin(az)

so az = asin(cos(inc) / cos(lat)). At az = 90 deg (due east) the
relation reduces to inc = lat. Because |sin(az)| <= 1, a real solution
requires |cos(inc) / cos(lat)| <= 1, which holds for
|lat| <= inc <= 180 - |lat|. Outside that range direct injection is
impossible and the function raises ValueError. For retrograde orbits
(inc > 90) the asin branch gives a negative angle and the physical
azimuth is 180 - asin(...), in [90, 180] (westward launch).

Reference numbers (KSC, 28.5 N): inc 28.5 -> az 90.0; inc 51.6 ->
az 44.975; inc 98 -> az 189.112; inc 90 -> az 0 (due north).

## 2. Daily window: the site crossing the orbit plane

The site's right ascension is its local sidereal time,
LST = GMST + site_lon. The orbit plane has normal

    n_hat = [sin(i) sin(raan), -sin(i) cos(raan), cos(i)]

and the site position unit vector is

    r_hat = [cos(lat) cos(LST), cos(lat) sin(LST), sin(lat)]

The site is in the plane when r_hat . n_hat = 0:

    cos(lat) sin(i) sin(raan - LST) + sin(lat) cos(i) = 0

which solves to sin(raan - LST) = -tan(lat) / tan(i). With
t = tan(lat) / tan(i), the two daily crossings are at

    LST = raan + asin(t)        (ascending side)
    LST = raan + 180 - asin(t)  (descending side)

mod 360. |t| > 1 means the site never crosses the plane (same
feasibility limit as the azimuth formula); the window functions raise
ValueError in that case. The window center is the crossing instant:

    center = (LST_cross - site_lon - gmst_ref) / rel_rate

with rel_rate = earth_rate - node_regression in deg per day.

## 3. Window half-width from the out-of-plane tolerance

Expand the crossing condition around the crossing. Write
raan - LST = delta_c + u with sin(delta_c) = -t, cos(delta_c) =
+sqrt(1 - t^2) on the ascending side. Then

    sin(theta) = cos(lat) sin(i) [sqrt(1 - t^2) u + t u^2 / 2]

where theta is the site's out-of-plane angle. Setting
sin(theta) = sin(tolerance) gives a quadratic in u whose positive root
is the half-width in radians of site right ascension:

    u = (-A + sqrt(A^2 + 4 B eps)) / (2 B)
    A = cos(lat) sin(i) sqrt(1 - t^2)
    B = cos(lat) sin(i) t / 2
    eps = tolerance in radians

with the special cases B = 0 -> u = eps / A and A = 0 (grazing,
|t| = 1) -> u = sqrt(eps / |B|). The half-width in time is
u_deg / rel_rate. Example: KSC (28.5 N) into 51.6 deg with a 5 deg
tolerance gives a half-width of 1864.5 s (about 31 min).

## 4. Sun-synchronous LTAN to RAAN

A sun-synchronous orbit precesses its RAAN at 0.9856 deg/day eastward,
tracking the sun's apparent motion. The ascending node crossing happens
at local solar time LTAN, so the node meridian sits (LTAN - 12) hours
west of the subsolar meridian. With the sun at right ascension sun_ra:

    raan = sun_ra + 15 * (LTAN - 12)   mod 360

LTAN 12:00 -> raan = sun_ra (node under the sun); LTAN 06:00 (dawn-dusk)
-> sun_ra - 90; LTAN 10:30 -> sun_ra - 22.5; LTAN 18:00 -> sun_ra + 90.

## 5. Plane change delta-v

Rotating a circular velocity vector v by an angle di costs

    dv = 2 v sin(di / 2)

At 7.8 km/s: 10 deg -> 1.360 km/s; 20 deg -> 2.709 km/s. Note that
2 v sin(10 deg) = 2.709 km/s, so a "10 deg plane change costs about
2.7 km/s" claim is really the 20 deg case under the half-angle formula;
a 10 deg change at LEO speeds is about 1.36 km/s.

## 6. Window period from regression versus Earth rotation

The crossing condition recurs when the site gains 360 deg on the node:

    period = 360 / (earth_rate - node_regression) days

earth_rate = 360.9856 deg/day (sidereal). Without regression the period
is 0.99727 days (one sidereal day). With the sun-synchronous regression
of 0.9856 deg/day the period is exactly 1.0 day: the window falls at the
same local solar time every day, the defining sun-synchronous property.

## 7. Elevation angle at the crossing

At the crossing instant the site lies on the ground track, so the pass
is a zenith pass and the satellite elevation is 90 deg at t = 0. The
sub-satellite point moves at the orbital angular rate v / r with
v = sqrt(mu_earth / r), r = R + h. The elevation follows the standard
pass geometry:

    e(t) = atan2(cos(mu) - R / r, sin(mu)),  mu = v t / r

The horizon (e = 0) is at mu = acos(R / r). For h = 400 km:
R / r = 0.94093, horizon at 304.85 s on each side, elevation 24.97 deg
at 100 s and 0.32 deg at 300 s.

## 8. Beta angle (lighting)

sin(beta) = n_hat . s_hat with s_hat the sun unit vector
[cos(dec) cos(ra), cos(dec) sin(ra), sin(dec)]. Dawn-dusk orbits
(LTAN 06:00) put the sun near the plane at equinox, |beta| about 90 deg;
noon-midnight orbits (LTAN 12:00) put the sun perpendicular to the
plane, beta about 0. LTAN 10:30 at equinox gives beta about -22.3 deg.
Beta drives solar array power and eclipse fraction constraints.

## 9. Standards framing

ECSS-E-ST-10C (Space engineering: System engineering general
requirements) frames mission analysis and the ECSS lifecycle in which
launch window analysis sits. ECSS standards are free to download from
https://ecss.nl/standards/ (name + paraphrase + link only, no
reproduction). The formulas in this skill are common space engineering
methodology and are summarized, not reproduced, per standards-map.yaml.
