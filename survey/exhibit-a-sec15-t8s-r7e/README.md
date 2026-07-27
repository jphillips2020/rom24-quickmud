# Exhibit "A" — parcel plot

Plots the metes-and-bounds description from Exhibit "A" onto a map.

> Land situated in the Township of Bedford, County of Monroe, State of Michigan,
> described as: That part of the Northwest quarter of Section 15, Town 8 South,
> Range 7 East, Bedford Township, Monroe County, Michigan, described as follows:
> Commencing at a point 7.7 feet South 89 degrees 58 minutes 30 seconds West
> from the North one quarter corner of said Section 15; thence South 89 degrees
> 58 minutes 30 seconds West 157.98 feet; thence South 0 degrees 40 minutes West
> 249.95 feet; thence due East 160.88 feet; thence due North 250.00 feet to the
> Point of Beginning.

## Files

| File | What it is |
| --- | --- |
| `plot_parcel.py` | Computes the traverse and writes the three files below |
| `parcel.kml` | Import into Google Earth or Google My Maps |
| `parcel.geojson` | Import into geojson.io, QGIS, Leaflet, Mapbox |
| `parcel-plat.svg` | Scaled plat drawing (no georeferencing needed) |

## Computed geometry

This part is **exact** — it falls straight out of the deed.

The description is a closed four-sided figure. The "Commencing at" point is
itself the Point of Beginning: running the four calls from it returns to within
**0.0085 ft**, so the deed closes essentially perfectly.

| | |
| --- | --- |
| Area | 39,852.3 sq ft — **0.9149 acres** |
| Perimeter | 818.81 ft |
| Frontage on the north section line | 157.98 ft |
| Depth | 250 ft |
| Shape | Very slightly non-rectangular; the west line leans 0°40' west of south, making the south line 2.90 ft longer than the north line |

Corner offsets from the North 1/4 corner of Section 15, in feet:

| Corner | North | East |
| --- | --- | --- |
| NE (P.O.B.) | 0.00 | −7.70 |
| NW | −0.07 | −165.68 |
| SW | −250.01 | −168.59 |
| SE | −250.01 | −7.71 |

The parcel's north line is coincident with the north line of Section 15, so it
fronts on Erie Road. The tie is only 7.7 ft, which means the parcel's east line
sits essentially on the north–south quarter line of Section 15.

## Georeferencing — read this before trusting the position

The **shape is exact; the absolute position is an estimate.** No authoritative
PLSS or parcel service was reachable from the environment this was built in
(`gis.blm.gov`, Census, ArcGIS, OSM/Nominatim and Overpass were all blocked by
egress policy), so the North 1/4 corner of Section 15 was reconstructed from
the PLSS grid using published township geometry:

**Longitude.** Ida Township (T7S R7E) and Bedford Township (T8S R7E) both
publish a centroid longitude of 83°35′19″W. Being the same range, that is the
range's north–south centre line — the section line 3 miles east of the range's
west boundary, which is the Section 15/16 line, i.e. Jackman Road. That is
corroborated independently by the geocode of the Bedford Township Government
Center at 8100 Jackman Rd (−83.5861), and by Temperance's CDP centroid falling
one mile further east on Lewis Ave. Section 15 therefore runs Jackman Rd to
Lewis Ave, and its North 1/4 corner is the midpoint of that mile.

**Latitude.** Ida Township is a regular 36 sq mi township, so its published
centroid fixes the T7S/T8S line at 41.82208. Section 15 sits in the third tier
of sections from the north, so its north line is 2 miles south of it.

Resulting anchor: **41.79309, −83.57760**

**This anchor is known to be wrong.** Checked against aerial imagery in Google
Earth it puts the parcel roughly three lots away, on golf course ground — an
error on the order of a few hundred feet. It confirms the right stretch of Erie
Road and nothing finer. Correct it before using any coordinate from here.

### Re-anchoring

Everything is parameterised on that one coordinate, so correcting it is a
one-liner. Get the true corner from Monroe County GIS, the Michigan
Remonumentation records, a surveyor, or by right-clicking the spot in Google
Earth or Google Maps, then:

```sh
python3 plot_parcel.py --anchor 41.7930500,-83.5779000
```

All three output files are rewritten in place against the new corner.

`index.html` does the same thing interactively, and will also take the parcel's
road-side east corner (the P.O.B.) instead of the section corner — that is the
point you can actually identify on imagery. It sits 7.7 ft west of the section
corner, and the page converts between the two.

## Importing

- **Google My Maps** — <https://mymaps.google.com> → *Create a new map* →
  *Import* → upload `parcel.kml`.
- **Google Earth** — <https://earth.google.com/web> → *Projects* → *Import KML
  file* → `parcel.kml`. Best option for checking the fit against imagery.
- **geojson.io** — <https://geojson.io> → *Open* → `parcel.geojson`.
- **QGIS / ArcGIS** — open either file directly.

Coordinates are WGS84 (EPSG:4326).

## Assumptions

- Deed bearings are treated as true-north bearings. If the deed's basis is grid
  or magnetic north, the parcel rotates slightly about the anchor; over 250 ft
  the effect of the 1′30″ implied by the section-line call is 0.11 ft, i.e.
  negligible.
- Distances are horizontal ground distances in US survey feet.
