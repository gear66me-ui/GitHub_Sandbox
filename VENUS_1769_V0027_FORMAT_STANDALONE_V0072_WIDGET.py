# V0072
# Audit reference: GitHub widget only; no AI images; preserves V0068 math/style and mirrors plotted X coordinates about the Y-axis only.
from __future__ import annotations

import urllib.request

VERSION = "V0072"
RAW_V0068 = "https://raw.githubusercontent.com/gear66me-ui/GitHub_Sandbox/main/VENUS_1769_V0027_FORMAT_STANDALONE_V0068_WIDGET.py"

source = urllib.request.urlopen(RAW_V0068, timeout=60).read().decode("utf-8")
source = source.replace("# V0068", "# V0072")
source = source.replace(
    "# Audit reference: GitHub widget only; no AI images; Matplotlib/JPL vectors; local CA, solar-limb zooms, and Earth/Venus/Sun diameters.",
    "# Audit reference: V0068 preserved; visual-only mirror about Y-axis by negating plotted X coordinates; no math/style/color/label changes."
)
source = source.replace('VERSION = "V0068"', 'VERSION = "V0072"')
source = source.replace('OUT = Path("/content/VENUS_1769_V0068_WIDGET_OUTPUT")', 'OUT = Path("/content/VENUS_1769_V0072_WIDGET_OUTPUT")')
source = source.replace('PNG = OUT / "VENUS_1769_V0068_WIDGET.png"', 'PNG = OUT / "VENUS_1769_V0072_WIDGET.png"')
source = source.replace('CSV = OUT / "VENUS_1769_V0068_CONTACTS_GEOMETRY.csv"', 'CSV = OUT / "VENUS_1769_V0072_CONTACTS_GEOMETRY.csv"')

insert_after = '''def lims(items, evs):
    pts, rs = [], []
    for st in items:
        for ev in evs:
            pts.append(st["epts"][ev]); rs.append(st["r"][ev][1])
    pts = np.array(pts); r = max(rs); m = r * .55 + 7
    return (pts[:,0].min()-r-m, pts[:,0].max()+r+m), (pts[:,1].min()-r-m, pts[:,1].max()+r+m)
'''

mirror_function = '''def mirror_display_about_y_axis_only(st):
    # Visual-only mirror: x -> -x for rendered track arrays and event points.
    # No timing, CA minimization, contact roots, tables, colors, labels, or radii are recomputed or changed.
    st["pts"] = st["pts"].copy()
    st["pts"][:, 0] *= -1.0
    for key in st["epts"]:
        st["epts"][key] = st["epts"][key].copy()
        st["epts"][key][0] *= -1.0
    return st
'''

if insert_after not in source:
    raise RuntimeError("V0068 patch anchor not found: lims block")
source = source.replace(insert_after, insert_after + "\n\n" + mirror_function)

old_main = '    pv, va = station(c, PV), station(c, VA)\n    g = geo(c)\n'
new_main = '    pv, va = station(c, PV), station(c, VA)\n    pv = mirror_display_about_y_axis_only(pv)\n    va = mirror_display_about_y_axis_only(va)\n    g = geo(c)\n'
if old_main not in source:
    raise RuntimeError("V0068 patch anchor not found: station assignment")
source = source.replace(old_main, new_main)
source = source.replace(
    '"NO AI IMAGES — Matplotlib only. JPL Horizons geometric ecliptic vectors; diameters from stated reduction constants."',
    '"NO AI IMAGES — Matplotlib only. V0068 style preserved; display mirrored about Y-axis by x→−x only."'
)
source = source.replace("# V0072\n# V0072", "# V0072")
exec(compile(source, "VENUS_1769_V0027_FORMAT_STANDALONE_V0072_WIDGET_EXPANDED.py", "exec"), globals())
# V0072
