#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Převod exportu z ProWeatherLive (CSV, záznamy po 5 minutách) na hodinová data pro pocasi.py.

Použití:
    python pwl_export.py EXPORT.csv data/pwl_frymburk.csv

Výstup: CSV se sloupci time (UTC, konec hodiny), T (°C), W (m/s, hodinový průměr),
G (m/s, nejvyšší náraz v hodině), P (mm za hodinu), D (směr větru ve stupních).

Co převod vyřazuje:
  * záznamy, kdy konzole neměla spojení s venkovním čidlem (vlhkost 0 %),
  * "zamrzlé" záznamy, kdy se teplota, vlhkost, vítr, směr i světlo přestaly měnit
    (konzole při výpadku spojení opakuje poslední hodnotu).
Zaseklý anemometr a ucpaný srážkoměr tady neřeší, to hlídá pocasi.py porovnáním se stanicí ČHMÚ.
"""
import sys

import numpy as np
import pandas as pd

COLS = {
    "Outdoor temperature": "T", "Outdoor humidity": "H", "Wind speed": "WS", "10 min AVG": "W10",
    "Wind gust": "WG", "Wind Direction": "D", "Daily rainfall": "RD", "Light intensity": "LUX",
}
ZONES = {"CET": 1, "CEST": 2}


def read_export(path):
    df = pd.read_csv(path, skiprows=[1], na_values=["---", "--", ""], encoding="utf-8-sig", low_memory=False)
    miss = [c for c in ("Time & Timezone", "Time", "Outdoor temperature") if c not in df.columns]
    if miss:
        raise SystemExit("V souboru chybí sloupce: %s" % ", ".join(miss))
    zone = df["Time & Timezone"].astype(str).str.rsplit(" ", n=1).str[-1]
    off = zone.map(ZONES)
    if off.isna().any():
        raise SystemExit("Neznámé časové pásmo v exportu: %s" % sorted(set(zone[off.isna()]))[:5])
    local = pd.to_datetime(df["Time"])
    out = pd.DataFrame(index=local - pd.to_timedelta(off, unit="h"))
    out["local_day"] = local.dt.normalize().to_numpy()
    for src, dst in COLS.items():
        out[dst] = pd.to_numeric(df[src], errors="coerce").to_numpy() if src in df.columns else np.nan
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out


def flag_offline(df):
    """True tam, kde venkovní čidlo neposílalo data."""
    off = (df["H"] == 0)
    keys = ["T", "H", "D", "WS", "WG", "LUX"]
    same = pd.Series(True, index=df.index)
    for k in keys:
        same &= (df[k].diff() == 0) | (df[k].isna() & df[k].shift().isna())
    step = df.index.to_series().diff() <= pd.Timedelta(minutes=20)
    same &= step
    run = (~same).cumsum()
    n = same.groupby(run).transform("sum")
    day = df["LUX"] > 0
    frozen = same & ((n >= 36) | ((n >= 12) & day))
    return off | frozen


def to_hourly(df):
    bad = flag_offline(df)
    d = df.copy()
    for k in ("T", "H", "WS", "W10", "WG", "D", "RD"):
        d.loc[bad, k] = np.nan
    d.loc[(d["T"] < -40) | (d["T"] > 45), "T"] = np.nan
    for k in ("WS", "W10", "WG"):
        d.loc[(d[k] < 0) | (d[k] > 60), k] = np.nan

    # srážky z denního čítače (nuluje se o místní půlnoci)
    rd = d["RD"]
    step = d.index.to_series().diff()
    inc = rd.diff()
    newday = d["local_day"] != d["local_day"].shift()
    p = inc.where(~newday, rd)                 # první záznam dne: napršelo od půlnoci
    p = p.where(~((inc < 0) & ~newday), rd)    # čítač se vynuloval během dne (restart konzole)
    p = p.where(step <= pd.Timedelta(minutes=65))
    p[(p < 0) | (p > 15)] = np.nan
    d["P5"] = p

    idx = pd.date_range(d.index.min().ceil("h"), d.index.max().floor("h"), freq="h")
    out = pd.DataFrame(index=idx)
    t = d["T"]
    out["T"] = t.reindex(idx)
    for back in (5, 10):
        prev = t.reindex(idx - pd.Timedelta(minutes=back))
        prev.index = idx
        out["T"] = out["T"].fillna(prev)
    g = d.resample("h", label="right", closed="right")
    w = d["W10"].where(d["W10"].notna(), d["WS"])
    gw = w.resample("h", label="right", closed="right")
    out["W"] = gw.mean().where(gw.count() >= 6).reindex(idx)
    out["G"] = g["WG"].max().where(g["WG"].count() >= 6).reindex(idx)
    out["P"] = g["P5"].sum().where(g["P5"].count() >= 10).reindex(idx)
    rad = np.deg2rad(d["D"])
    wt = d["WS"].where(d["D"].notna())
    sx = (np.sin(rad) * wt).resample("h", label="right", closed="right").sum()
    sy = (np.cos(rad) * wt).resample("h", label="right", closed="right").sum()
    sw = wt.resample("h", label="right", closed="right").sum()
    ang = (np.rad2deg(np.arctan2(sx, sy)) + 360) % 360
    out["D"] = ang.where(sw > 0).reindex(idx).round(0)
    out = out.dropna(how="all")
    return out, bad


def periods(mask, min_len=36):
    res = []
    if not mask.any():
        return res
    run = (mask != mask.shift()).cumsum()
    for _, x in mask[mask].groupby(run[mask]):
        if len(x) >= min_len:
            res.append((x.index[0], x.index[-1], len(x)))
    return res


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    src, dst = argv[1], argv[2]
    raw = read_export(src)
    hourly, bad = to_hourly(raw)
    hourly.to_csv(dst, float_format="%.2f", index_label="time")
    print("záznamů: %d (%s až %s UTC)" % (len(raw), raw.index.min(), raw.index.max()))
    print("vyřazeno záznamů bez spojení s čidlem: %d (%.1f %%)" % (int(bad.sum()), 100.0 * bad.mean()))
    for a, b, n in periods(bad):
        print("  %s až %s (%.0f h)" % (a.strftime("%Y-%m-%d %H:%M"), b.strftime("%Y-%m-%d %H:%M"), n / 12.0))
    print("hodin: %d, platných: %s" % (len(hourly), ", ".join("%s %d" % (k, int(hourly[k].notna().sum())) for k in hourly.columns)))
    print("uloženo: %s" % dst)


if __name__ == "__main__":
    main(sys.argv)
