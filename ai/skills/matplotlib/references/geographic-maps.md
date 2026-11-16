# Geographic figures and flow maps

## Geographic Map Patterns

**International figures require world land-mass GeoJSON — US states GeoJSON produces empty space**: Any figure that shows destinations outside the US (international shipping, global OD flow maps) needs a world countries GeoJSON, not the US states GeoJSON used for domestic maps. Using only US states causes all non-US geography to render as blank canvas with floating dots and arcs — visually indistinguishable from a broken figure.

- Domestic-only maps: `us-states.geojson` (download from `https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json`)
- International or mixed maps: `world-countries.geojson` from Natural Earth or equivalent (e.g., `https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson`)
- Cache both locally in `data/figures/` and load via `Path(__file__).parent.parent / "data" / "figures" / "world-countries.geojson"` with a download fallback

**Separate domestic and international into distinct figure panels or modules**: Do not try to combine a US-scale map and a world-scale map into a single two-panel layout where the US panel is CONUS-extent and the world panel is also CONUS-extent. The projections fight — CONUS xlim (`-130, -65`) cuts off Atlantic destinations. Pattern that works:
- Domestic figure: single CONUS panel, `xlim=(-130, -65)`, `ylim=(24, 50)`, US states GeoJSON
- International figure: Mercator world extent, `xlim=(-130, 10)` covers US west coast through West Africa, `ylim=(-5, 65)` covers equatorial Africa through Canada, world countries GeoJSON

**OD flow arc direction**: Use `matplotlib.patches.ConnectionPatch` for arcs that cross figure panels, or `FancyArrowPatch` with `connectionstyle="arc3,rad=0.15"` for within-axes arcs. For eastward routes (US → Europe/Africa), set `rad=0.15` to curve north over the Atlantic. For westward routes, negative rad curves south. Always set `clip_on=False` on arcs — they frequently cross axes boundaries and will be silently clipped otherwise.

**Mercator y-projection for hand-rolled world maps**: When not using cartopy, convert latitude to Mercator y manually:
```python
import numpy as np

def _merc_y(lat_deg: float) -> float:
    lat_rad = np.radians(lat_deg)
    return np.log(np.tan(np.pi / 4 + lat_rad / 2))
```
Apply to all coordinate rings in the GeoJSON before drawing polygons. Apply to all destination/origin lat values before placing dots and arcs. xlim/ylim must be set in Mercator-y space, not degrees.
