# V0070
# Audit reference: Widget-only GitHub loader. Applies exactly one display change to V0068_WIDGET: mirror x-axis about the Y-axis; no other plot/style/calculation edits.
from __future__ import annotations

from pathlib import Path
import urllib.request
import runpy

VERSION = "V0070"
BASE_URL = "https://raw.githubusercontent.com/gear66me-ui/GitHub_Sandbox/main/VENUS_1769_V0027_FORMAT_STANDALONE_V0068_WIDGET.py"
OUT = Path("/content/VENUS_1769_V0027_FORMAT_STANDALONE_V0070_WIDGET_EXPANDED.py")

text = urllib.request.urlopen(BASE_URL, timeout=60).read().decode("utf-8")
text = text.replace("# V0068", "# V0070")
text = text.replace('VERSION = "V0068"', 'VERSION = "V0070"')
text = text.replace("VENUS_1769_V0068_WIDGET_OUTPUT", "VENUS_1769_V0070_WIDGET_OUTPUT")
text = text.replace("VENUS_1769_V0068_WIDGET.png", "VENUS_1769_V0070_WIDGET.png")
text = text.replace("VENUS_1769_V0068_CONTACTS_GEOMETRY.csv", "VENUS_1769_V0070_CONTACTS_GEOMETRY.csv")

old_main = 'ax.set_aspect("equal"); ax.set_xlim(-1.07*rs,1.07*rs); ax.set_ylim(-.08*rs,1.06*rs)'
new_main = 'ax.set_aspect("equal"); ax.set_xlim(1.07*rs,-1.07*rs); ax.set_ylim(-.08*rs,1.06*rs)'
if old_main not in text:
    raise RuntimeError("Main-axis V0068 mirror target not found; aborting to avoid unintended changes.")
text = text.replace(old_main, new_main, 1)

old_zoom = 'xl, yl = lims((pv,va), evs); zax.set_xlim(*xl); zax.set_ylim(*yl); zax.set_aspect("equal"); zax.set_title(title, fontsize=6.3, pad=3); zax.tick_params(labelsize=5, length=1.8)'
new_zoom = 'xl, yl = lims((pv,va), evs); zax.set_xlim(xl[1], xl[0]); zax.set_ylim(*yl); zax.set_aspect("equal"); zax.set_title(title, fontsize=6.3, pad=3); zax.tick_params(labelsize=5, length=1.8)'
if old_zoom not in text:
    raise RuntimeError("Zoom-axis V0068 mirror target not found; aborting to avoid unintended changes.")
text = text.replace(old_zoom, new_zoom, 1)

text = text.replace(
    "NO AI IMAGES — Matplotlib only. JPL Horizons geometric ecliptic vectors; diameters from stated reduction constants.",
    "NO AI IMAGES — Matplotlib only. JPL Horizons geometric ecliptic vectors; diameters from stated reduction constants; display mirrored about Y-axis only."
)

if "facecolor='#4" in text or "facecolor=\"#4" in text:
    raise RuntimeError("Unexpected solar fill color detected; aborting.")

OUT.write_text(text, encoding="utf-8")
runpy.run_path(str(OUT), run_name="__main__")
# V0070
