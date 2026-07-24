#!/usr/bin/env python3
"""
Plot the Exhibit "A" metes-and-bounds parcel onto a map.

Deed (Exhibit "A"):
    Land situated in the Township of Bedford, County of Monroe, State of
    Michigan, described as: That part of the Northwest quarter of Section 15,
    Town 8 South, Range 7 East, Bedford Township, Monroe County, Michigan,
    described as follows: Commencing at a point 7.7 feet South 89 degrees 58
    minutes 30 seconds West from the North one quarter corner of said Section
    15; thence South 89 degrees 58 minutes 30 seconds West 157.98 feet; thence
    South 0 degrees 40 minutes West 249.95 feet; thence due East 160.88 feet;
    thence due North 250.00 feet to the Point of Beginning.

The parcel's shape, dimensions and area are exact -- they come straight out of
the deed.  Only its absolute position on the globe depends on the coordinate of
the North one-quarter corner of Section 15, which is supplied by --anchor.

Usage:
    python3 plot_parcel.py                       # use the built-in estimate
    python3 plot_parcel.py --anchor LAT,LON      # re-anchor on a known corner
    python3 plot_parcel.py --anchor 41.7931,-83.5776 --outdir out
"""

from __future__ import annotations

import argparse
import json
import math
import os

# --------------------------------------------------------------------------
# The deed
# --------------------------------------------------------------------------

# Tie line: from the North 1/4 corner of Section 15 to the Point of Beginning.
TIE = ("S", 89, 58, 30, "W", 7.7)

# The four boundary calls, run in order from the Point of Beginning.
# (ns, deg, min, sec, ew, distance_ft)
CALLS = [
    ("S", 89, 58, 30, "W", 157.98),
    ("S", 0, 40, 0, "W", 249.95),
    ("N", 90, 0, 0, "E", 160.88),   # "due East"
    ("N", 0, 0, 0, "E", 250.00),    # "due North"
]

CALL_LABELS = [
    'S 89°58\'30" W  157.98\'',
    'S 00°40\'00" W  249.95\'',
    'Due East  160.88\'',
    'Due North  250.00\'',
]

# Best estimate of the North 1/4 corner of Section 15, T8S R7E, Bedford
# Township, Monroe County, Michigan.  Derived from PLSS grid reconstruction --
# see README.md.  Accurate to roughly +/- 0.3 mi; replace with a surveyed or
# county-GIS coordinate for real-world use.
DEFAULT_ANCHOR = (41.79309, -83.57760)

FT_PER_M = 1.0 / 0.3048

# WGS84
WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


def azimuth(ns: str, deg: int, minutes: int, sec: int, ew: str) -> float:
    """Convert a quadrant bearing to an azimuth in degrees clockwise from north."""
    angle = deg + minutes / 60.0 + sec / 3600.0
    if ns == "N":
        return angle % 360.0 if ew == "E" else (360.0 - angle) % 360.0
    return (180.0 - angle) % 360.0 if ew == "E" else (180.0 + angle) % 360.0


def leg(call) -> tuple[float, float]:
    """Return (delta_north_ft, delta_east_ft) for one call."""
    ns, deg, minutes, sec, ew, dist = call
    az = math.radians(azimuth(ns, deg, minutes, sec, ew))
    return dist * math.cos(az), dist * math.sin(az)


def traverse() -> tuple[list[tuple[float, float]], tuple[float, float]]:
    """Run the traverse in a local north/east foot grid.

    Returns (corners, quarter_corner).  The origin is the Point of Beginning;
    corners[0] is the POB and the list is not closed (4 distinct corners).
    """
    corners = [(0.0, 0.0)]
    north, east = 0.0, 0.0
    for call in CALLS:
        dn, de = leg(call)
        north, east = north + dn, east + de
        corners.append((north, east))

    # The closing call lands back on the POB; keep 4 distinct corners.
    closing = corners.pop()

    # The North 1/4 corner lies back up the tie line (reverse of the tie call).
    dn, de = leg(TIE)
    quarter_corner = (-dn, -de)

    return corners, (quarter_corner, closing)


def shoelace_area_sqft(corners: list[tuple[float, float]]) -> float:
    """Absolute polygon area, corners as (north, east) in feet."""
    total = 0.0
    for i, (n1, e1) in enumerate(corners):
        n2, e2 = corners[(i + 1) % len(corners)]
        total += e1 * n2 - e2 * n1
    return abs(total) / 2.0


def perimeter_ft() -> float:
    return sum(c[5] for c in CALLS)


# --------------------------------------------------------------------------
# Projection: local north/east feet -> WGS84 lat/lon
# --------------------------------------------------------------------------


def to_latlon(anchor: tuple[float, float], north_ft: float, east_ft: float):
    """Offset an anchor by a north/east distance in feet on a local tangent plane.

    At a few hundred feet the tangent-plane approximation is sub-millimetre,
    so this is exact for our purposes.
    """
    lat0, lon0 = anchor
    phi = math.radians(lat0)
    w = math.sqrt(1.0 - WGS84_E2 * math.sin(phi) ** 2)
    r_meridional = WGS84_A * (1.0 - WGS84_E2) / w**3
    r_prime_vertical = WGS84_A / w

    dlat = (north_ft / FT_PER_M) / r_meridional
    dlon = (east_ft / FT_PER_M) / (r_prime_vertical * math.cos(phi))

    return lat0 + math.degrees(dlat), lon0 + math.degrees(dlon)


# --------------------------------------------------------------------------
# Output writers
# --------------------------------------------------------------------------

DESCRIPTION = (
    "Exhibit “A” — part of the NW 1/4 of Section 15, T8S R7E, "
    "Bedford Township, Monroe County, Michigan. Shape and dimensions are exact "
    "per the deed; absolute position depends on the Section 15 North 1/4 corner "
    "coordinate used as the anchor."
)


def write_geojson(path, ring, pob, quarter, area_acres):
    features = [
        {
            "type": "Feature",
            "properties": {
                "name": "Exhibit “A” parcel",
                "area_acres": round(area_acres, 4),
                "description": DESCRIPTION,
            },
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        },
        {
            "type": "Feature",
            "properties": {"name": "Point of Beginning"},
            "geometry": {"type": "Point", "coordinates": list(pob)},
        },
        {
            "type": "Feature",
            "properties": {"name": "North 1/4 corner, Section 15 (anchor)"},
            "geometry": {"type": "Point", "coordinates": list(quarter)},
        },
    ]
    with open(path, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": features}, fh, indent=2)


def write_kml(path, ring, pob, quarter, area_acres):
    coords = "\n              ".join(f"{lon:.8f},{lat:.8f},0" for lon, lat in ring)
    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Exhibit &#8220;A&#8221; &#8212; Sec 15, T8S R7E, Bedford Twp, Monroe Co, MI</name>
    <description>{DESCRIPTION}</description>
    <Style id="parcel">
      <LineStyle><color>ff0000ff</color><width>3</width></LineStyle>
      <PolyStyle><color>4d0000ff</color></PolyStyle>
    </Style>
    <Placemark>
      <name>Exhibit &#8220;A&#8221; parcel ({area_acres:.3f} acres)</name>
      <styleUrl>#parcel</styleUrl>
      <Polygon>
        <tessellate>1</tessellate>
        <outerBoundaryIs><LinearRing><coordinates>
              {coords}
        </coordinates></LinearRing></outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>Point of Beginning</name>
      <Point><coordinates>{pob[0]:.8f},{pob[1]:.8f},0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>North 1/4 corner, Section 15 (anchor)</name>
      <Point><coordinates>{quarter[0]:.8f},{quarter[1]:.8f},0</coordinates></Point>
    </Placemark>
  </Document>
</kml>
"""
    with open(path, "w") as fh:
        fh.write(kml)


def write_svg(path, corners, quarter, area_acres):
    """A scaled plat drawing in local survey coordinates."""
    width, height = 660, 760
    left, right, top, bottom = 150, 120, 130, 90
    norths = [c[0] for c in corners] + [quarter[0]]
    easts = [c[1] for c in corners] + [quarter[1]]
    span_n, span_e = max(norths) - min(norths), max(easts) - min(easts)
    scale = min((width - left - right) / span_e, (height - top - bottom) / span_n)

    def xy(north, east):
        return (
            left + (east - min(easts)) * scale,
            height - bottom - (north - min(norths)) * scale,
        )

    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in (xy(*c) for c in corners))
    qx, qy = xy(*quarter)
    px, py = xy(*corners[0])

    # Traverse order is NE(POB) -> NW -> SW -> SE, so edges are
    # top, west, bottom, east.  Place each label clear of the polygon.
    placement = [
        ("inside-top", 0, 22),      # top edge: label just inside the parcel
        ("vertical-left", -6, 0),   # west edge
        ("outside-bottom", 0, 24),  # bottom edge
        ("vertical-right", 6, 0),   # east edge
    ]
    edges = []
    for i, (label, (kind, dx, dy)) in enumerate(zip(CALL_LABELS, placement)):
        x1, y1 = xy(*corners[i])
        x2, y2 = xy(*corners[(i + 1) % len(corners)])
        mx, my = (x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy
        if kind == "vertical-left":
            rot = f' transform="rotate(-90 {mx:.2f} {my:.2f})"'
        elif kind == "vertical-right":
            rot = f' transform="rotate(90 {mx:.2f} {my:.2f})"'
        else:
            rot = ""
        edges.append(
            f'<text x="{mx:.2f}" y="{my:.2f}" text-anchor="middle"'
            f' class="dim"{rot}>{label}</text>'
        )
    edge_labels = "\n    ".join(edges)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <style>
    .bg {{ fill: #ffffff; }}
    .parcel {{ fill: #d94a4a; fill-opacity: .15; stroke: #c0392b; stroke-width: 2.5; }}
    .dim {{ font: 12px "DejaVu Sans", sans-serif; fill: #333; }}
    .note {{ font: 13px "DejaVu Sans", sans-serif; fill: #444; }}
    .title {{ font: bold 16px "DejaVu Sans", sans-serif; fill: #111; }}
    .mono {{ font: 11px "DejaVu Sans Mono", monospace; fill: #555; }}
    .sectionline {{ stroke: #3b6ea5; stroke-width: 1.8; stroke-dasharray: 10 6; }}
    .tie {{ stroke: #c0392b; stroke-width: 1.2; stroke-dasharray: 3 3; }}
  </style>
  <rect class="bg" x="0" y="0" width="{width}" height="{height}"/>
  <text class="title" x="{left}" y="38">Exhibit &#8220;A&#8221; &#8212; NW 1/4, Section 15, T8S R7E</text>
  <text class="note" x="{left}" y="60">Bedford Township, Monroe County, Michigan</text>
  <text class="note" x="{left}" y="80">{area_acres:.3f} acres &#183; 39,852 sq ft &#183; closes to 0.01 ft</text>

  <line class="sectionline" x1="26" y1="{qy:.2f}" x2="{width - 26}" y2="{qy:.2f}"/>
  <text class="mono" x="26" y="{qy - 10:.2f}">north line of Sec. 15 &#8212; Erie Rd</text>

  <polygon class="parcel" points="{pts}"/>
  {edge_labels}

  <line class="tie" x1="{px:.2f}" y1="{py:.2f}" x2="{qx:.2f}" y2="{qy:.2f}"/>
  <circle cx="{qx:.2f}" cy="{qy:.2f}" r="5" fill="#111"/>
  <text class="mono" x="{qx + 11:.2f}" y="{qy + 20:.2f}">N 1/4 cor.</text>
  <text class="mono" x="{qx + 11:.2f}" y="{qy + 34:.2f}">Sec. 15</text>
  <circle cx="{px:.2f}" cy="{py:.2f}" r="5" fill="#c0392b"/>
  <text class="mono" x="{px - 12:.2f}" y="{py - 12:.2f}" text-anchor="end">P.O.B.</text>
  <text class="mono" x="{px - 12:.2f}" y="{py - 26:.2f}" text-anchor="end">7.7' W of N 1/4 cor.</text>

  <g transform="translate({width - 56},{height - 92})">
    <path d="M0,-28 L8,9 L0,2 L-8,9 Z" fill="#111"/>
    <text class="mono" x="0" y="26" text-anchor="middle">N</text>
  </g>
  <g transform="translate({left},{height - 40})">
    <line x1="0" y1="0" x2="{100 * scale:.2f}" y2="0" stroke="#111" stroke-width="2"/>
    <line x1="0" y1="-5" x2="0" y2="5" stroke="#111" stroke-width="2"/>
    <line x1="{100 * scale:.2f}" y1="-5" x2="{100 * scale:.2f}" y2="5" stroke="#111" stroke-width="2"/>
    <text class="mono" x="{50 * scale:.2f}" y="18" text-anchor="middle">100 feet</text>
  </g>
</svg>
"""
    with open(path, "w") as fh:
        fh.write(svg)


# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--anchor",
        help="LAT,LON of the North 1/4 corner of Section 15 (WGS84 decimal degrees)",
    )
    ap.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()

    if args.anchor:
        lat, lon = (float(v) for v in args.anchor.split(","))
        anchor = (lat, lon)
    else:
        anchor = DEFAULT_ANCHOR

    corners, (quarter_local, closing) = traverse()
    area_sqft = shoelace_area_sqft(corners)
    area_acres = area_sqft / 43560.0
    closure_ft = math.hypot(*closing)

    # Shift the local grid so the anchor (N 1/4 corner) is the origin, then project.
    def project(pt):
        north, east = pt[0] - quarter_local[0], pt[1] - quarter_local[1]
        lat, lon = to_latlon(anchor, north, east)
        return (lon, lat)  # GeoJSON/KML order

    ring = [project(c) for c in corners]
    ring.append(ring[0])
    pob = project(corners[0])
    quarter = project(quarter_local)

    os.makedirs(args.outdir, exist_ok=True)
    gj = os.path.join(args.outdir, "parcel.geojson")
    kml = os.path.join(args.outdir, "parcel.kml")
    svg = os.path.join(args.outdir, "parcel-plat.svg")
    write_geojson(gj, ring, pob, quarter, area_acres)
    write_kml(kml, ring, pob, quarter, area_acres)
    write_svg(svg, corners, quarter_local, area_acres)

    names = ["NE (P.O.B.)", "NW", "SW", "SE"]
    print(f"Anchor  N 1/4 cor. Sec 15 : {anchor[0]:.6f}, {anchor[1]:.6f}")
    print(f"Area                      : {area_sqft:,.1f} sq ft  ({area_acres:.4f} acres)")
    print(f"Perimeter                 : {perimeter_ft():,.2f} ft")
    print(f"Closure error             : {closure_ft:.4f} ft")
    print()
    print("Corner            local N (ft)  local E (ft)      latitude      longitude")
    for name, c, (lon, lat) in zip(names, corners, ring):
        dn, de = c[0] - quarter_local[0], c[1] - quarter_local[1]
        print(f"{name:<16}{dn:13.2f}{de:14.2f}{lat:14.6f}{lon:15.6f}")
    print()
    print("Wrote:")
    for path in (gj, kml, svg):
        print(f"  {path}")


if __name__ == "__main__":
    main()
