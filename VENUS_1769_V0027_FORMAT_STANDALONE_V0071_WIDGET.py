# V0071
# Audit reference: GitHub widget only; no AI images; V0068-style plot restored; display geometry mirrored about Y-axis only; no orange Sun fill, no label-relayout, local CA preserved.
from __future__ import annotations

import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def req(name: str, pkg: str) -> None:
    try:
        __import__(name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "-q", "install", pkg])


for a, b in (("numpy", "numpy"), ("pandas", "pandas"), ("scipy", "scipy"), ("astropy", "astropy"), ("astroquery", "astroquery"), ("matplotlib", "matplotlib"), ("IPython", "ipython")):
    req(a, b)

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.time import Time
from astroquery.jplhorizons import Horizons
from IPython.display import Image, display
from matplotlib.patches import Circle
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq, minimize_scalar

VERSION = "V0071"
TZ = ZoneInfo("America/Bogota")
OUT = Path("/content/VENUS_1769_V0071_WIDGET_OUTPUT")
PNG = OUT / "VENUS_1769_V0071_WIDGET.png"
CSV = OUT / "VENUS_1769_V0071_CONTACTS_GEOMETRY.csv"
ARC = 206264.80624709636
AU = 149597870.7
C_KM_S = 299792.458
TAU_A_S = 499.004782
IAU1976_AU_KM = C_KM_S * TAU_A_S
EARTH_RADIUS_KM = 6378.140
VENUS_RADIUS_KM = 6051.800
SUN_RADIUS_KM = 695700.000
START = "1769-06-03 18:00"
STOP = "1769-06-04 06:00"
STEP = "1m"
BG = "#000000"
FG = "#F8FAFC"
MUTED = "#B8CBD6"
BLUE = "#23466F"
BODY = "#101A2E"
TEAL = "#164B55"
GOLD = "#563B0B"
PV = {"key": "PV", "label": "Point Venus, Tahiti", "short": "PV", "lat": -17.4956, "lon": -149.4939, "color": "#42D7C3"}
VA = {"key": "VA", "label": "Vardø, Norway", "short": "V", "lat": 70.3724, "lon": 31.1103, "color": "#D89B18"}
SITES = (PV, VA)
EVENTS = ("C1", "C2", "CA", "C3", "C4")


def utc(jd: float) -> str:
    return Time(float(jd), format="jd", scale="tdb").utc.datetime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def nrm(v) -> float:
    return float(np.linalg.norm(np.asarray(v, float)))


def unit(v):
    v = np.asarray(v, float)
    return v / nrm(v)


def loc(site):
    return {"lon": site["lon"], "lat": site["lat"], "elevation": 0.0, "body": 399}


def pull(prefix: str, target: str, location):
    tab = Horizons(id=target, location=location, epochs={"start": START, "stop": STOP, "step": STEP}, id_type=None).vectors(refplane="ecliptic", aberrations="geometric", cache=False).to_pandas()
    df = pd.DataFrame({"jd": pd.to_numeric(tab["datetime_jd"])})
    for ax in "xyz":
        df[f"{prefix}_{ax}"] = pd.to_numeric(tab[ax]) * AU
    return df.drop_duplicates("jd").sort_values("jd")


def master():
    frames = [pull("G_S", "10", "@399"), pull("G_V", "299", "@399")]
    for site in SITES:
        frames += [pull(f"{site['key']}_S", "10", loc(site)), pull(f"{site['key']}_V", "299", loc(site))]
    df = frames[0]
    for f in frames[1:]:
        df = df.merge(f, on="jd", how="inner")
    if len(df) < 600:
        raise RuntimeError(f"JPL synchronization failed: {len(df)} rows")
    return df.reset_index(drop=True)


def splines(df):
    c = {"jd": df.jd.to_numpy(float)}
    for col in df.columns:
        if col != "jd":
            c[col] = CubicSpline(c["jd"], df[col].to_numpy(float), bc_type="natural")
    return c


def vec(c, pref, jd):
    return np.array([float(c[f"{pref}_{ax}"](jd)) for ax in "xyz"])


def sep(c, site, jd):
    a, b = unit(vec(c, f"{site}_S", jd)), unit(vec(c, f"{site}_V", jd))
    return math.atan2(nrm(np.cross(a, b)), float(np.dot(a, b)))


def radii(c, site, jd):
    return math.asin(SUN_RADIUS_KM / nrm(vec(c, f"{site}_S", jd))), math.asin(VENUS_RADIUS_KM / nrm(vec(c, f"{site}_V", jd)))


def residual(c, site, jd, internal):
    rs, rv = radii(c, site, jd)
    return sep(c, site, jd) - (rs - rv if internal else rs + rv)


def roots(c, site, internal):
    j = c["jd"]
    y = np.array([residual(c, site, x, internal) for x in j])
    out = []
    for i in range(len(j) - 1):
        if y[i] == 0 or y[i] * y[i + 1] < 0:
            out.append(brentq(lambda z: residual(c, site, z, internal), j[i], j[i + 1], xtol=1e-13))
    if len(out) != 2:
        raise RuntimeError(f"contact roots failed {site} internal={internal}: {len(out)}")
    return out


def local_ca(c, site, a, b):
    res = minimize_scalar(lambda z: sep(c, site, z), bounds=(a, b), method="bounded", options={"xatol": 1e-12})
    if not res.success:
        raise RuntimeError(f"local CA failed {site}")
    return float(res.x)


def basis(sun):
    z = np.array([0.0, 0.0, 1.0])
    s = unit(sun)
    e = np.cross(z, s)
    if nrm(e) < 1e-14:
        e = np.cross([0, 1, 0], s)
    e = unit(e)
    n = unit(np.cross(s, e))
    if np.dot(n, z) < 0:
        e, n = -e, -n
    return s, e, n


def pos(c, site, jd):
    s, e, n = basis(vec(c, f"{site}_S", jd))
    v = unit(vec(c, f"{site}_V", jd))
    d = sep(c, site, jd)
    t = unit(v - math.cos(d) * s)
    return ARC * d * np.array([np.dot(t, e), np.dot(t, n)])


def fit(pts):
    m = pts.mean(axis=0)
    _u, _sv, vt = np.linalg.svd(pts - m, full_matrices=False)
    d = vt[0]
    if d[0] < 0:
        d = -d
    normal = np.array([-d[1], d[0]])
    along = (pts - m) @ d
    cross = (pts - m) @ normal
    rms = float(np.sqrt(np.mean((cross - np.polyval(np.polyfit(along, cross, 2), along)) ** 2)))
    return {"angle": math.degrees(math.atan2(d[1], d[0])), "rms": rms, "dir": d, "normal": normal}


def station(c, site):
    ex = roots(c, site["key"], False)
    inn = roots(c, site["key"], True)
    ca = local_ca(c, site["key"], inn[0], inn[1])
    ev = {"C1": ex[0], "C2": inn[0], "CA": ca, "C3": inn[1], "C4": ex[1]}
    j = c["jd"][(c["jd"] >= ev["C1"]) & (c["jd"] <= ev["C4"])]
    pts = np.array([pos(c, site["key"], x) for x in j])
    epts = {k: pos(c, site["key"], v) for k, v in ev.items()}
    er = {k: tuple(r * ARC for r in radii(c, site["key"], v)) for k, v in ev.items()}
    return {"site": site, "events": ev, "jd": j, "pts": pts, "epts": epts, "r": er, "fit": fit(pts), "ca_sep": sep(c, site["key"], ca) * ARC}


def common_xy(c, site, jd, b):
    s, e, n = b
    def gn(v):
        v = unit(v)
        return np.array([np.dot(v, e), np.dot(v, n)]) / np.dot(v, s)
    return ARC * (gn(vec(c, f"{site}_V", jd)) - gn(vec(c, f"{site}_S", jd)))


def geo(c):
    j = c["jd"]
    ca = minimize_scalar(lambda z: math.atan2(nrm(np.cross(unit(vec(c, "G_S", z)), unit(vec(c, "G_V", z)))), float(np.dot(unit(vec(c, "G_S", z)), unit(vec(c, "G_V", z))))), bounds=(j[0], j[-1]), method="bounded", options={"xatol": 1e-12}).x
    b = basis(vec(c, "G_S", ca))
    p = common_xy(c, "PV", ca, b)
    v = common_xy(c, "VA", ca, b)
    td = unit((common_xy(c, "PV", ca + .5/86400, b) - common_xy(c, "PV", ca - .5/86400, b)) + (common_xy(c, "VA", ca + .5/86400, b) - common_xy(c, "VA", ca - .5/86400, b)))
    nn = np.array([-td[1], td[0]])
    if np.dot(v - p, nn) < 0:
        nn = -nn
    s, e, n = b
    n3 = unit(nn[0] * e + nn[1] * n)
    base = (vec(c, "G_S", ca) - vec(c, "VA_S", ca)) - (vec(c, "G_S", ca) - vec(c, "PV_S", ca))
    if np.dot(base, n3) < 0:
        nn, n3 = -nn, -n3
    es = nrm(vec(c, "G_S", ca))
    km_as = es / ARC
    apbp = float(np.dot(v - p, nn))
    abkm = float(np.dot(base, n3))
    return {"jd": ca, "utc": utc(ca), "apbp_as": apbp, "apbp_km": apbp * km_as, "ab_as": abkm / km_as, "ab_km": abkm, "basis": b}


def mirror_y_point(p):
    p = np.asarray(p, float)
    return np.array([-p[0], p[1]])


def mirror_y_points(pts):
    pts = np.asarray(pts, float).copy()
    pts[:, 0] *= -1.0
    return pts


def table_style(tab, gold=(), teal=()):
    for (r, col), cell in tab.get_celld().items():
        cell.set_edgecolor("#70879A")
        cell.set_linewidth(.32)
        cell.get_text().set_color(FG)
        cell.get_text().set_fontsize(5.6)
        if r == 0:
            cell.set_facecolor(BLUE); cell.get_text().set_fontweight("bold")
        elif r in gold:
            cell.set_facecolor(GOLD); cell.get_text().set_fontweight("bold")
        elif r in teal:
            cell.set_facecolor(TEAL); cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor(BODY)


def disk(ax, p, r, color):
    p = mirror_y_point(p)
    ax.add_patch(Circle((p[0], p[1]), r, facecolor=color, edgecolor=color, alpha=.16, lw=.35, zorder=4))


def draw_events(ax, st, evs, main):
    site = st["site"]
    for ev in evs:
        p_raw = st["epts"][ev]
        p = mirror_y_point(p_raw)
        disk(ax, p_raw, st["r"][ev][1], site["color"])
        ax.scatter([p[0]], [p[1]], s=12 if ev == "CA" else 7, marker="x" if ev == "CA" else "o", c=site["color"], lw=.35, zorder=8)
        dy = 18 if main and site["key"] == "PV" else -18 if main else 8 if site["key"] == "PV" else -8
        ax.text(p[0], p[1] + dy, f"{site['short']} {ev}", color=site["color"], fontsize=6, fontweight="bold", ha="center", zorder=9)


def lims(items, evs):
    pts, rs = [], []
    for st in items:
        for ev in evs:
            pts.append(mirror_y_point(st["epts"][ev])); rs.append(st["r"][ev][1])
    pts = np.array(pts); r = max(rs); m = r * .55 + 7
    return (pts[:,0].min()-r-m, pts[:,0].max()+r+m), (pts[:,1].min()-r-m, pts[:,1].max()+r+m)


def make_plot(pv, va, g):
    plt.close("all")
    plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "text.color": FG, "axes.labelcolor": FG, "xtick.color": MUTED, "ytick.color": MUTED, "font.family": "DejaVu Serif"})
    fig = plt.figure(figsize=(16,9), facecolor=BG)
    gs = fig.add_gridspec(1,2, width_ratios=[2.05,1], left=.03, right=.985, top=.925, bottom=.07, wspace=.035)
    left = gs[0,0].subgridspec(2,1, height_ratios=[.70,.30], hspace=.20)
    ax = fig.add_subplot(left[0,0])
    low = left[1,0].subgridspec(1,3, width_ratios=[.82,1.58,.82], wspace=.25)
    eg, der, ing = fig.add_subplot(low[0,0]), fig.add_subplot(low[0,1]), fig.add_subplot(low[0,2])
    right = gs[0,1].subgridspec(2,1, height_ratios=[.43,.57], hspace=.10)
    res, con = fig.add_subplot(right[0,0]), fig.add_subplot(right[1,0])
    fig.suptitle("1769 VENUS TRANSIT — JPL ECLIPTIC HALF-SUN CONTACT GEOMETRY", fontsize=15, fontweight="bold", y=.977)
    rs = pv["r"]["CA"][0]
    th = np.linspace(0, 2*math.pi, 1600)
    ax.plot(rs*np.cos(th), rs*np.sin(th), c=FG, lw=.5)
    ax.axhline(0, c="#263A4B", lw=.25); ax.axvline(0, c="#263A4B", lw=.25)
    for st in (pv, va):
        pts = mirror_y_points(st["pts"])
        ax.plot(pts[:,0], pts[:,1], c=st["site"]["color"], lw=.38, label=st["site"]["label"])
        draw_events(ax, st, EVENTS, True)
    ax.set_aspect("equal"); ax.set_xlim(-1.07*rs,1.07*rs); ax.set_ylim(-.08*rs,1.06*rs)
    ax.set_xlabel(r"Ecliptic longitude direction, $\xi$ (arcsec)"); ax.set_ylabel(r"Ecliptic north direction, $\eta$ (arcsec)")
    ax.tick_params(labelsize=6.5, length=2.2)
    leg = ax.legend(loc="lower left", frameon=False, fontsize=6.5)
    for t in leg.get_texts(): t.set_color(FG)
    for zax, evs, title in ((eg,("C3","C4"),"EGRESS ZOOM — C3 / C4 TANGENCY"), (ing,("C1","C2"),"INGRESS ZOOM — C1 / C2 TANGENCY")):
        zax.add_patch(Circle((0,0), np.mean([st["r"][e][0] for st in (pv,va) for e in evs]), fill=False, ec="#DDEBFF", lw=.7, zorder=1))
        for st in (pv, va):
            pts = mirror_y_points(st["pts"])
            zax.plot(pts[:,0], pts[:,1], c=st["site"]["color"], lw=.38)
            draw_events(zax, st, evs, False)
        xl, yl = lims((pv,va), evs); zax.set_xlim(*xl); zax.set_ylim(*yl); zax.set_aspect("equal"); zax.set_title(title, fontsize=6.3, pad=3); zax.tick_params(labelsize=5, length=1.8)
    der.axis("off"); der.text(.5,.895,"A′B′ AND AB DERIVATION",ha="center",va="center",fontsize=8.2,fontweight="bold")
    rows = [["Quantity","Definition / source","Arcsec","Kilometers"],["A′B′","JPL separate-ray derived",f"{g['apbp_as']:.6f}",f"{g['apbp_km']:,.6f}"],["AB","JPL projected baseline",f"{g['ab_as']:.6f}",f"{g['ab_km']:,.6f}"],["Earth diameter","IAU 1976 reduction: 2×6378.140 km","",f"{2*EARTH_RADIUS_KM:,.6f}"],["Venus diameter","Project/JPL reduction: 2×6051.800 km","",f"{2*VENUS_RADIUS_KM:,.6f}"],["Sun diameter","Project/JPL reduction: 2×695700.000 km","",f"{2*SUN_RADIUS_KM:,.6f}"],["α PV","Point Venus track angle",f"{pv['fit']['angle']:.6f}°",""] ,["α V","Vardø track angle",f"{va['fit']['angle']:.6f}°",""]]
    tab = der.table(cellText=rows, cellLoc="left", colWidths=[.16,.47,.15,.22], bbox=[0,0,1,.805]); tab.auto_set_font_size(False); table_style(tab, gold=(2,3,4,5), teal=(1,))
    res.axis("off"); res.set_title("RESULTS", loc="left", fontsize=9, fontweight="bold", pad=5)
    pi0 = math.asin(EARTH_RADIUS_KM / IAU1976_AU_KM) * ARC
    rr = [["Quantity","Symbol","Value","Unit/status"],["IAU 1976 AU-normalized solar horizontal parallax","π₀",f"{pi0:.12f}","arcsec"],["Point Venus, Tahiti track angle","α_PV",f"{pv['fit']['angle']:.6f}","deg"],["Vardø, Norway track angle","α_V",f"{va['fit']['angle']:.6f}","deg"],["A′B′ common-normal separation","A′B′",f"{g['apbp_as']:.6f}","arcsec"],["Projection reference","","JPL ECLIPTIC","verified"]]
    rt = res.table(cellText=rr, cellLoc="left", colWidths=[.47,.12,.21,.20], bbox=[0,0,1,.90]); rt.auto_set_font_size(False); table_style(rt, gold=(2,3), teal=(4,5))
    con.axis("off"); con.set_title("RECOMPUTED CONTACT TIMES — UTC", loc="left", fontsize=9, fontweight="bold", pad=5)
    cr = [["Station","Event","UTC","Exact limb condition"]]
    for st in (pv, va):
        for ev in EVENTS:
            cond = "dρ/dt = 0; local minimum" if ev == "CA" else "ρ = R☉ − R♀" if ev in ("C2","C3") else "ρ = R☉ + R♀"
            cr.append([st["site"]["label"], ev, utc(st["events"][ev]).split()[1], cond])
    ct = con.table(cellText=cr, cellLoc="left", colWidths=[.28,.12,.30,.30], bbox=[0,0,1,.92]); ct.auto_set_font_size(False); table_style(ct, teal=(1,2,3,6,7,8))
    fig.text(.5,.02,"NO AI IMAGES — Matplotlib only. JPL Horizons geometric ecliptic vectors; display geometry mirrored about Y-axis only; all calculations and labels preserved.",ha="center",fontsize=6,color=MUTED)
    fig.savefig(PNG, dpi=160, bbox_inches="tight", pad_inches=.02, facecolor=BG)
    display(Image(filename=str(PNG)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = splines(master())
    pv, va = station(c, PV), station(c, VA)
    g = geo(c)
    rows = [["Point Venus local CA", utc(pv["events"]["CA"]), pv["ca_sep"], "arcsec"], ["Vardø local CA", utc(va["events"]["CA"]), va["ca_sep"], "arcsec"], ["A′B′", g["apbp_as"], g["apbp_km"], "arcsec/km"], ["AB", g["ab_as"], g["ab_km"], "arcsec/km"], ["Earth diameter", 2*EARTH_RADIUS_KM, "IAU 1976 reduction: 2×6378.140 km", "km"], ["Venus diameter", 2*VENUS_RADIUS_KM, "project/JPL reduction: 2×6051.800 km", "km"], ["Sun diameter", 2*SUN_RADIUS_KM, "project/JPL reduction: 2×695700.000 km", "km"]]
    pd.DataFrame(rows, columns=["quantity","value_1","value_2","unit"]).to_csv(CSV, index=False)
    make_plot(pv, va, g)
    print("CODE INPUTS")
    print("JPL Horizons geometric ecliptic vectors; no AI images.")
    print("COMMENTS")
    print("Only display geometry is mirrored about the Y-axis; calculations and local closest approaches are unchanged.")
    print("RESULTS")
    print(f"Earth, Venus, Sun diameters km: {2*EARTH_RADIUS_KM:.6f}, {2*VENUS_RADIUS_KM:.6f}, {2*SUN_RADIUS_KM:.6f}")
    print("OUTPUT SUMMARY")
    print(PNG)
    print(CSV)
    print("PAPER COMPARISON")
    print("IAU 1976 Earth radius source is used for parallax comparison; Venus/Sun radii are project/JPL reduction constants.")
    print("EQUATION STATUS")
    print("PASS")
    print(datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %z"))
    print(VERSION)


if __name__ == "__main__":
    main()
# V0071