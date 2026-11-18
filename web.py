#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grafická podoba předpovědi: stránka docs/index.html (iPhone, iPad) a obrázky pro Telegram.

Vstup je slovník, který pocasi.py ukládá do out/predpoved.json. Všechno se kreslí tady
jako SVG, bez cizích knihoven a bez stahování čehokoli z internetu.
Samostatné spuštění:  python web.py out/predpoved.json
"""
import datetime as dt
import html
import json
import os
import sys
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Prague")
DAYS = ["po", "út", "st", "čt", "pá", "so", "ne"]
DAYS_LONG = ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"]
DIRS = ["S", "SV", "V", "JV", "J", "JZ", "Z", "SZ"]
TABS = {"cerna": "Lanový park", "frymburk": "Frymburk"}
FONT = "ui-rounded, 'SF Pro Rounded', -apple-system, system-ui, 'DejaVu Sans', sans-serif"

C = {   # barvy: tmavá hladina přehrady, ověřeno na rozlišitelnost i pro barvoslepé
    "bg": "#0e1f26", "panel": "#142a33", "night": "#0a171c", "grid": "#25404a",
    "text": "#eaf1ef", "muted": "#93aab0", "temp": "#d95926", "band": "#d95926",
    "rain": "#3987e5", "wind": "#199e70", "gust": "#9085e9", "sun": "#f2b84b", "cloud": "#b9c7cb", "snow": "#e8f1f4",
}


def esc(x):
    return html.escape(str(x), quote=True)


def num(x, nd=0):
    if x is None:
        return "–"
    s = ("%.*f" % (nd, x)).replace("-", "−").replace(".", ",")
    return "0" if s in ("−0", "−0,0") else s


def local(tiso):
    return dt.datetime.strptime(tiso, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc).astimezone(TZ)


# --------------------------------------------------------------------------
# Symboly počasí
# --------------------------------------------------------------------------

def classify(cloud, precip, prob, night, snow=False, storm=False, hours=3):
    """Symbol pro úsek: precip = úhrn v mm za úsek, prob = podíl modelů se srážkami v %."""
    cloud = 50 if cloud is None else cloud
    precip = precip or 0.0
    prob = prob or 0.0
    lim = 0.3 * hours / 3.0
    if storm:
        return "storm"
    if precip >= lim and prob >= 40:
        if snow:
            return "snow"
        if precip >= 10 * lim:
            return "heavy"
        return "rain" if precip >= 3.3 * lim else "drizzle"
    if cloud >= 80:
        return "cloudy"
    if cloud >= 30:
        return "partly-night" if night else "partly-day"
    return "clear-night" if night else "clear-day"


NAMES = {"clear-day": "jasno", "clear-night": "jasná noc", "partly-day": "polojasno", "partly-night": "polojasno",
         "cloudy": "zataženo", "drizzle": "slabý déšť", "rain": "déšť", "heavy": "silný déšť", "snow": "sněžení", "storm": "bouřka"}


def _cloud(x, y, s, fill):
    return ('<path transform="translate(%.1f %.1f) scale(%.3f)" fill="%s" d="M7 20a5 5 0 0 1-.6-9.96A7 7 0 0 1 19.9 8.6 '
            '5.5 5.5 0 0 1 20.5 20Z"/>' % (x, y, s, fill))


def symbol(code, x, y, size=28):
    """SVG skupina se symbolem, levý horní roh v (x, y)."""
    k = size / 28.0
    g = ['<g transform="translate(%.1f %.1f) scale(%.3f)">' % (x, y, k)]
    sun = ('<circle cx="{cx}" cy="{cy}" r="{r}" fill="%s"/>' % C["sun"])
    rays = "".join('<line x1="{cx}" y1="{y1}" x2="{cx}" y2="{y2}" stroke="%s" stroke-width="1.8" stroke-linecap="round" '
                   'transform="rotate(%d {cx} {cy})"/>' % (C["sun"], a) for a in range(0, 360, 45))
    moon = '<path d="M{mx} {my}a7.5 7.5 0 1 0 8.2 10.3A6 6 0 0 1 {mx} {my}Z" fill="%s"/>' % C["snow"]
    if code == "clear-day":
        g.append((sun + rays).format(cx=14, cy=14, r=5.5, y1=3.2, y2=5.6))
    elif code == "clear-night":
        g.append(moon.format(mx=13, my=5.5))
    elif code in ("partly-day", "partly-night"):
        g.append((sun + rays).format(cx=10, cy=10, r=4.2, y1=2.2, y2=4.0) if code == "partly-day" else moon.format(mx=9, my=2.5))
        g.append(_cloud(4, 5, 0.86, C["cloud"]))
    else:
        g.append(_cloud(1.5, -2, 1.0, C["cloud"] if code in ("cloudy", "drizzle", "snow") else "#8fa2a8"))
        drop = '<path d="M{x} {y}l-1.6 4.6" stroke="%s" stroke-width="2" stroke-linecap="round"/>' % C["rain"]
        flake = '<circle cx="{x}" cy="{y}" r="1.5" fill="%s"/>' % C["snow"]
        if code == "drizzle":
            g.append(drop.format(x=14.5, y=20.5))
        elif code == "rain":
            g.append(drop.format(x=11, y=20.5) + drop.format(x=17.5, y=20.5))
        elif code == "heavy":
            g.append(drop.format(x=8.5, y=20.5) + drop.format(x=14.5, y=20.5) + drop.format(x=20.5, y=20.5))
        elif code == "snow":
            g.append(flake.format(x=9, y=22) + flake.format(x=14.5, y=24.5) + flake.format(x=20, y=22))
        elif code == "storm":
            g.append('<path d="M15.5 18.5l-4.5 5h3.4l-1.6 4.3 5.4-6h-3.6l1.9-3.3Z" fill="%s"/>' % C["sun"])
    g.append("</g>")
    return "".join(g)


def arrow(deg, cx, cy, r=7):
    """Šipka ve směru, kam vítr fouká (deg = odkud fouká)."""
    return ('<g transform="rotate(%.0f %.1f %.1f)"><path d="M%.1f %.1fl%.1f %.1fh-%.1fv%.1fh-%.1fv-%.1fh-%.1fZ" fill="%s"/></g>'
            % ((deg + 180) % 360, cx, cy, cx, cy - r, r * 0.62, r * 0.9, r * 0.36, r * 1.1, r * 0.52, r * 1.1, r * 0.36, C["muted"]))


# --------------------------------------------------------------------------
# Meteogram
# --------------------------------------------------------------------------

def blocks3(hours):
    """Tříhodinové úseky zarovnané na místní čas (0, 3, 6 ... h)."""
    out, cur = [], []
    for h in hours:
        lt = local(h["t"])
        if cur and lt.hour % 3 == 0:
            out.append(cur)
            cur = []
        cur.append(h)
    if cur:
        out.append(cur)
    res = []
    for b in out:
        cl = [h["C"] for h in b if h.get("C") is not None]
        res.append({"i0": hours.index(b[0]), "n": len(b),
                    "sym": classify(sum(cl) / len(cl) if cl else None, sum(h.get("P") or 0 for h in b),
                                    max([h.get("Pp") or 0 for h in b]), sum(h["night"] for h in b) * 2 > len(b),
                                    any(h.get("snow") for h in b), any(h.get("storm") for h in b), hours=len(b)),
                    "psum": sum(h.get("P") or 0 for h in b)})
    return res


def smooth(points):
    """Hladká křivka bodů (Catmull-Rom převedený na Bézierovy oblouky)."""
    if len(points) < 3:
        return "M" + " L".join("%.1f %.1f" % p for p in points)
    d = ["M%.1f %.1f" % points[0]]
    for i in range(len(points) - 1):
        p0 = points[max(i - 1, 0)]
        p1, p2 = points[i], points[i + 1]
        p3 = points[min(i + 2, len(points) - 1)]
        d.append("C%.1f %.1f %.1f %.1f %.1f %.1f" % (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                                                      p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]))
    return " ".join(d)


LAY = {"day": 20, "sym": 30, "t0": 78, "t1": 190, "p0": 214, "p1": 262, "w0": 292, "w1": 368, "arr": 388, "hr": 414, "h": 426}


def meteogram(hours, pxh=12, pad=14):
    """SVG se symboly, křivkou teploty, sloupci srážek a křivkami větru. Vrací (svg, šířka, výška)."""
    n = len(hours)
    Wd = n * pxh + 2 * pad
    L = LAY
    X = lambda i: pad + (i + 0.5) * pxh
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="%s" role="img" '
         'aria-label="Graf předpovědi po hodinách">' % (Wd, L["h"], Wd, L["h"], FONT),
         '<rect width="%d" height="%d" fill="%s"/>' % (Wd, L["h"], C["panel"])]
    # noc a hranice dnů
    i = 0
    while i < n:
        if hours[i]["night"]:
            j = i
            while j < n and hours[j]["night"]:
                j += 1
            o.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"/>' % (pad + i * pxh, L["sym"] - 6, (j - i) * pxh, L["hr"] - L["sym"] + 16, C["night"]))
            i = j
        else:
            i += 1
    for i, h in enumerate(hours):
        lt = local(h["t"])
        if lt.hour == 0 or i == 0:
            x = pad + i * pxh
            if lt.hour == 0:
                o.append('<line x1="%.1f" y1="4" x2="%.1f" y2="%d" stroke="%s" stroke-width="1"/>' % (x, x, L["h"] - 4, C["grid"]))
            left = n - i if lt.hour else min(24, n - i)
            if (24 - lt.hour if i == 0 else left) * pxh >= 70:
                o.append('<text x="%.1f" y="%d" fill="%s" font-size="13" font-weight="600">%s %d. %d.</text>'
                         % (x + 6, L["day"], C["text"], DAYS_LONG[lt.weekday()], lt.day, lt.month))
    bl = blocks3(hours)
    # symboly
    for b in bl:
        if b["n"] >= 2 or len(bl) == 1:
            cx = pad + (b["i0"] + b["n"] / 2.0) * pxh
            o.append(symbol(b["sym"], cx - 14, L["sym"], 28))
    # teplota
    lo = min(h["lo"] for h in hours)
    hi = max(h["hi"] for h in hours)
    span = max(hi - lo, 4.0)
    Y = lambda v: L["t1"] - (v - lo) / span * (L["t1"] - L["t0"] - 16)
    if lo < 0 < hi:
        o.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1" stroke-dasharray="2 4"/>' % (pad, Y(0), Wd - pad, Y(0), C["muted"]))
    up = [(X(i), Y(h["hi"])) for i, h in enumerate(hours)]
    dn = [(X(i), Y(h["lo"])) for i, h in enumerate(hours)][::-1]
    o.append('<path d="%s L%s Z" fill="%s" fill-opacity="0.16"/>' % (smooth(up), " L".join("%.1f %.1f" % p for p in dn), C["band"]))
    o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.5" stroke-linecap="round"/>' % (smooth([(X(i), Y(h["T"])) for i, h in enumerate(hours)]), C["temp"]))
    for i, h in enumerate(hours):
        if local(h["t"]).hour % 3 == 0:
            o.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s" stroke="%s" stroke-width="2"/>' % (X(i), Y(h["T"]), C["temp"], C["panel"]))
            o.append('<text x="%.1f" y="%.1f" fill="%s" font-size="12.5" font-weight="600" text-anchor="middle">%s°</text>' % (X(i), Y(h["T"]) - 9, C["text"], num(h["T"])))
    # srážky
    pmax = max([h.get("P") or 0 for h in hours] + [1.5])
    o.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1"/>' % (pad, L["p1"], Wd - pad, L["p1"], C["grid"]))
    for i, h in enumerate(hours):
        p = h.get("P") or 0
        if p >= 0.05:
            hh = max(2.0, p / pmax * (L["p1"] - L["p0"] - 14))
            op = 0.35 + 0.65 * min(1.0, (h.get("Pp") or 0) / 100.0)
            w = max(2.0, pxh - 2)
            r = min(3.0, w / 2, hh)
            x0, y0 = X(i) - w / 2, L["p1"] - hh
            o.append('<path d="M%.1f %dV%.1fa%.1f %.1f 0 0 1 %.1f -%.1fh%.1fa%.1f %.1f 0 0 1 %.1f %.1fV%dZ" fill="%s" fill-opacity="%.2f"/>'
                     % (x0, L["p1"], y0 + r, r, r, r, r, w - 2 * r, r, r, r, r, L["p1"], C["rain"], op))
    for b in bl:
        if b["psum"] >= 0.3 and b["n"] >= 2:
            cx = pad + (b["i0"] + b["n"] / 2.0) * pxh
            top = max((hours[k].get("P") or 0) for k in range(b["i0"], b["i0"] + b["n"])) / pmax * (L["p1"] - L["p0"] - 14)
            o.append('<text x="%.1f" y="%.1f" fill="%s" font-size="11" text-anchor="middle">%s</text>' % (cx, L["p1"] - max(top, 2) - 4, C["text"], num(b["psum"], 1 if b["psum"] < 10 else 0)))
    # vítr
    gmax = max([h.get("G") or 0 for h in hours] + [8.0])
    YW = lambda v: L["w1"] - (v or 0) / gmax * (L["w1"] - L["w0"] - 14)
    o.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1"/>' % (pad, L["w1"], Wd - pad, L["w1"], C["grid"]))
    wp = [(X(i), YW(h.get("W"))) for i, h in enumerate(hours)]
    gp = [(X(i), YW(h.get("G"))) for i, h in enumerate(hours)]
    o.append('<path d="%s L%.1f %d L%.1f %d Z" fill="%s" fill-opacity="0.14"/>' % (smooth(wp), wp[-1][0], L["w1"], wp[0][0], L["w1"], C["wind"]))
    o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2"/>' % (smooth(wp), C["wind"]))
    o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2" stroke-dasharray="5 3"/>' % (smooth(gp), C["gust"]))
    for i, h in enumerate(hours):
        lt = local(h["t"])
        if lt.hour % 3 == 0 and h.get("G") is not None:
            o.append('<text x="%.1f" y="%.1f" fill="%s" font-size="11.5" font-weight="600" text-anchor="middle">%s</text>' % (X(i), YW(h["G"]) - 6, C["text"], num(h["G"])))
            if h.get("D") is not None:
                o.append(arrow(h["D"], X(i), L["arr"], 6.5))
            o.append('<text x="%.1f" y="%d" fill="%s" font-size="11" text-anchor="middle">%02d</text>' % (X(i), L["hr"], C["muted"], lt.hour))
    o.append("</svg>")
    return "".join(o), Wd, L["h"]


# --------------------------------------------------------------------------
# Stránka
# --------------------------------------------------------------------------

def day_symbol(hours, d):
    hs = [h for h in hours if local(h["t"]).date() == d and 7 <= local(h["t"]).hour <= 19] or [h for h in hours if local(h["t"]).date() == d]
    if not hs:
        return "cloudy"
    cl = [h["C"] for h in hs if h.get("C") is not None]
    return classify(sum(cl) / len(cl) if cl else None, sum(h.get("P") or 0 for h in hs), max(h.get("Pp") or 0 for h in hs),
                    False, sum(1 for h in hs if h.get("snow")) * 2 > len(hs), any(h.get("storm") for h in hs), hours=len(hs))


def site_html(key, s, first):
    hours = s.get("hourly") or []
    if not hours:
        return '<section class="site" id="s-%s"%s><p class="empty">Pro %s teď nejsou hodinová data. Zkus to po dalším výpočtu.</p></section>' % (key, "" if first else " hidden", esc(s["name"]))
    now = hours[0]
    nb = blocks3(hours[:3])[0]
    o = ['<section class="site" id="s-%s"%s>' % (key, "" if first else " hidden")]
    # teď
    st = s.get("station_last")
    stxt = ""
    if st:
        stxt = '<p class="station">Stanice v %s naměřila %s °C%s.</p>' % (local(st["time_utc"][:16] + "Z").strftime("%-H:%M"), num(st["temp"], 1),
                                                                      (", vítr %s m/s, náraz %s m/s" % (num(st["wind"], 1), num(st["gust"], 1))) if st.get("wind") is not None else "")
    o.append('<div class="now"><svg viewBox="0 0 28 30" width="84" height="90" aria-hidden="true">%s</svg>'
             '<div><p class="big">%s°</p><p class="desc">%s, vítr %s%s m/s, nárazy %s m/s</p>%s</div></div>'
             % (symbol(nb["sym"], 0, 0, 28), num(now["T"]), NAMES[nb["sym"]],
                ("od %s " % DIRS[int(((now["D"] + 22.5) % 360) // 45)]) if now.get("D") is not None else "", num(now.get("W")), num(now.get("G")), stxt))
    # dny
    daily = s.get("daily") or []
    if daily:
        lo = min(d["tmin"] for d in daily)
        hi = max(d["tmax"] for d in daily)
        sp = max(hi - lo, 1.0)
        o.append('<ol class="days">')
        for d in daily[:7]:
            dd = dt.date.fromisoformat(d["date"])
            sym = day_symbol(hours, dd)
            rain = ('<span class="rain">%s mm</span>' % num(d["precip_mm"], 0 if d["precip_mm"] >= 10 else 1)) if (d.get("precip_mm") or 0) >= 0.3 else '<span class="rain dry">bez srážek</span>'
            o.append('<li><span class="dn">%s %d.</span><svg viewBox="0 0 28 30" width="34" height="36" role="img" aria-label="%s">%s</svg>'
                     '<span class="tmin">%s°</span><span class="bar"><i style="left:%.0f%%;right:%.0f%%"></i></span><span class="tmax">%s°</span>'
                     '<span class="wr"><span class="gust">%s m/s</span>%s</span></li>'
                     % (DAYS[dd.weekday()], dd.day, NAMES[sym], symbol(sym, 0, 0, 28), num(d["tmin"]),
                        (d["tmin"] - lo) / sp * 100, (hi - d["tmax"]) / sp * 100, num(d["tmax"]), num(d["gust_max"]), rain))
        o.append("</ol>")
        o.append('<p class="cap">V řádku: den, nejnižší a nejvyšší teplota, vpravo nejsilnější náraz větru a pod ním srážky.</p>')
    # graf
    svg, w, h = meteogram(hours)
    o.append('<h2>Hodinu po hodině</h2>')
    o.append('<p class="legend"><span><i style="background:%s"></i>teplota (°C) s pásmem nejistoty</span><span><i style="background:%s"></i>srážky (mm)</span>'
             '<span><i style="background:%s"></i>vítr (m/s)</span><span><i class="dash" style="color:%s"></i>nárazy (m/s)</span></p>' % (C["temp"], C["rain"], C["wind"], C["gust"]))
    o.append('<div class="scroll" data-site="%s" tabindex="0"><div class="plot" style="width:%dpx">%s<div class="cur" hidden></div></div></div>' % (key, w, svg))
    o.append('<p class="tip" data-tip="%s">Táhni prstem po grafu a uvidíš přesné hodnoty.</p>' % key)
    # tabulka
    rows = []
    for b in blocks3(hours[:48]):
        hs = hours[b["i0"]:b["i0"] + b["n"]]
        lt = local(hs[0]["t"])
        rows.append("<tr><td>%s %02d h</td><td>%s</td><td>%s °C</td><td>%s / %s m/s</td><td>%s</td></tr>"
                    % (DAYS[lt.weekday()], lt.hour, NAMES[b["sym"]], num(sum(h["T"] for h in hs) / len(hs)),
                       num(sum((h.get("W") or 0) for h in hs) / len(hs)), num(max((h.get("G") or 0) for h in hs)),
                       (num(b["psum"], 1) + " mm") if b["psum"] >= 0.1 else "–"))
    o.append('<details><summary>Tabulka na 48 hodin</summary><table><thead><tr><th>Kdy</th><th>Počasí</th><th>Teplota</th><th>Vítr / nárazy</th><th>Srážky</th></tr></thead><tbody>%s</tbody></table></details>' % "".join(rows))
    o.append('<p class="src">Kalibrace: %s. Vítr platí pro volné prostranství, mezi stromy a u budov je slabší.</p>' % esc(s.get("calibration_source", "")))
    o.append("</section>")
    return "".join(o)


CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:%(bg)s;color:%(text)s;font:16px/1.4 %(font)s;-webkit-text-size-adjust:100%%;padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)}
main{max-width:1100px;margin:0 auto;padding:14px 14px 40px}
h1{font-size:15px;font-weight:600;margin:6px 2px 10px;color:%(muted)s}
h2{font-size:17px;margin:26px 2px 6px}
p{margin:0}
.tabs{display:flex;gap:6px;background:%(panel)s;padding:4px;border-radius:14px}
.tabs button{flex:1;font:inherit;font-weight:600;color:%(muted)s;background:none;border:0;border-radius:11px;padding:11px 8px;min-height:44px}
.tabs button[aria-selected=true]{background:%(bg)s;color:%(text)s}
.tabs button:focus-visible,.scroll:focus-visible,summary:focus-visible{outline:2px solid %(sun)s;outline-offset:2px}
.now{display:flex;align-items:center;gap:14px;margin:18px 2px 4px}
.big{font-size:76px;line-height:1;font-weight:700;letter-spacing:-2px}
.desc{font-size:17px;margin-top:4px}
.station{color:%(muted)s;font-size:14px;margin-top:4px}
.days{list-style:none;margin:18px 0 0;padding:4px 12px;background:%(panel)s;border-radius:16px}
.days li{display:grid;grid-template-columns:3.4em 38px 2.4em 1fr 2.4em 5.6em;align-items:center;gap:6px;padding:7px 0;border-top:1px solid %(grid)s;font-variant-numeric:tabular-nums}
.days li:first-child{border-top:0}
.dn{font-weight:600}
.tmin{color:%(muted)s;text-align:right}
.tmax{font-weight:600}
.bar{height:6px;border-radius:3px;background:%(grid)s;position:relative}
.bar i{position:absolute;top:0;bottom:0;border-radius:3px;background:%(temp)s}
.wr{display:flex;flex-direction:column;text-align:right;line-height:1.25}
.gust{font-size:15px}
.rain{font-size:13px;color:#8ab8f0}
.rain.dry,.cap,.tip,.src,footer{color:%(muted)s}
.cap,.tip,.src{font-size:13px;margin:8px 2px 0}
.legend{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:13px;color:%(muted)s;margin:0 2px 8px}
.legend i{display:inline-block;width:14px;height:4px;border-radius:2px;margin-right:6px;vertical-align:middle}
.legend i.dash{background:none;border-top:2px dashed currentColor;height:0}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:16px;background:%(panel)s}
.plot{position:relative}
.plot svg{display:block}
.cur{position:absolute;top:26px;bottom:8px;width:0;border-left:1px solid %(text)s;pointer-events:none}
.cur b{position:absolute;top:0;left:8px;white-space:nowrap;background:%(bg)s;border:1px solid %(grid)s;border-radius:10px;padding:6px 9px;font-size:13px;font-weight:500;line-height:1.45}
.cur.flip b{left:auto;right:8px}
details{margin-top:18px;background:%(panel)s;border-radius:16px;padding:4px 12px}
summary{padding:10px 0;font-weight:600;min-height:44px;cursor:pointer}
table{width:100%%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums;margin-bottom:10px}
th,td{text-align:left;padding:6px 6px 6px 0;border-top:1px solid %(grid)s;font-weight:400}
th{color:%(muted)s}
.empty{margin:30px 2px}
footer{font-size:12.5px;margin:28px 2px 0}
footer a{color:inherit}
@media(max-width:520px){.big{font-size:64px}}
"""

JS = """
(function(){
var t0=Date.now();
function fresh(){if(Date.now()-t0>15*60*1000)location.reload()}
document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')fresh()});
window.addEventListener('pageshow',function(e){if(e.persisted)fresh()});
var D=JSON.parse(document.getElementById('d').textContent),tabs=document.querySelectorAll('.tabs button');
function show(k){tabs.forEach(function(b){var on=b.dataset.k===k;b.setAttribute('aria-selected',on);document.getElementById('s-'+b.dataset.k).hidden=!on});try{localStorage.setItem('misto',k)}catch(e){}}
tabs.forEach(function(b){b.addEventListener('click',function(){show(b.dataset.k)})});
try{var m=localStorage.getItem('misto');if(m&&D.h[m])show(m)}catch(e){}
var dn=['ne','po','út','st','čt','pá','so'],dr=['S','SV','V','JV','J','JZ','Z','SZ'];
function f(v,n){if(v==null)return '–';var s=v.toFixed(n||0);if(parseFloat(s)===0)s=s.replace('-','');return s.replace('-','−').replace('.',',')}
document.querySelectorAll('.scroll').forEach(function(sc){
var H=D.h[sc.dataset.site],plot=sc.querySelector('.plot'),cur=sc.querySelector('.cur'),i=-1;
function at(x){var k=Math.max(0,Math.min(H.length-1,Math.floor((x-D.pad)/D.pxh)));if(k===i)return;i=k;var h=H[k],t=new Date(h.t);
var p=new Intl.DateTimeFormat('cs-CZ',{timeZone:'Europe/Prague',weekday:'short',hour:'numeric'}).format(t);
cur.hidden=false;cur.style.left=(D.pad+(k+.5)*D.pxh)+'px';cur.className='cur'+(D.pad+(k+.5)*D.pxh-sc.scrollLeft>sc.clientWidth-215?' flip':'');
cur.innerHTML='<b>'+p+' h<br>'+f(h.T,1)+' °C ('+f(h.lo)+' až '+f(h.hi)+')<br>vítr '+f(h.W,1)+', náraz '+f(h.G,1)+' m/s '+(h.D==null?'':dr[Math.floor(((h.D+22.5)%360)/45)])+'<br>srážky '+f(h.P,1)+' mm, '+f(h.Pp)+' % modelů</b>';
var tip=document.querySelector('[data-tip="'+sc.dataset.site+'"]');if(tip)tip.hidden=true}
plot.addEventListener('pointermove',function(e){at(e.clientX-plot.getBoundingClientRect().left)});
plot.addEventListener('pointerdown',function(e){at(e.clientX-plot.getBoundingClientRect().left)});
sc.addEventListener('keydown',function(e){if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();at(D.pad+(Math.max(0,i+(e.key==='ArrowRight'?1:-1))+.5)*D.pxh)}});
});
})();
"""


def build_html(result):
    sites = result.get("sites", {})
    issued = local(result["issued_utc"])
    tabs = "".join('<button role="tab" data-k="%s" aria-selected="%s">%s</button>' % (k, "true" if i == 0 else "false", esc(TABS.get(k, s["name"])))
                   for i, (k, s) in enumerate(sites.items()))
    body = "".join(site_html(k, s, i == 0) for i, (k, s) in enumerate(sites.items()))
    keep = ("t", "T", "lo", "hi", "W", "G", "D", "P", "Pp")
    data = {"pxh": 12, "pad": 14, "h": {k: [{a: h.get(a) for a in keep} for h in (s.get("hourly") or [])] for k, s in sites.items()}}
    css = CSS % dict(C, font=FONT)
    return ('<!doctype html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<meta name="robots" content="noindex"><meta name="theme-color" content="%s"><meta name="apple-mobile-web-app-capable" content="yes">'
            '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="Počasí Lipno">'
            '<link rel="apple-touch-icon" href="ikona.png"><title>Počasí Lipno</title><style>%s</style></head><body><main>'
            '<h1>Předpověď pro Lipno, vydáno %s %d. %d. v %s</h1><div class="tabs" role="tablist">%s</div>%s'
            '<footer>Směs %d modelů počasí kalibrovaná podle vlastních stanic a stanice ČHMÚ. Data: <a href="https://open-meteo.com/">Open-Meteo.com</a> (CC BY 4.0), '
            'měření <a href="https://opendata.chmi.cz/">ČHMÚ</a>.</footer></main>'
            '<script id="d" type="application/json">%s</script><script>%s</script></body></html>'
            % (C["bg"], css, DAYS_LONG[issued.weekday()], issued.day, issued.month, issued.strftime("%-H:%M"), tabs, body,
               max([len(s.get("models") or []) for s in sites.values()] or [0]), json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"), JS))


# --------------------------------------------------------------------------
# Obrázek a text pro Telegram (a hodinky)
# --------------------------------------------------------------------------

def card_svg(s, issued):
    hours = (s.get("hourly") or [])[:48]
    svg, w, h = meteogram(hours, pxh=16, pad=16)
    inner = svg[svg.index(">") + 1:-len("</svg>")]
    Wd, Hd = w + 32, h + 92
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="DejaVu Sans, sans-serif">'
            '<rect width="%d" height="%d" fill="%s"/><text x="18" y="38" fill="%s" font-size="24" font-weight="700">%s</text>'
            '<text x="18" y="64" fill="%s" font-size="15">vydáno %s %d. %d. v %s · teplota °C, srážky mm, vítr a nárazy (čárkovaně) m/s</text>'
            '<g transform="translate(16 78)">%s</g></svg>'
            % (Wd, Hd, Wd, Hd, Wd, Hd, C["bg"], C["text"], esc(s["name"]), C["muted"], DAYS[issued.weekday()], issued.day, issued.month,
               issued.strftime("%-H:%M"), inner))


def caption(s):
    out = [s["name"]]
    hours = s.get("hourly") or []
    for d in (s.get("daily") or [])[:3]:
        dd = dt.date.fromisoformat(d["date"])
        out.append("%s %d. %d.: %s, %s/%s °C, náraz %s m/s%s" % (DAYS[dd.weekday()], dd.day, dd.month, NAMES[day_symbol(hours, dd)], num(d["tmin"]), num(d["tmax"]), num(d["gust_max"]),
                                                                (", %s mm" % num(d["precip_mm"], 0)) if (d.get("precip_mm") or 0) >= 0.5 else ""))
    return "\n".join(out)


def icon_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180" viewBox="0 0 180 180"><rect width="180" height="180" fill="%s"/>'
            '<g transform="translate(20 22)">%s</g></svg>' % (C["bg"], symbol("partly-day", 0, 0, 140)))


def write_all(result, docs="docs"):
    """Zapíše stránku a obrázky. Vrací seznam (cesta k PNG, popisek) pro Telegram."""
    os.makedirs(docs, exist_ok=True)
    with open(os.path.join(docs, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_html(result))
    with open(os.path.join(docs, ".nojekyll"), "w") as f:
        f.write("")
    cards = []
    try:
        import cairosvg
    except Exception:
        return cards
    cairosvg.svg2png(bytestring=icon_svg().encode("utf-8"), write_to=os.path.join(docs, "ikona.png"))
    issued = local(result["issued_utc"])
    for k, s in result.get("sites", {}).items():
        if s.get("hourly"):
            path = os.path.join(docs, "karta-%s.png" % k)
            cairosvg.svg2png(bytestring=card_svg(s, issued).encode("utf-8"), write_to=path, scale=2)
            cards.append((path, caption(s)))
    return cards


if __name__ == "__main__":
    res = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "out/predpoved.json", encoding="utf-8"))
    print(write_all(res, sys.argv[2] if len(sys.argv) > 2 else "docs"))
