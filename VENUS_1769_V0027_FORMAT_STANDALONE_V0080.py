# V0080
# Audit reference: GitHub widget only; V0068 base preserved; V0080 audits and applies real data-coordinate mirror about Y-axis, not reversed axis labels.
from __future__ import annotations

import re
import urllib.request

VERSION = "V0080"
RAW_V0068 = "https://raw.githubusercontent.com/gear66me-ui/GitHub_Sandbox/main/VENUS_1769_V0027_FORMAT_STANDALONE_V0068_WIDGET.py"

source = urllib.request.urlopen(RAW_V0068, timeout=60).read().decode("utf-8")

required_base_checks = {
    "base_version_v0068": '# V0068' in source and 'VERSION = "V0068"' in source,
    "no_filled_main_sun": 'ax.plot(rs*np.cos(th), rs*np.sin(th), c=FG, lw=.5)' in source,
    "zoom_solar_limb_present": 'zax.add_patch(Circle((0,0), np.mean([st["r"][e][0] for st in (pv,va) for e in evs]), fill=False' in source,
    "clean_axis_order": 'ax.set_xlim(-1.07*rs,1.07*rs)' in source,
    "pv_color_preserved": '"color": "#42D7C3"' in source,
    "vardo_color_preserved": '"color": "#D89B18"' in source,
    "local_ca_function_preserved": 'def local_ca(c, site, a, b):' in source,
    "station_ca_assignment_preserved": 'ca = local_ca(c, site["key"], inn[0], inn[1])' in source,
    "diameters_preserved": 'Earth diameter' in source and 'Venus diameter' in source and 'Sun diameter' in source,
}
failed = [name for name, ok in required_base_checks.items() if not ok]
if failed:
    raise RuntimeError(f"V0080 base audit failed before patch: {failed}")

if 'set_xlim(1.07*rs,-1.07*rs)' in source or 'invert_xaxis' in source:
    raise RuntimeError("V0080 rejection: source contains fake mirror by reversed axis labels.")

source = source.replace("# V0068", "# V0080")
source = source.replace(
    "# Audit reference: GitHub widget only; no AI images; Matplotlib/JPL vectors; local CA, solar-limb zooms, and Earth/Venus/Sun diameters.",
    "# Audit reference: V0068 preserved; V0080 mirrors rendered X data only; axis order, labels, colors, disks, tables, and CA math unchanged."
)
source = source.replace('VERSION = "V0068"', 'VERSION = "V0080"')
source = source.replace('OUT = Path("/content/VENUS_1769_V0068_WIDGET_OUTPUT")', 'OUT = Path("/content/VENUS_1769_V0080_WIDGET_OUTPUT")')
source = source.replace('PNG = OUT / "VENUS_1769_V0068_WIDGET.png"', 'PNG = OUT / "VENUS_1769_V0080_WIDGET.png"')
source = source.replace('CSV = OUT / "VENUS_1769_V0068_CONTACTS_GEOMETRY.csv"', 'CSV = OUT / "VENUS_1769_V0080_CONTACTS_GEOMETRY.csv"')

insert_after = '''def lims(items, evs):
    pts, rs = [], []
    for st in items:
        for ev in evs:
            pts.append(st["epts"][ev]); rs.append(st["r"][ev][1])
    pts = np.array(pts); r = max(rs); m = r * .55 + 7
    return (pts[:,0].min()-r-m, pts[:,0].max()+r+m), (pts[:,1].min()-r-m, pts[:,1].max()+r+m)
'''

mirror_function = '''def mirror_display_about_y_axis_only(st):
    # V0080 visual-only mirror: x -> -x for rendered tracks and event centers.
    # This preserves all timing, local CA minimization, contact roots, radii, tables, colors, labels, and math.
    st["pts"] = st["pts"].copy()
    st["pts"][:, 0] *= -1.0
    for key in st["epts"]:
        st["epts"][key] = st["epts"][key].copy()
        st["epts"][key][0] *= -1.0
    return st
'''

if insert_after not in source:
    raise RuntimeError("V0080 patch anchor not found: lims block")
source = source.replace(insert_after, insert_after + "\n\n" + mirror_function)

old_main = '    pv, va = station(c, PV), station(c, VA)\n    g = geo(c)\n'
new_main = '    pv, va = station(c, PV), station(c, VA)\n    pv = mirror_display_about_y_axis_only(pv)\n    va = mirror_display_about_y_axis_only(va)\n    g = geo(c)\n'
if old_main not in source:
    raise RuntimeError("V0080 patch anchor not found: station assignment")
source = source.replace(old_main, new_main)
source = source.replace(
    '"NO AI IMAGES — Matplotlib only. JPL Horizons geometric ecliptic vectors; diameters from stated reduction constants."',
    '"NO AI IMAGES — Matplotlib only. V0080: V0068 style preserved; plotted X data mirrored about Y-axis only."'
)

required_after_patch = {
    "version_v0080": '# V0080' in source and 'VERSION = "V0080"' in source,
    "real_data_mirror_tracks": 'st["pts"][:, 0] *= -1.0' in source,
    "real_data_mirror_events": 'st["epts"][key][0] *= -1.0' in source,
    "mirror_called_pv": 'pv = mirror_display_about_y_axis_only(pv)' in source,
    "mirror_called_vardo": 'va = mirror_display_about_y_axis_only(va)' in source,
    "axis_not_reversed": 'ax.set_xlim(-1.07*rs,1.07*rs)' in source and 'ax.set_xlim(1.07*rs,-1.07*rs)' not in source,
    "main_limb_preserved": 'ax.plot(rs*np.cos(th), rs*np.sin(th), c=FG, lw=.5)' in source,
    "zoom_limb_preserved": 'zax.add_patch(Circle((0,0), np.mean([st["r"][e][0] for st in (pv,va) for e in evs]), fill=False' in source,
    "no_orange_sun_fill": 'facecolor="#4' not in source and 'alpha=.16, lw=.35' in source,
    "local_ca_preserved": 'ca = local_ca(c, site["key"], inn[0], inn[1])' in source,
}
failed_after = [name for name, ok in required_after_patch.items() if not ok]
if failed_after:
    raise RuntimeError(f"V0080 patch audit failed: {failed_after}")

print("V0080 AUDIT")
for name, ok in required_after_patch.items():
    print(f"{name}: {'PASS' if ok else 'FAIL'}")
print("V0080 audit complete: PASS")

exec(compile(source, "VENUS_1769_V0027_FORMAT_STANDALONE_V0080_EXPANDED.py", "exec"), globals())
# V0080
