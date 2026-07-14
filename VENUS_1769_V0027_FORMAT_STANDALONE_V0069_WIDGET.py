# V0069
# Audit reference: GitHub widget only; no AI images; patches V0068 to apply 180-degree display flip about the Y-axis for NW-to-SE Venus transit video orientation.
from __future__ import annotations

import urllib.request

VERSION = "V0069"
BASE_URL = "https://raw.githubusercontent.com/gear66me-ui/GitHub_Sandbox/main/VENUS_1769_V0027_FORMAT_STANDALONE_V0068_WIDGET.py"


def patch_source(source: str) -> str:
    source = source.replace("# V0068", "# V0069")
    source = source.replace(
        "# Audit reference: GitHub widget only; no AI images; Matplotlib/JPL vectors; local CA, solar-limb zooms, and Earth/Venus/Sun diameters.",
        "# Audit reference: GitHub widget only; no AI images; Matplotlib/JPL vectors; local CA, solar-limb zooms, diameters, and 180-degree Y-axis display flip."
    )
    source = source.replace('VERSION = "V0068"', 'VERSION = "V0069"')
    source = source.replace("VENUS_1769_V0068_WIDGET_OUTPUT", "VENUS_1769_V0069_WIDGET_OUTPUT")
    source = source.replace("VENUS_1769_V0068_WIDGET.png", "VENUS_1769_V0069_WIDGET.png")
    source = source.replace("VENUS_1769_V0068_CONTACTS_GEOMETRY.csv", "VENUS_1769_V0069_CONTACTS_GEOMETRY.csv")
    source = source.replace(
        "EVENTS = (\"C1\", \"C2\", \"CA\", \"C3\", \"C4\")\n",
        "EVENTS = (\"C1\", \"C2\", \"CA\", \"C3\", \"C4\")\nDISPLAY_Y_AXIS_180_FLIP = True\n"
    )
    source = source.replace(
        "ax.set_aspect(\"equal\"); ax.set_xlim(-1.07*rs,1.07*rs); ax.set_ylim(-.08*rs,1.06*rs)",
        "ax.set_aspect(\"equal\"); ax.set_xlim(-1.07*rs,1.07*rs); ax.set_ylim(-.08*rs,1.06*rs); ax.invert_xaxis()"
    )
    source = source.replace(
        "xl, yl = lims((pv,va), evs); zax.set_xlim(*xl); zax.set_ylim(*yl); zax.set_aspect(\"equal\"); zax.set_title(title, fontsize=6.3, pad=3); zax.tick_params(labelsize=5, length=1.8)",
        "xl, yl = lims((pv,va), evs); zax.set_xlim(*xl); zax.set_ylim(*yl); zax.invert_xaxis(); zax.set_aspect(\"equal\"); zax.set_title(title, fontsize=6.3, pad=3); zax.tick_params(labelsize=5, length=1.8)"
    )
    source = source.replace(
        "NO AI IMAGES — Matplotlib only. JPL Horizons geometric ecliptic vectors; diameters from stated reduction constants.",
        "NO AI IMAGES — Matplotlib only. JPL Horizons geometric ecliptic vectors; diameters from stated reduction constants; display flipped about Y-axis for NW→SE transit-video orientation."
    )
    source = source.replace(
        "print(\"Local closest approach is independently minimized for Point Venus and Vardø.\")",
        "print(\"Local closest approach is independently minimized for Point Venus and Vardø.\")\n    print(\"Display orientation: 180-degree flip about Y-axis; ingress northwest, egress southeast.\")"
    )
    if "ax.invert_xaxis()" not in source or "zax.invert_xaxis()" not in source:
        raise RuntimeError("Y-axis 180-degree display flip patch failed.")
    return source


def main() -> None:
    with urllib.request.urlopen(BASE_URL, timeout=60) as response:
        source = response.read().decode("utf-8")
    patched = patch_source(source)
    code = compile(patched, "VENUS_1769_V0027_FORMAT_STANDALONE_V0069_WIDGET.py", "exec")
    namespace = {"__name__": "__main__", "__file__": "VENUS_1769_V0027_FORMAT_STANDALONE_V0069_WIDGET.py"}
    exec(code, namespace)


if __name__ == "__main__":
    main()
# V0069
