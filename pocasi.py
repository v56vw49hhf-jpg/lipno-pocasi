#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lokální předpověď pro Lipno (Černá v Pošumaví, Frymburk).

Dva režimy:
  verify    zpětné vyhodnocení: jak se které modely trefovaly proti stanici
            ČHMÚ Černá v Pošumaví a co přinese kalibrovaná směs
  forecast  aktuální předpověď: kalibrace podle posledních 30 dní + směs modelů

Zdroje dat:
  předpovědi   Open-Meteo (api.open-meteo.com, previous-runs-api.open-meteo.com)
  měření       ČHMÚ, opendata.chmi.cz (desetiminutová data)
"""
import argparse
import datetime as dt
import glob
import json
import math
import os
import random
import sys
import time

import numpy as np
import pandas as pd
import requests

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Prague")
except Exception:  # pragma: no cover
    TZ = dt.timezone(dt.timedelta(hours=1))

# --------------------------------------------------------------------------
# Nastavení
# --------------------------------------------------------------------------

SITES = {
    "cerna": {
        "name": "Černá v Pošumaví – lanový park",
        "lat": 48.7356, "lon": 14.1073, "elev": 740,
        "chmi": "0-203-0-11547",      # stanice ČHMÚ Černá v Pošumaví
        "calib": "cerna",
        "wu": "IERNVP8",               # vlastní stanice na Weather Underground (terasa u lanového parku)
        "own": ("T",),                 # terasa u lesa: v noci tepleji a přes den chladněji než stanice ČHMÚ 500 m odtud
    },
    "frymburk": {
        "name": "Frymburk – wake",
        "lat": 48.660, "lon": 14.171, "elev": 735,
        "chmi": None,
        "calib": "cerna",              # bez čerstvých dat z vlastní stanice se kalibruje podle Černé
        "wu": "IFRYMB21",              # Wake Frymburk na Weather Underground (přeposílá ProWeatherLive)
        "wu_from": "2026-11-17 22:00", # první platná hodina (UTC); předtím pod tímto ID krátce chodila data lanového parku
        "own": ("T",),                 # co se smí kalibrovat podle vlastní stanice (vítr ne: čidlo je v závětří)
    },
}

# (název, [identifikátory Open-Meteo v pořadí priority], patří do směsi?)
MODELS = [
    ("ALADIN-CZ 1 km", ["chmi_aladin_cz_1km"], True),
    ("ALADIN-CE 2,3 km", ["chmi_aladin_central_europe_2km"], True),
    ("C-LAEF 1 km", ["geosphere_claef_austria"], True),
    ("ICON-D2 2 km", ["dwd_icon_d2_native", "icon_d2"], True),
    ("ICON-CH1 1 km", ["meteoswiss_icon_ch1"], True),
    ("ICON-CH2 2 km", ["meteoswiss_icon_ch2"], True),
    ("HARMONIE-DMI 2 km", ["dmi_harmonie_arome_europe"], True),
    ("AROME-FR 1,3 km", ["meteofrance_arome_france_hd", "meteofrance_arome_france"], True),
    ("HARMONIE-KNMI 5,5 km", ["knmi_harmonie_arome_europe"], True),
    ("ICON-EU 7 km", ["dwd_icon_eu_native", "icon_eu"], True),
    ("ECMWF IFS 9 km", ["ecmwf_ifs"], True),
    ("ECMWF IFS 0,25°", ["ecmwf_ifs025"], False),
    ("UKMO 10 km", ["ukmo_global_deterministic_10km"], True),
    ("ARPEGE 11 km", ["meteofrance_arpege_europe"], True),
    ("ICON 13 km", ["dwd_icon_global_native", "icon_global"], True),
    ("GFS 13 km", ["ncep_gfs_global", "gfs_global"], True),
    ("GEM 15 km", ["gem_global"], True),
    ("ECMWF AIFS (AI)", ["ecmwf_aifs025_single"], True),
    ("Open-Meteo best match", ["best_match"], False),
]
BLEND = [m[0] for m in MODELS if m[2]]

# veličiny: zkratka -> (název v Open-Meteo, způsob korekce, jednotka, český název)
VARS = {
    "T": ("temperature_2m", "add", "°C", "Teplota"),
    "W": ("wind_speed_10m", "mul", "m/s", "Vítr (průměr)"),
    "G": ("wind_gusts_10m", "mul", "m/s", "Nárazy větru"),
    "P": ("precipitation", None, "mm", "Srážky"),
}
LEADS = [0, 1, 2, 3, 5]          # o kolik dní dřív byla předpověď vydaná
EVAL_LEADS = [1, 2, 3, 5]
WINDOW = 30                      # dní pro klouzavou kalibraci (výchozí)
OWN_MAX_AGE = 14                 # jak stará smí být data z vlastní stanice, aby se podle nich kalibrovalo (dny)
MINP = 7
SHRINK = 0.8                     # opravu bereme jen z 80 %, zbytek je šum
# zkoušené způsoby kalibrace: (režim, okno ve dnech)
VARIANTS = {
    "add": [("none", 30), ("mean", 15), ("mean", 30), ("mean", 60), ("hod3", 30), ("hod3", 60)],
    "mul": [("none", 30), ("ratio", 15), ("ratio", 30), ("ratio", 60)],
}
DEFAULT_METHOD = {"T": ("mean", 30), "W": ("ratio", 30), "G": ("ratio", 30)}
VARIANT_NAMES = {"none": "bez opravy, jen váhy podle úspěšnosti", "mean": "oprava průměrné odchylky",
                 "hod3": "oprava odchylky podle denní doby", "ratio": "přeškálování"}

OM_FORECAST = "https://api.open-meteo.com/v1/forecast"
OM_PREVIOUS = "https://previous-runs-api.open-meteo.com/v1/forecast"
CHMI = "https://opendata.chmi.cz/meteorology/climate"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "lipno-pocasi/0.1 (GitHub Actions; osobni projekt)"
STATE = {"om_calls": 0, "om_cost": 0.0, "om_remaining": None, "errors": []}


def log(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

class ApiError(Exception):
    pass


def http_json(url, params=None, tries=6, timeout=90, allow404=False):
    last = None
    for attempt in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=timeout)
        except requests.RequestException as e:
            last = "síť: %s" % e
            time.sleep(3 + 3 * attempt + random.random())
            continue
        if r.status_code == 200:
            cost = r.headers.get("X-RateLimit-Cost")
            rem = r.headers.get("X-RateLimit-Remaining")
            if cost is not None:
                try:
                    STATE["om_cost"] += float(cost)
                except ValueError:
                    pass
            if rem is not None:
                STATE["om_remaining"] = rem
            if cost is not None:
                try:
                    time.sleep(min(float(cost) * 0.12, 8.0))   # limit 600 vážených dotazů za minutu
                except ValueError:
                    pass
            try:
                return r.json()
            except ValueError:
                last = "odpověď není JSON"
                time.sleep(2 + attempt)
                continue
        if r.status_code == 404 and allow404:
            return None
        if r.status_code == 429:
            try:
                wait = float(r.headers.get("Retry-After", "20"))
            except ValueError:
                wait = 20.0
            try:
                reason = r.json().get("reason", "")
            except ValueError:
                reason = r.text[:120]
            last = "429 %s" % reason
            if wait > 150:
                # hodinový nebo denní limit: nemá smysl čekat v rámci běhu
                raise ApiError("limit API vyčerpán (čekání %d s): %s" % (wait, reason))
            log("    429, čekám %.0f s (%s)" % (wait, reason))
            time.sleep(wait + 1 + 2 * random.random())
            continue
        if r.status_code in (500, 502, 503, 504):
            last = "HTTP %d" % r.status_code
            time.sleep(5 + 5 * attempt + random.random())
            continue
        try:
            reason = r.json().get("reason", r.text[:200])
        except ValueError:
            reason = r.text[:200]
        raise ApiError("HTTP %d: %s" % (r.status_code, reason))
    raise ApiError("opakované selhání (%s)" % last)


def om_base(url):
    key = os.environ.get("OPENMETEO_API_KEY", "").strip()
    if key:
        return url.replace("https://", "https://customer-"), {"apikey": key}
    return url, {}


def om_fetch(url, site, model_id, hourly, **extra):
    """Jeden model, jedno místo. Vrací DataFrame (index = čas UTC bez zóny)."""
    base, auth = om_base(url)
    params = {
        "latitude": site["lat"], "longitude": site["lon"], "elevation": site["elev"],
        "hourly": ",".join(hourly), "models": model_id,
        "wind_speed_unit": "ms", "timezone": "GMT",
    }
    params.update(extra)
    params.update(auth)
    STATE["om_calls"] += 1
    j = http_json(base, params)
    if isinstance(j, list):
        j = j[0]
    h = j.get("hourly") or {}
    if "time" not in h:
        raise ApiError("odpověď bez časové osy")
    idx = pd.to_datetime(h["time"])
    data = {}
    suffix = "_" + model_id
    for k, v in h.items():
        if k == "time":
            continue
        name = k[: -len(suffix)] if k.endswith(suffix) else k
        data[name] = pd.to_numeric(pd.Series(v, dtype="object"), errors="coerce").to_numpy(dtype=float)
    return pd.DataFrame(data, index=idx)


def hourly_names(var_keys, leads):
    out = []
    for vk in var_keys:
        base = VARS[vk][0]
        for L in leads:
            out.append(base if L == 0 else "%s_previous_day%d" % (base, L))
    return out


def chunks(start, end, days=60):
    d = start
    while d <= end:
        e = min(end, d + dt.timedelta(days=days - 1))
        yield d, e
        d = e + dt.timedelta(days=1)


def fetch_previous_runs(site, start, end, var_keys=("T", "W", "G", "P"), leads=LEADS):
    """Vrací slovník fc[(veličina, předstih)] = DataFrame čas × model."""
    names = hourly_names(var_keys, leads)
    per_model = {}
    for label, ids, _ in MODELS:
        merged = None
        label_errors = []
        for mid in ids:
            parts = []
            failed = None
            for a, b in chunks(start, end):
                try:
                    df = om_fetch(OM_PREVIOUS, site, mid, names,
                                  start_date=a.isoformat(), end_date=b.isoformat())
                    parts.append(df)
                except ApiError as e:
                    failed = str(e)
                    break
                time.sleep(0.4)
            if failed and not parts:
                log("  %-24s %-34s vynecháno: %s" % (label, mid, failed))
                label_errors.append("%s (%s): %s" % (label, mid, failed))
                if "limit API" in failed:
                    break
                continue
            df = pd.concat(parts)
            df = df[~df.index.duplicated(keep="last")].sort_index()
            n_ok = int(df.notna().any(axis=1).sum())
            log("  %-24s %-34s hodin s daty: %d%s" % (label, mid, n_ok, " (neúplné: %s)" % failed if failed else ""))
            merged = df if merged is None else merged.combine_first(df)
        if merged is not None and merged.notna().any().any():
            per_model[label] = merged
        else:
            STATE["errors"].extend(label_errors or ["%s: bez dat" % label])
    fc = {}
    for vk in var_keys:
        base = VARS[vk][0]
        for L in leads:
            col = base if L == 0 else "%s_previous_day%d" % (base, L)
            cols = {m: d[col] for m, d in per_model.items() if col in d.columns and d[col].notna().any()}
            fc[(vk, L)] = pd.DataFrame(cols).sort_index() if cols else pd.DataFrame()
    return fc


# --------------------------------------------------------------------------
# Měření ČHMÚ
# --------------------------------------------------------------------------

WANT = ("T", "F", "Fmax", "D", "SRA10M")


def _find_table(j):
    """Najde v JSON slovník s klíči header + values."""
    if isinstance(j, dict):
        if "header" in j and "values" in j:
            return j
        for v in j.values():
            t = _find_table(v)
            if t is not None:
                return t
    elif isinstance(j, list):
        for v in j[:3]:
            if isinstance(v, (dict, list)):
                t = _find_table(v)
                if t is not None:
                    return t
    return None


def chmi_parse(j):
    t = _find_table(j)
    if t is None:
        return None
    hdr = [h.strip() for h in t["header"].split(",")]
    iE, iT, iV = hdr.index("ELEMENT"), hdr.index("DT"), hdr.index("VAL")
    rows = [(r[iT], r[iE], r[iV]) for r in t["values"] if r[iE] in WANT]
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["t", "e", "v"])
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df["t"] = pd.to_datetime(df["t"], utc=True).dt.tz_localize(None)
    return df.pivot_table(index="t", columns="e", values="v", aggfunc="last")


def chmi_get(path):
    try:
        j = http_json(CHMI + path, tries=3, timeout=120, allow404=True)
    except ApiError as e:
        log("  ČHMÚ %s: %s" % (path, e))
        return None
    if j is None:
        return None
    try:
        return chmi_parse(j)
    except Exception as e:  # neočekávaný formát
        log("  ČHMÚ %s: nečitelný formát (%s)" % (path, e))
        return None


def fetch_chmi_10min(wsi, start, end):
    """Desetiminutová data stanice za období [start, end] (data UTC)."""
    today = dt.datetime.now(dt.timezone.utc).date()
    frames = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        ym = "%04d%02d" % (y, m)
        df = None
        for path in ("/historical/data/10min/%04d/10m-%s-%s.json" % (y, wsi, ym),
                     "/recent/data/10min/%02d/10m-%s-%s.json" % (m, wsi, ym)):
            df = chmi_get(path)
            if df is not None:
                log("  ČHMÚ %s: %d záznamů (%s)" % (ym, len(df), path.split("/")[1]))
                break
        if df is None:
            # měsíc ještě není uzavřený: denní soubory
            got = 0
            d = dt.date(y, m, 1)
            while d.month == m and d <= min(end, today):
                if d >= start:
                    ymd = d.strftime("%Y%m%d")
                    dd = chmi_get("/recent/data/10min/10m-%s-%s.json" % (wsi, ymd))
                    if dd is None:
                        dd = chmi_get("/now/data/10m-%s-%s.json" % (wsi, ymd))
                    if dd is not None:
                        frames.append(dd)
                        got += 1
                d += dt.timedelta(days=1)
            log("  ČHMÚ %s: denní soubory, načteno dní: %d" % (ym, got))
        else:
            frames.append(df)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out


def obs_hourly(df10):
    """Hodinové hodnoty srovnatelné s modely (čas = konec hodiny, UTC)."""
    if df10.empty:
        return pd.DataFrame()
    df10 = df10.sort_index()
    idx = pd.date_range(df10.index.min().ceil("h"), df10.index.max().floor("h"), freq="h")
    out = pd.DataFrame(index=idx)
    if "T" in df10:
        t = df10["T"]
        out["T"] = t.reindex(idx)
        # chybějící celá hodina: vezmi hodnotu o 10 minut dřív
        prev = t.reindex(idx - pd.Timedelta(minutes=10))
        prev.index = idx
        out["T"] = out["T"].fillna(prev)
    g = df10.resample("h", label="right", closed="right")
    if "F" in df10:
        out["W"] = g["F"].mean().where(g["F"].count() >= 4).reindex(idx)
    if "Fmax" in df10:
        out["G"] = g["Fmax"].max().where(g["Fmax"].count() >= 4).reindex(idx)
    if "SRA10M" in df10:
        out["P"] = g["SRA10M"].sum().where(g["SRA10M"].count() >= 5).reindex(idx)
    if "D" in df10:
        out["D"] = df10["D"].reindex(idx)
    return out


# --------------------------------------------------------------------------
# Vlastní stanice (Weather Underground + export z ProWeatherLive)
# --------------------------------------------------------------------------

WU = "https://api.weather.com/v2/pws"
STATION_DIR = os.path.join("data", "stanice")
STATION_COLS = ["T", "W", "G", "P", "D"]


def wu_get(path, **params):
    key = os.environ.get("WU_API_KEY", "").strip()
    if not key:
        return None
    params.update({"format": "json", "units": "m", "numericPrecision": "decimal", "apiKey": key})
    for attempt in range(4):
        try:
            r = SESSION.get(WU + path, params=params, timeout=60)
        except requests.RequestException:
            time.sleep(5 + 5 * attempt)
            continue
        if r.status_code == 200:
            time.sleep(2.1)            # limit 30 dotazů za minutu
            try:
                return r.json().get("observations") or []
            except ValueError:
                return []
        if r.status_code == 204:
            time.sleep(2.1)
            return []
        if r.status_code in (401, 403):
            raise ApiError("Weather Underground odmítl klíč (HTTP %d)" % r.status_code)
        time.sleep(65 if r.status_code == 429 else 5 + 5 * attempt)
    return None


def wu_to_hourly(obs_list):
    rows = []
    for o in obs_list or []:
        m, k = o.get("metric"), 1.0 / 3.6          # km/h -> m/s
        if m is None:
            m, k = o.get("metric_si"), 1.0
        if not m or not o.get("obsTimeUtc"):
            continue
        ws, wg = m.get("windspeedAvg"), m.get("windgustHigh")
        rows.append({"t": o["obsTimeUtc"], "loc": str(o.get("obsTimeLocal", ""))[:10], "tavg": m.get("tempAvg"),
                     "W": None if ws is None else ws * k, "G": None if wg is None else wg * k,
                     "ptot": m.get("precipTotal"), "D": o.get("winddirAvg")})
    if not rows:
        return pd.DataFrame(columns=STATION_COLS)
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["t"], utc=True).dt.tz_localize(None).dt.ceil("h")
    df = df.drop_duplicates("t", keep="last").sort_values("t")
    for c in ("tavg", "W", "G", "ptot", "D"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    d = df.groupby("loc")["ptot"].diff()
    # první hodina dne: úhrn od půlnoci; pokles během dne = konzole se restartovala, počítá se od nuly
    df["P"] = d.where(d.notna() & (d >= 0), df["ptot"]).clip(lower=0)
    df = df.set_index("t")
    # Weather Underground dává hodinový průměr teploty, modely i ČHMÚ hodnotu v celou hodinu.
    # Hodnota v celou hodinu ~ průměr dvou sousedních hodinových průměrů (jinak ráno a večer sedí o 0,6 °C vedle).
    t = df["tavg"]
    nxt = t.reindex(t.index + pd.Timedelta(hours=1))
    nxt.index = t.index
    prv = t.reindex(t.index - pd.Timedelta(hours=1))
    prv.index = t.index
    df["T"] = (0.5 * (t + nxt)).fillna(t + 0.5 * (t - prv)).fillna(t)
    return df[STATION_COLS]


def station_load(key):
    paths = []
    seed = os.path.join("data", "pwl_%s.csv" % key)
    if os.path.exists(seed):
        paths.append(seed)
    paths += sorted(glob.glob(os.path.join(STATION_DIR, key, "*.csv")))
    frames = []
    for p in paths:
        try:
            d = pd.read_csv(p, parse_dates=["time"], index_col="time")
            frames.append(d.reindex(columns=STATION_COLS))
        except Exception as e:
            log("  %s: nejde načíst (%s)" % (p, e))
    if not frames:
        return pd.DataFrame(columns=STATION_COLS)
    df = pd.concat(frames)
    return df[~df.index.duplicated(keep="last")].sort_index()


def station_update(key, start=None, end=None, backfill=False):
    """Hodinová data vlastní stanice: uložená v repozitáři + doplnění z Weather Underground."""
    df = station_load(key)
    sid = SITES[key].get("wu")
    wu_from = pd.Timestamp(SITES[key]["wu_from"]) if SITES[key].get("wu_from") else None
    if not sid or not os.environ.get("WU_API_KEY", "").strip():
        log("  %s: uložených hodin %d, Weather Underground se nedotazuji (%s)"
            % (key, len(df), "chybí ID stanice" if not sid else "chybí WU_API_KEY"))
        return df
    new = []
    try:
        new.append(wu_to_hourly(wu_get("/observations/hourly/7day", stationId=sid)))
        if backfill and start and end:
            have = set()
            if len(df):
                cnt = pd.Series(1, index=df.index[df["T"].notna()]).groupby(lambda t: t.date()).sum()
                have = set(cnt[cnt >= 20].index)
            # dny starší než 10 dní stačí zkontrolovat jednou (historie na WU se už nemění)
            seen_path = os.path.join(STATION_DIR, key, "zkontrolovane_dny.txt")
            seen = set(open(seen_path, encoding="utf-8").read().split()) if os.path.exists(seen_path) else set()
            old = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=10)
            d, n, fresh = start, 0, []
            if wu_from is not None:
                d = max(d, wu_from.date())
            while d <= end and n < 450:
                if d not in have and d.isoformat() not in seen:
                    new.append(wu_to_hourly(wu_get("/history/hourly", stationId=sid, date=d.strftime("%Y%m%d"))))
                    n += 1
                    if d < old:
                        fresh.append(d.isoformat())
                d += dt.timedelta(days=1)
            if fresh:
                os.makedirs(os.path.join(STATION_DIR, key), exist_ok=True)
                with open(seen_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(sorted(seen | set(fresh))) + "\n")
            log("  %s: doplněno dní z Weather Underground: %d" % (key, n))
    except ApiError as e:
        log("  %s: %s" % (key, e))
        STATE["errors"].append("vlastní stanice %s: %s" % (key, e))
    new = [x for x in new if x is not None and len(x)]
    if not new:
        return df
    add = pd.concat(new)
    add = add[add.index <= pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))]   # bez rozdělané hodiny
    if wu_from is not None:
        add = add[add.index >= wu_from]
    if not len(add):
        return df
    merged = pd.concat([df, add]) if len(df) else add
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    merged = merged.reindex(columns=STATION_COLS).apply(pd.to_numeric, errors="coerce")
    os.makedirs(os.path.join(STATION_DIR, key), exist_ok=True)
    changed = set(zip(add.index.year, add.index.month))
    for (y, m) in sorted(changed):
        part = merged[(merged.index.year == y) & (merged.index.month == m)]
        part.to_csv(os.path.join(STATION_DIR, key, "%04d-%02d.csv" % (y, m)), float_format="%.2f", index_label="time")
    log("  %s: hodin celkem %d (nových/aktualizovaných %d)" % (key, len(merged), len(add)))
    return merged


def sun_elev(idx, lat, lon):
    """Výška slunce nad obzorem ve stupních (přibližně; stačí na rozlišení dne a noci). idx v UTC."""
    hours = idx.hour.to_numpy() + idx.minute.to_numpy() / 60.0
    g = 2 * np.pi * (idx.dayofyear.to_numpy() - 1 + hours / 24.0) / 365.25
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    ha = np.deg2rad(15.0 * (hours + (eqt + 4.0 * lon) / 60.0 - 12.0))
    la = np.deg2rad(lat)
    return np.rad2deg(np.arcsin(np.sin(la) * np.sin(decl) + np.cos(la) * np.cos(decl) * np.cos(ha)))


NIGHT_ELEV = -3.0     # slunce aspoň 3° pod obzorem: čidlo už není ohřáté sluncem
DAY_ELEV = 10.0
NIGHT_MINP = 3        # v létě je noc krátká, na noční kalibraci stačí méně hodin


def _runs(mask):
    """Souvislé úseky True v hodinové řadě -> [(začátek, konec, počet hodin)]."""
    m = mask.fillna(False).to_numpy(dtype=bool)
    if not m.any():
        return []
    edges = np.flatnonzero(np.diff(np.concatenate(([0], m.astype(np.int8), [0]))))
    return [(mask.index[i], mask.index[j - 1], int(j - i)) for i, j in zip(edges[::2], edges[1::2])]


def _fmt_runs(runs, top=4, min_hours=12):
    runs = [r for r in runs if r[2] >= min_hours]
    runs = sorted(sorted(runs, key=lambda r: -r[2])[:top], key=lambda r: r[0])
    out = []
    for a, b, _ in runs:
        out.append(a.strftime("%-d. %-m. %Y") if a.date() == b.date()
                   else "%s – %s" % (a.strftime("%-d. %-m."), b.strftime("%-d. %-m. %Y")))
    return ", ".join(out)


def station_qc(st, ref=None):
    """
    Vyřadí zjevně vadná hodinová data vlastní stanice. ref = hodinová data stanice ČHMÚ (když jsou).
    Vrací (očištěná data, seznam poznámek pro zprávu).
    """
    notes = []
    if st is None or not len(st):
        return st, notes
    full = pd.date_range(st.index.min(), st.index.max(), freq="h")
    s = st.reindex(full).astype(float).copy()

    # 1) čidlo neposílá data: konzole opakuje poslední hodnoty
    same = (s["T"].diff() == 0) & (s["W"].diff().fillna(0) == 0) & (s["G"].diff().fillna(0) == 0)
    n = same.groupby((~same).cumsum()).transform("sum")
    frozen = same & (n >= 6)
    if frozen.any():
        s.loc[frozen, STATION_COLS] = np.nan
        notes.append("čidlo neposílalo data (opakovaly se stejné hodnoty): %d h%s"
                     % (int(frozen.sum()), (", hlavně " + _fmt_runs(_runs(frozen))) if _fmt_runs(_runs(frozen)) else ""))

    # 2) anemometr stojí: během 24 hodin je aspoň 90 % hodin úplně bez větru
    w = s["W"]
    valid = w.notna()
    zero = (w <= 0.05)
    zc = zero.astype(float).rolling(25, center=True, min_periods=1).sum()
    vc = valid.astype(float).rolling(25, center=True, min_periods=1).sum()
    stuck = (vc >= 18) & (zc >= 0.9 * vc)
    stuck = (stuck | (zero & stuck.groupby((zero != zero.shift()).cumsum()).transform("any"))) & valid

    # 3) stanice ukazuje nulu aspoň 6 hodin v kuse, i když na stanici ČHMÚ fouká
    if ref is not None and "W" in ref:
        rw = ref["W"].reindex(full)
        grp = (zero != zero.shift()).cumsum()
        g = pd.DataFrame({"rw": rw[zero], "grp": grp[zero]})
        if len(g):
            a = g.groupby("grp")["rw"].agg(["size", "count", "mean", "min"])
            bad = a[(a["size"] >= 6) & (a["count"] >= 0.8 * a["size"]) & (a["mean"] >= 3.0) & (a["min"] >= 2.0)].index
            stuck = stuck | (zero & grp.isin(bad))
    if stuck.any():
        s.loc[stuck, ["W", "G", "D"]] = np.nan
        txt = _fmt_runs(_runs(stuck), min_hours=24)
        notes.append("vítr vyřazen (anemometr stál nebo namrzl): %d h%s" % (int(stuck.sum()), (", hlavně " + txt) if txt else ""))

    # 4) srážkoměr: měsíce, kdy stanice naměřila méně než pětinu toho co ČHMÚ
    if ref is not None and "P" in ref:
        both = pd.DataFrame({"s": s["P"], "c": ref["P"].reindex(full)}).dropna()
        if len(both):
            g = both.groupby(both.index.to_period("M")).agg(s=("s", "sum"), c=("c", "sum"), n=("s", "size"))
            badm = g[(g["n"] >= 200) & (g["c"] >= 20) & (g["s"] < 0.2 * g["c"])].index
            if len(badm):
                s.loc[s.index.to_period("M").isin(badm), "P"] = np.nan
                notes.append("srážky vyřazeny za měsíce %s (stanice naměřila méně než pětinu úhrnu ČHMÚ: ucpaný srážkoměr, v zimě sníh)"
                             % ", ".join("%d/%d" % (x.month, x.year) for x in badm))
    return s.dropna(how="all"), notes


def station_vs_chmi(name, st, ref, raw=None, notes=None):
    """Porovnání vlastní stanice se stanicí ČHMÚ: vítr podle směru, teplota podle denní doby, srážky po měsících."""
    md = ["## %s: vlastní stanice proti stanici ČHMÚ v Černé" % name, ""]
    if notes:
        md += ["Kontrola dat stanice:", ""] + ["- " + x for x in notes] + [""]
    j = st.join(ref, how="inner", lsuffix="_s", rsuffix="_c")
    if len(j) < 24 * 30:
        return md + ["Málo společných hodin.", ""]
    need = {"D_c", "W_s", "W_c", "G_s", "G_c"}
    if need.issubset(j.columns):
        jj = j[(j["W_c"] >= 2.0) & j["D_c"].notna() & j["W_s"].notna()]
        sec = (((jj["D_c"] + 22.5) % 360) // 45).astype(int)
        rows = []
        for k in range(8):
            x = jj[sec == k]
            if len(x) >= 40:
                gc = x["G_c"].mean()
                rows.append([DIRS[k], str(len(x)), cz(x["W_c"].mean(), 1), cz(x["W_s"].mean(), 1),
                             cz(100 * x["W_s"].mean() / x["W_c"].mean(), 0) + " %",
                             cz(gc, 1), cz(x["G_s"].mean(), 1),
                             (cz(100 * x["G_s"].mean() / gc, 0) + " %") if gc > 0 else "–"])
        if len(jj) >= 40:
            gc = jj["G_c"].mean()
            rows.append(["**všechny směry**", str(len(jj)), cz(jj["W_c"].mean(), 1), cz(jj["W_s"].mean(), 1),
                         cz(100 * jj["W_s"].mean() / jj["W_c"].mean(), 0) + " %", cz(gc, 1), cz(jj["G_s"].mean(), 1),
                         (cz(100 * jj["G_s"].mean() / gc, 0) + " %") if gc > 0 else "–"])
        if rows:
            md += ["Vítr podle směru (jen hodiny, kdy ČHMÚ měřil aspoň 2 m/s; směr podle ČHMÚ; průměr a nejvyšší náraz za hodinu v m/s):", "",
                   md_table(["Vítr od", "Hodin", "Průměr ČHMÚ", "Průměr stanice", "Stanice / ČHMÚ",
                             "Náraz ČHMÚ", "Náraz stanice", "Stanice / ČHMÚ"], rows), "",
                   "Nárazy stanice jsou podhodnocené i tím, že se ukládá jedna okamžitá hodnota za 5 minut, "
                   "kdežto ČHMÚ zaznamená nejvyšší náraz z celých deseti minut.", ""]
        if "D_s" in j.columns:
            both = jj[jj["D_s"].notna() & (jj["W_s"] >= 0.5)]
            if len(both) >= 200:
                sc = (((both["D_c"] + 22.5) % 360) // 45).astype(int)
                ss = (((both["D_s"] + 22.5) % 360) // 45).astype(int)
                rows = [[DIRS[k], cz(100.0 * float((sc == k).mean()), 0) + " %", cz(100.0 * float((ss == k).mean()), 0) + " %"]
                        for k in range(8)]
                md += ["Odkud fouká podle ČHMÚ a podle stanice (podíl hodin; jen když ČHMÚ měří aspoň 2 m/s a stanice aspoň 0,5 m/s). "
                       "Když stanice ukazuje skoro jen dva protilehlé směry, vítr u ní usměrňuje překážka (hrana lesa, stěna domu):", "",
                       md_table(["Směr", "ČHMÚ", "Stanice"], rows), ""]
        # silný vítr: co ukazuje stanice, když ČHMÚ hlásí silné nárazy
        gg = j[j["G_c"].notna() & j["G_s"].notna()]
        rows = []
        for lo, hi in ((8, 11), (11, 14), (14, 17), (17, 99)):
            x = gg[(gg["G_c"] >= lo) & (gg["G_c"] < hi)]
            if len(x) >= 8:
                rows.append([("%d–%d" % (lo, hi)) if hi < 99 else ("%d a víc" % lo), str(len(x)), cz(x["G_s"].median(), 1),
                             "%s–%s" % (cz(x["G_s"].quantile(0.1), 1), cz(x["G_s"].quantile(0.9), 1)), cz(x["G_s"].max(), 1)])
        if rows:
            md += ["Co ukáže stanice, když ČHMÚ naměří silný náraz (m/s):", "",
                   md_table(["Náraz ČHMÚ", "Hodin", "Stanice: typicky", "Stanice: 80 % případů", "Stanice: nejvíc"], rows), ""]
    if "T_s" in j and "T_c" in j:
        d = (j["T_s"] - j["T_c"]).dropna()
        hrs = [0, 3, 6, 9, 12, 15, 18, 21]
        rows = []
        for nm, x in (("léto (V–IX)", d[(d.index.month >= 5) & (d.index.month <= 9)]),
                      ("zima (XI–III)", d[(d.index.month >= 11) | (d.index.month <= 3)]), ("celé období", d)):
            if len(x) > 200:
                g = x.groupby(x.index.hour).mean()
                rows.append([nm] + [cz(float(g.get(h, np.nan)), 1) for h in hrs] + [cz(float(x.mean()), 1)])
        if rows:
            md += ["Rozdíl teploty stanice − ČHMÚ podle denní doby (°C, hodiny v UTC; SEČ = UTC + 1, letní čas = UTC + 2):", "",
                   md_table(["Období"] + ["%02d h" % h for h in hrs] + ["Průměr"], rows), ""]
    pr = raw if raw is not None else st
    if "P" in pr and "P" in ref:
        both = pd.DataFrame({"P_s": pr["P"], "P_c": ref["P"]}).dropna()
        if len(both):
            g = both.groupby([both.index.year, both.index.month]).sum()
            rows = [["%d/%d" % (mm, yy), cz(float(r["P_c"]), 0), cz(float(r["P_s"]), 0),
                     (cz(100 * float(r["P_s"]) / float(r["P_c"]), 0) + " %") if float(r["P_c"]) >= 5 else "–"]
                    for (yy, mm), r in g.iterrows()]
            md += ["Srážky po měsících (mm, jen hodiny, kdy měřily obě stanice; před vyřazením vadných měsíců):", "",
                   md_table(["Měsíc", "ČHMÚ", "Stanice", "Stanice / ČHMÚ"], rows), ""]
    return md


# --------------------------------------------------------------------------
# Statistika
# --------------------------------------------------------------------------

def basic_stats(f, o):
    d = (f - o).dropna()
    n = int(len(d))
    if n == 0:
        return {"n": 0, "bias": np.nan, "mae": np.nan, "rmse": np.nan}
    return {"n": n, "bias": float(d.mean()), "mae": float(d.abs().mean()),
            "rmse": float(math.sqrt((d ** 2).mean()))}


def _roll(a, w):
    out = a.copy()
    out[w:] = a[w:] - a[:-w]
    return out


def rolling_blend(E, O, lead, kind, mode="mean", window=WINDOW, shrink=SHRINK, minp=MINP, Ecal=None, Ocal=None):
    """
    Klouzavá kalibrace jen z minulosti.
    E: čas × model (předpovědi vydané o `lead` dní dřív), O: měření.
    kind: "add" (teplota) nebo "mul" (vítr). mode: "none" | "mean" | "hod3" | "ratio".
    Ecal, Ocal: když jsou zadané, opravy i váhy se počítají z nich (předpovědi a měření
    na jiném místě) a jen se použijí na E. Tak se dá zjistit, jak by dopadla kalibrace převzatá odjinud.
    Vrací (opravené předpovědi, směs).
    """
    idx = E.index
    Ev = E.to_numpy(dtype=float)
    if Ecal is None:
        Cv, Ov = Ev, O.reindex(idx).to_numpy(dtype=float)
    else:
        Cv = Ecal.reindex(index=idx, columns=E.columns).to_numpy(dtype=float)
        Ov = Ocal.reindex(idx).to_numpy(dtype=float)
    day0 = idx.min().normalize()
    dpos = ((idx.normalize() - day0) / pd.Timedelta(days=1)).astype(int).to_numpy()
    hod = idx.hour.to_numpy()
    nd = int(dpos.max()) + 1
    nm = Ev.shape[1]
    shift = lead + 1
    Fc = np.full_like(Ev, np.nan)       # opravené předpovědi pro cílové místo
    Fk = np.full_like(Ev, np.nan)       # opravené předpovědi tam, kde se kalibruje (pro váhy)
    if mode == "hod3":
        nb, bins = 8, hod // 3
    else:
        nb, bins = 1, np.zeros(len(idx), dtype=int)
    need = minp * (24 // nb)
    with np.errstate(invalid="ignore", divide="ignore"):
        for j in range(nm):
            e = Cv[:, j]
            ok = ~np.isnan(e) & ~np.isnan(Ov)
            if mode == "none":
                Fc[:, j] = Ev[:, j]
                Fk[:, j] = e
            elif kind == "add":
                S = np.zeros((nd, nb))
                C = np.zeros((nd, nb))
                np.add.at(S, (dpos[ok], bins[ok]), (e - Ov)[ok])
                np.add.at(C, (dpos[ok], bins[ok]), 1.0)
                rs = _roll(np.cumsum(S, axis=0), window)
                rc = _roll(np.cumsum(C, axis=0), window)
                bias = np.where(rc >= need, rs / np.maximum(rc, 1.0), np.nan) * shrink
                bsh = np.full_like(bias, np.nan)
                if nd > shift:
                    bsh[shift:] = bias[:-shift]
                Fc[:, j] = Ev[:, j] - bsh[dpos, bins]
                Fk[:, j] = e - bsh[dpos, bins]
            else:
                SF = np.zeros(nd)
                SO = np.zeros(nd)
                C = np.zeros(nd)
                np.add.at(SF, dpos[ok], e[ok])
                np.add.at(SO, dpos[ok], Ov[ok])
                np.add.at(C, dpos[ok], 1.0)
                rf = _roll(np.cumsum(SF), window)
                ro = _roll(np.cumsum(SO), window)
                rc = _roll(np.cumsum(C), window)
                ratio = np.where((rc >= minp * 24) & (rf > 1e-6), ro / np.maximum(rf, 1e-6), np.nan)
                ratio = 1.0 + shrink * (np.clip(ratio, 0.4, 2.5) - 1.0)
                rsh = np.full(nd, np.nan)
                if nd > shift:
                    rsh[shift:] = ratio[:-shift]
                Fc[:, j] = Ev[:, j] * rsh[dpos]
                Fk[:, j] = e * rsh[dpos]
        err2 = (Fk - Ov[:, None]) ** 2
        S2 = np.zeros((nd, nm))
        C2 = np.zeros((nd, nm))
        for j in range(nm):
            ok = ~np.isnan(err2[:, j])
            np.add.at(S2[:, j], dpos[ok], err2[ok, j])
            np.add.at(C2[:, j], dpos[ok], 1.0)
        rs2 = _roll(np.cumsum(S2, axis=0), window)
        rc2 = _roll(np.cumsum(C2, axis=0), window)
        mse = np.where(rc2 >= minp * 24, rs2 / np.maximum(rc2, 1.0), np.nan)
        msh = np.full_like(mse, np.nan)
        if nd > shift:
            msh[shift:] = mse[:-shift]
        wt = 1.0 / np.maximum(msh, 0.05)
        Wt = wt[dpos, :]
        valid = ~np.isnan(Fc) & ~np.isnan(Wt)
        num = np.where(valid, Fc * Wt, 0.0).sum(axis=1)
        den = np.where(valid, Wt, 0.0).sum(axis=1)
        cnt = valid.sum(axis=1)
        blend = np.where(cnt >= 2, num / np.maximum(den, 1e-12), np.nan)
    return (pd.DataFrame(Fc, index=idx, columns=E.columns),
            pd.Series(blend, index=idx))


def current_calibration(E, O, kind, mode="mean", window=WINDOW, shrink=SHRINK, minp=MINP):
    """
    Kalibrace z posledních `window` dní pro provozní předpověď.
    Vrací slovník model -> {"bias": [...] | "ratio": x, "mse": y, "n": n} a RMSE směsi.
    """
    out = {}
    if E.empty:
        return out, np.nan
    idx = E.index
    last = idx.max()
    sel = idx > (last - pd.Timedelta(days=window))
    E = E[sel]
    O = O.reindex(E.index)
    hod = E.index.hour.to_numpy()
    Ov = O.to_numpy(dtype=float)
    corrected = {}
    for m in E.columns:
        e = E[m].to_numpy(dtype=float)
        ok = ~np.isnan(e) & ~np.isnan(Ov)
        if ok.sum() < minp * 24:
            continue
        entry = {}
        if mode == "none":
            c = e
        elif kind == "add":
            allb = float((e[ok] - Ov[ok]).mean())
            if mode == "hod3":
                bias = []
                for b in range(8):
                    sb = ok & ((hod // 3) == b)
                    bias.append(shrink * (float((e[sb] - Ov[sb]).mean()) if sb.sum() >= 12 else allb))
                c = e - np.array(bias)[hod // 3]
            else:
                bias = [shrink * allb]
                c = e - bias[0]
            entry["bias"] = [round(float(x), 3) for x in bias]
        else:
            sf = float(e[ok].sum())
            ratio = float(np.clip(Ov[ok].sum() / sf, 0.4, 2.5)) if sf > 1e-6 else 1.0
            ratio = 1.0 + shrink * (ratio - 1.0)
            c = e * ratio
            entry["ratio"] = round(ratio, 3)
        mse = float(((c - Ov)[ok] ** 2).mean())
        entry["mse"] = round(mse, 4)
        entry["n"] = int(ok.sum())
        out[m] = entry
        corrected[m] = pd.Series(c, index=E.index)
    rmse = np.nan
    use = [m for m in corrected if m in BLEND]
    if len(use) >= 2:
        C = pd.DataFrame({m: corrected[m] for m in use})
        w = pd.Series({m: 1.0 / max(out[m]["mse"], 0.05) for m in use})
        W = pd.DataFrame(np.tile(w.to_numpy(), (len(C), 1)), index=C.index, columns=C.columns).where(C.notna())
        b = (C * W).sum(axis=1) / W.sum(axis=1)
        d = (b - O).dropna()
        if len(d):
            rmse = float(math.sqrt((d ** 2).mean()))
    return out, rmse


# --------------------------------------------------------------------------
# Formátování
# --------------------------------------------------------------------------

def cz(x, nd=1):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "–"
    s = "%.*f" % (nd, x)
    if float(s) == 0:
        s = s.replace("-", "")
    return s.replace(".", ",").replace("-", "−")


def md_table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(lines)


def season_mask(idx, name):
    m = idx.month
    if name == "léto (V–IX)":
        return (m >= 5) & (m <= 9)
    if name == "zima (XI–III)":
        return (m >= 11) | (m <= 3)
    return np.ones(len(idx), dtype=bool)


# --------------------------------------------------------------------------
# Režim: zpětné vyhodnocení
# --------------------------------------------------------------------------

def verify_target(title, intro, obs, fc, start, end, station_id, vars_=("T", "W", "G"), transfer=None, site=None):
    """transfer = (předpovědi, měření, způsoby kalibrace, název) referenčního místa: porovná se,
    jestli je lepší kalibrovat podle tohoto měření, nebo kalibraci převzít z referenčního místa.
    site (kvůli výšce slunce) je potřeba pro oddělené vyhodnocení noci."""
    md = []
    skill = {"period": [str(start), str(end)], "station": station_id, "models": {}, "blend": {}, "method": {}}
    md.append("# " + title)
    md.append("")
    md.append(intro)
    md.append("")
    md.append("Chyba = průměrná absolutní odchylka předpovědi od měření (menší je lepší). "
              "Odchylka = průměr (předpověď − měření); kladná znamená, že model nadsazuje.")
    md.append("")

    summary_rows = []
    for vk in vars_:
        base, kind, unit, title = VARS[vk]
        o = obs[vk] if vk in obs else pd.Series(dtype=float)
        if o.notna().sum() < 200:
            md.append("## %s\n\nMěření nejsou k dispozici.\n" % title)
            continue
        md.append("## %s (%s)" % (title, unit))
        md.append("")
        # tabulka po modelech
        per = {}
        for L in EVAL_LEADS:
            E = fc.get((vk, L), pd.DataFrame())
            for m in E.columns:
                per.setdefault(m, {})[L] = basic_stats(E[m], o.reindex(E.index))
        order = sorted(per, key=lambda m: (per[m].get(1, {}).get("mae", np.nan)
                                           if not np.isnan(per[m].get(1, {}).get("mae", np.nan)) else 99))
        rows = []
        for m in order:
            r = [m]
            for L in EVAL_LEADS:
                s = per[m].get(L)
                r.append(cz(s["mae"], 2) if s and s["n"] >= 200 else "–")
            s1 = per[m].get(1)
            r.append(cz(s1["bias"], 2) if s1 and s1["n"] >= 200 else "–")
            r.append(str(s1["n"]) if s1 else "0")
            rows.append(r)
            skill["models"].setdefault(m, {})[vk] = {str(L): per[m].get(L) for L in EVAL_LEADS}
        md.append(md_table(["Model", "Chyba +1 den", "+2 dny", "+3 dny", "+5 dní", "Odchylka +1 den", "Hodin (+1 den)"], rows))
        md.append("")

        # směs: vyzkoušej všechny způsoby kalibrace na stejných hodinách
        variants = VARIANTS[kind]
        base = {}
        res = {}
        for L in EVAL_LEADS:
            E = fc.get((vk, L), pd.DataFrame())
            cols = [m for m in E.columns if m in BLEND]
            if len(cols) < 2:
                continue
            Eb = E[cols]
            oo = o.reindex(Eb.index)
            base[L] = (E, Eb, oo)
            for v in variants:
                _, bl = rolling_blend(Eb, oo, L, kind, mode=v[0], window=v[1])
                res.setdefault(v, {})[L] = bl
        masks = {}
        for L in list(base):
            msk = base[L][2].notna()
            for v in variants:
                msk &= res[v][L].notna()
            if int(msk.sum()) >= 300:
                masks[L] = msk
            else:
                del base[L]
        vmae = {v: {L: float((res[v][L][masks[L]] - base[L][2][masks[L]]).abs().mean()) for L in base}
                for v in variants}
        best_v = DEFAULT_METHOD[vk]
        if base:
            score = {v: float(np.mean(list(vmae[v].values()))) for v in variants}
            best_v = min(score, key=score.get)
            skill["method"][vk] = {"mode": best_v[0], "window": best_v[1],
                                   "variants": {"%s/%d" % v: {str(L): x for L, x in vmae[v].items()} for v in variants}}
            vrows = []
            for v in variants:
                name = VARIANT_NAMES[v[0]] + ("" if v[0] == "none" else ", okno %d dní" % v[1])
                vrows.append([("**%s**" % name) if v == best_v else name] +
                             [cz(vmae[v].get(L, np.nan), 2) for L in EVAL_LEADS])
            md.append("**Který způsob kalibrace funguje nejlíp** (chyba směsi; vše počítáno jen z dat starších než den vydání):")
            md.append("")
            md.append(md_table(["Způsob", "+1 den", "+2 dny", "+3 dny", "+5 dní"], vrows))
            md.append("")
        md.append("**Směs (%s) proti jednotlivým modelům** na stejných hodinách:" %
                  (VARIANT_NAMES[best_v[0]] + ("" if best_v[0] == "none" else ", okno %d dní" % best_v[1])))
        md.append("")
        rows = []
        for L in EVAL_LEADS:
            if L not in base:
                continue
            E, Eb, oo = base[L]
            cols = list(Eb.columns)
            blend = res[best_v][L]
            okb = masks[L]
            nb = int(okb.sum())
            sb = basic_stats(blend[okb], oo[okb])
            raw_mean = Eb.mean(axis=1).where(Eb.notna().sum(axis=1) >= 2)
            sm = basic_stats(raw_mean[okb], oo[okb])
            best_name, best = None, None
            for m in cols:
                s = basic_stats(Eb[m][okb], oo[okb])
                if s["n"] >= 0.6 * nb and (best is None or s["mae"] < best["mae"]):
                    best_name, best = m, s
            bm = E["Open-Meteo best match"] if "Open-Meteo best match" in E.columns else None
            sbm = basic_stats(bm[okb], oo[okb]) if bm is not None else {"mae": np.nan}
            gain = (1 - sb["mae"] / best["mae"]) * 100 if best and best["mae"] > 0 else np.nan
            rows.append(["+%d d" % L, cz(sb["mae"], 2),
                         "%s (%s)" % (cz(best["mae"], 2), best_name) if best else "–",
                         cz(sm["mae"], 2), cz(sbm["mae"], 2),
                         (cz(gain, 0) + " %") if not np.isnan(gain) else "–", str(nb)])
            skill["blend"].setdefault(vk, {})[str(L)] = {
                "mae": sb["mae"], "rmse": sb["rmse"], "bias": sb["bias"], "n": nb,
                "best_single": best_name, "best_single_mae": best["mae"] if best else None,
                "raw_mean_mae": sm["mae"], "best_match_mae": sbm["mae"]}
            summary_rows.append([title, "+%d d" % L, cz(best["mae"], 2) if best else "–", cz(sm["mae"], 2),
                                 cz(sb["mae"], 2), (cz(gain, 0) + " %") if not np.isnan(gain) else "–"])
            # sezóny
            for sname in ("léto (V–IX)", "zima (XI–III)"):
                sel = okb & season_mask(blend.index, sname)
                if int(sel.sum()) >= 300 and L in (1, 3):
                    s1 = basic_stats(blend[sel], oo[sel])
                    bbest, bname = None, None
                    for m in cols:
                        s = basic_stats(Eb[m][sel], oo[sel])
                        if s["n"] >= 0.6 * int(sel.sum()) and (bbest is None or s["mae"] < bbest["mae"]):
                            bname, bbest = m, s
                    skill["blend"][vk][str(L)][sname] = {
                        "mae": s1["mae"], "best_single": bname,
                        "best_single_mae": bbest["mae"] if bbest else None, "n": int(sel.sum())}
        if rows:
            md.append(md_table(["Předstih", "Směs", "Nejlepší jednotlivý model", "Prostý průměr modelů",
                                "Open-Meteo best match", "Zlepšení proti nejlepšímu", "Hodin"], rows))
        else:
            md.append("Na směs zatím není dost dat.")
        md.append("")
        seas = []
        for L in (1, 3):
            b = skill["blend"].get(vk, {}).get(str(L), {})
            for sname in ("léto (V–IX)", "zima (XI–III)"):
                if sname in b:
                    x = b[sname]
                    seas.append([sname, "+%d d" % L, cz(x["mae"], 2),
                                 "%s (%s)" % (cz(x["best_single_mae"], 2), x["best_single"]) if x["best_single"] else "–",
                                 str(x["n"])])
        if seas:
            md.append("Podle sezóny:")
            md.append("")
            md.append(md_table(["Sezóna", "Předstih", "Směs", "Nejlepší jednotlivý model", "Hodin"], seas))
            md.append("")

        if transfer is not None and base:
            fc_ref, obs_ref, meth_ref, ref_name = transfer
            mref = meth_ref.get(vk, DEFAULT_METHOD[vk])
            split = (vk == "T" and site is not None)
            trows, tinfo = [], {}
            for L in EVAL_LEADS:
                Er = fc_ref.get((vk, L), pd.DataFrame())
                if L not in base or Er.empty or vk not in obs_ref:
                    continue
                E, Eb, oo = base[L]
                _, bt = rolling_blend(Eb, oo, L, kind, mode=mref[0], window=mref[1], Ecal=Er, Ocal=obs_ref[vk])
                msk = masks[L] & bt.notna()
                nn = int(msk.sum())
                if nn < 300:
                    continue
                own_mae = float((res[best_v][L][msk] - oo[msk]).abs().mean())
                tr_mae = float((bt[msk] - oo[msk]).abs().mean())
                info = {"own": own_mae, "transfer": tr_mae, "n": nn}
                row = ["+%d d" % L, cz(own_mae, 2), cz(tr_mae, 2)]
                if split:
                    night = pd.Series(sun_elev(Eb.index, site["lat"], site["lon"]) < NIGHT_ELEV, index=Eb.index)
                    _, bn = rolling_blend(Eb, oo.where(night), L, kind, mode=best_v[0], window=best_v[1], minp=NIGHT_MINP)
                    mn = msk & night & bn.notna()
                    if int(mn.sum()) >= 150:
                        info.update({"own_night": float((bn[mn] - oo[mn]).abs().mean()),
                                     "transfer_night": float((bt[mn] - oo[mn]).abs().mean()),
                                     "transfer_night_bias": float((bt[mn] - oo[mn]).mean()), "n_night": int(mn.sum())})
                    row += [cz(info.get("own_night", np.nan), 2), cz(info.get("transfer_night", np.nan), 2),
                            cz(info.get("transfer_night_bias", np.nan), 2)]
                row.append(str(nn))
                trows.append(row)
                tinfo[str(L)] = info
            if trows:
                o_m = float(np.mean([x["own"] for x in tinfo.values()]))
                t_m = float(np.mean([x["transfer"] for x in tinfo.values()]))
                tr = {"by_lead": tinfo, "own_better": bool(o_m < 0.98 * t_m), "use": "all" if o_m < 0.98 * t_m else "none"}
                verdict = ("kalibrace podle vlastní stanice je lepší, předpověď ji použije" if tr["use"] == "all"
                           else "vlastní stanice kalibraci nezlepší, zůstává %s" % ref_name)
                if split:
                    d = (obs[vk] - obs_ref[vk]).dropna()
                    el = sun_elev(d.index, site["lat"], site["lon"])
                    dd, dn = d[el > DAY_ELEV], d[el < NIGHT_ELEV]
                    if len(dd) >= 200 and len(dn) >= 200:
                        tr["day_diff"], tr["night_diff"] = float(dd.mean()), float(dn.mean())
                        tr["day_excess"] = tr["day_diff"] - tr["night_diff"]
                    nights = [x for x in tinfo.values() if "own_night" in x]
                    if nights:
                        on = float(np.mean([x["own_night"] for x in nights]))
                        tn = float(np.mean([x["transfer_night"] for x in nights]))
                        tr["night_better"] = bool(on < 0.98 * tn)
                    if tr.get("day_excess", 0.0) >= 1.0:
                        tr["use"] = "night" if tr.get("night_better") else "none"
                        verdict = ("přes den stanice ukazuje proti ČHMÚ o %s °C víc než v noci, čidlo se tedy na slunci přehřívá "
                                   "a denní hodnoty se ke kalibraci nehodí; %s"
                                   % (cz(tr["day_excess"], 1),
                                      "noční hodnoty kalibraci zlepšují, předpověď je použije pro noc" if tr["use"] == "night"
                                      else "ani noční hodnoty kalibraci nezlepší, zůstává %s" % ref_name))
                skill.setdefault("transfer", {})[vk] = tr
                md.append("**Vyplatí se kalibrovat podle vlastní stanice?** Chyba směsi proti vlastní stanici, "
                          "když se opravy a váhy modelů počítají z vlastní stanice, nebo se převezmou z %s:" % ref_name)
                md.append("")
                hdr = ["Předstih", "Vlastní stanice", "Převzato z %s" % ref_name]
                if split:
                    hdr += ["Jen noc: vlastní", "Jen noc: převzato", "Jen noc: odchylka převzaté"]
                md.append(md_table(hdr + ["Hodin"], trows))
                md.append("")
                if "day_excess" in tr:
                    md.append("Stanice proti ČHMÚ: přes den (slunce nad 10°) v průměru %s °C, v noci %s °C."
                              % (cz(tr["day_diff"], 1), cz(tr["night_diff"], 1)))
                    md.append("")
                md.append("Závěr: %s." % verdict)
                md.append("")

        if vk == "T":
            E = fc.get(("T", 1), pd.DataFrame())
            top = [m for m in order if m in E.columns][:8]
            if top:
                hrs = [0, 3, 6, 9, 12, 15, 18, 21]
                rows = []
                for m in top:
                    d = (E[m] - o.reindex(E.index)).dropna()
                    g = d.groupby(d.index.hour).mean()
                    rows.append([m] + [cz(float(g.get(h, np.nan)), 1) for h in hrs])
                md.append("Odchylka teploty podle denní doby (předstih 1 den, hodiny v UTC; SEČ = UTC + 1):")
                md.append("")
                md.append(md_table(["Model"] + ["%02d h" % h for h in hrs], rows))
                md.append("")

    # srážky: denní úhrny
    if "P" in obs and obs["P"].notna().sum() >= 200:
        md.append("## Srážky (denní úhrny, mm)")
        md.append("")
        o = obs["P"]
        od = o.groupby(o.index.normalize()).sum().where(o.groupby(o.index.normalize()).count() >= 22)
        rows = []
        pstats = {}
        for L in (1, 3):
            E = fc.get(("P", L), pd.DataFrame())
            if E.empty:
                continue
            for m in list(E.columns) + ["Medián modelů"]:
                if m == "Medián modelů":
                    cols = [c for c in E.columns if c in BLEND]
                    f = E[cols].median(axis=1).where(E[cols].notna().sum(axis=1) >= 3)
                else:
                    f = E[m]
                fd = f.groupby(f.index.normalize()).sum().where(f.groupby(f.index.normalize()).count() >= 22)
                both = pd.concat([fd, od], axis=1, keys=["f", "o"]).dropna()
                if len(both) < 60:
                    continue
                a = int(((both.f >= 1) & (both.o >= 1)).sum())
                b = int(((both.f >= 1) & (both.o < 1)).sum())
                c = int(((both.f < 1) & (both.o >= 1)).sum())
                pstats.setdefault(m, {})[L] = {
                    "n": len(both), "mae": float((both.f - both.o).abs().mean()),
                    "bias": float((both.f - both.o).mean()),
                    "pod": a / (a + c) if a + c else np.nan,
                    "far": b / (a + b) if a + b else np.nan}
        order = sorted(pstats, key=lambda m: pstats[m].get(1, {}).get("mae", 99))
        for m in order:
            s1, s3 = pstats[m].get(1), pstats[m].get(3)
            rows.append([m,
                         cz(s1["mae"], 2) if s1 else "–", cz(s1["bias"], 2) if s1 else "–",
                         (cz(s1["pod"] * 100, 0) + " %") if s1 and not np.isnan(s1["pod"]) else "–",
                         (cz(s1["far"] * 100, 0) + " %") if s1 and not np.isnan(s1["far"]) else "–",
                         cz(s3["mae"], 2) if s3 else "–",
                         str(s1["n"]) if s1 else "0"])
            skill["models"].setdefault(m, {})["P"] = {str(k): v for k, v in pstats[m].items()}
        md.append("Zachycené deště = podíl dní s naměřeným úhrnem aspoň 1 mm, které model předpověděl. "
                  "Plané poplachy = podíl dní, kdy model dal aspoň 1 mm a nenapršelo.")
        md.append("")
        md.append(md_table(["Model", "Chyba +1 den", "Odchylka +1 den", "Zachycené deště", "Plané poplachy",
                            "Chyba +3 dny", "Dní"], rows))
        md.append("")

    if summary_rows:
        md.insert(5, "## Shrnutí\n\n" + md_table(
            ["Veličina", "Předstih", "Nejlepší jednotlivý model", "Prostý průměr modelů", "Kalibrovaná směs",
             "Směs proti nejlepšímu"], summary_rows) + "\n")
    return md, skill


def run_verify(start, outdir):
    site = SITES["cerna"]
    today = dt.datetime.now(dt.timezone.utc).date()
    end = today - dt.timedelta(days=1)
    log("== Zpětné vyhodnocení %s až %s, stanice ČHMÚ %s" % (start, end, site["chmi"]))

    log("-- měření ČHMÚ")
    df10 = fetch_chmi_10min(site["chmi"], start, end)
    obs = obs_hourly(df10)
    if obs.empty:
        raise SystemExit("Nepodařilo se načíst měření ČHMÚ.")
    log("  hodinových záznamů: %d (%s až %s)" % (len(obs), obs.index.min(), obs.index.max()))
    log("  platných hodnot: " + ", ".join("%s %d" % (k, int(obs[k].notna().sum())) for k in obs.columns))

    log("-- archiv předpovědí Open-Meteo")
    fc = fetch_previous_runs(site, start, end)
    log("  dotazů: %d, váha: %.0f, zbývá v limitu: %s" % (STATE["om_calls"], STATE["om_cost"], STATE["om_remaining"]))
    if all(v.empty for v in fc.values()):
        raise SystemExit("Nepodařilo se načíst žádné předpovědi: " + "; ".join(STATE["errors"][:5]))

    period = "%s až %s" % (start.strftime("%-d. %-m. %Y"), end.strftime("%-d. %-m. %Y"))
    md, skill = verify_target(
        "Jak se modely trefují v Černé v Pošumaví (stanice ČHMÚ)",
        "Období: %s. Měřítko: stanice ČHMÚ Černá v Pošumaví (740 m), desetiminutová data převedená na hodinová. "
        "Předpovědi: archiv Open-Meteo, vždy to, co model říkal 1, 2, 3 a 5 dní předem. Časy v UTC." % period,
        obs, fc, start, end, site["chmi"])
    skill["targets"] = {}
    ref_method = {k: (v["mode"], int(v["window"])) for k, v in skill["method"].items()}
    for key, s_site in SITES.items():
        log("-- vlastní stanice: %s" % s_site["name"])
        raw = station_update(key, start, end, backfill=True)
        if len(raw):
            raw = raw[(raw.index >= pd.Timestamp(start)) & (raw.index < pd.Timestamp(end) + pd.Timedelta(days=1))]
        st, notes = station_qc(raw, obs)
        if st is None or not len(st) or st["T"].notna().sum() < 24 * 45:
            log("  málo dat, vynechávám")
            continue
        for x in notes:
            log("  kontrola dat: " + x)
        own = tuple(v for v in (s_site.get("own") or ()) if v in ("T", "W", "G"))
        md += ["", "---", ""]
        if own:
            s0 = max(start, st[own[0]].first_valid_index().date())
            fcs = fc if key == "cerna" else fetch_previous_runs(s_site, s0, end, var_keys=own + ("P",), leads=EVAL_LEADS)
            m2, s2 = verify_target(
                "%s: modely proti vlastní stanici" % s_site["name"],
                "Období: %s až %s. Měřítko: vlastní stanice GARNI, hodinové hodnoty po vyřazení vadných úseků. Časy v UTC."
                % (s0.strftime("%-d. %-m. %Y"), end.strftime("%-d. %-m. %Y")),
                st, fcs, s0, end, s_site.get("wu") or "PWL", vars_=own, site=s_site,
                transfer=(fc, obs, ref_method, "ČHMÚ Černá"))
            md += m2 + [""]
            skill["targets"][key] = s2
        md += station_vs_chmi(s_site["name"], st, obs, raw=raw, notes=notes)
    if STATE["errors"]:
        md.append("## Co se nepodařilo načíst")
        md.append("")
        for e in STATE["errors"]:
            md.append("- " + e)
        md.append("")
    md.append("Zdroje: předpovědi Open-Meteo.com (CC BY 4.0), měření ČHMÚ (opendata.chmi.cz).")
    text = "\n".join(md) + "\n"
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "verifikace.md"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(outdir, "skill.json"), "w", encoding="utf-8") as f:
        json.dump(skill, f, ensure_ascii=False, indent=1, default=lambda x: None if isinstance(x, float) and math.isnan(x) else x)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(text)
    log("\n" + text)


# --------------------------------------------------------------------------
# Režim: aktuální předpověď
# --------------------------------------------------------------------------

DIRS = ["S", "SV", "V", "JV", "J", "JZ", "Z", "SZ"]
DAYS = ["po", "út", "st", "čt", "pá", "so", "ne"]


def lead_bucket(hours_ahead):
    if hours_ahead <= 30:
        return 1
    if hours_ahead <= 54:
        return 2
    if hours_ahead <= 90:
        return 3
    return 5


def fetch_current(site):
    names = ["temperature_2m", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m",
             "precipitation", "cloud_cover", "cape", "snowfall"]
    per = {}
    for label, ids, _ in MODELS:
        merged = None
        label_errors = []
        for mid in ids:
            try:
                df = om_fetch(OM_FORECAST, site, mid, names, forecast_days=8, past_days=1)
            except ApiError as e:
                label_errors.append("%s (%s): %s" % (label, mid, e))
                if "limit API" in str(e):
                    break
                continue
            merged = df if merged is None else merged.combine_first(df)
            time.sleep(0.3)
        if merged is not None and merged.notna().any().any():
            per[label] = merged
        else:
            STATE["errors"].extend(label_errors or ["%s: bez dat" % label])
    return per


def apply_calibration(per, calib, now):
    """Vrací slovník veličina -> DataFrame čas × model (opravené hodnoty) a váhy."""
    out = {}
    for vk in ("T", "W", "G"):
        base, kind, _, _ = VARS[vk]
        cols = {}
        wts = {}
        for m, df in per.items():
            if base not in df.columns or m not in BLEND:
                continue
            s = df[base].copy()
            s = s[s.index >= now.floor("h")]
            if s.notna().sum() == 0:
                continue
            c = pd.Series(np.nan, index=s.index)
            w = pd.Series(np.nan, index=s.index)
            hrs = ((s.index - now) / pd.Timedelta(hours=1)).to_numpy()
            for L in (1, 2, 3, 5):
                sel = np.array([lead_bucket(h) == L for h in hrs])
                if not sel.any():
                    continue
                entry = None
                for LL in (L, 3, 2, 1):
                    if LL <= L:
                        entry = calib.get((vk, LL), {}).get(m)
                        if entry:
                            break
                vals = s.to_numpy(dtype=float)[sel]
                if entry is None:
                    # model bez historie: bez opravy, poloviční váha proti mediánu
                    others = [e["mse"] for e in calib.get((vk, min(L, 3)), {}).values()]
                    mse = (float(np.median(others)) * 2.0) if others else 4.0
                    cv = vals
                elif "bias" in entry:
                    barr = np.array(entry["bias"])
                    hh = s.index.hour.to_numpy()[sel]
                    cv = vals - (barr[hh // 3] if len(barr) == 8 else barr[0])
                    mse = entry["mse"]
                elif "ratio" in entry:
                    cv = vals * entry["ratio"]
                    mse = entry["mse"]
                else:
                    cv = vals
                    mse = entry["mse"]
                c.iloc[np.where(sel)[0]] = cv
                w.iloc[np.where(sel)[0]] = 1.0 / max(mse, 0.05)
            cols[m] = c
            wts[m] = w
        C = pd.DataFrame(cols)
        W = pd.DataFrame(wts).where(C.notna())
        out[vk] = (C, W)
    return out


def wmean_std(C, W):
    num = (C * W).sum(axis=1, min_count=1)
    den = W.sum(axis=1, min_count=1)
    mean = num / den
    var = ((C.sub(mean, axis=0)) ** 2 * W).sum(axis=1, min_count=1) / den
    return mean, np.sqrt(var), C.notna().sum(axis=1)


def agreement(spread, scale):
    if np.isnan(spread):
        return "–"
    if spread <= scale:
        return "vysoká"
    if spread <= 2 * scale:
        return "střední"
    return "nízká"


def run_forecast(outdir):
    now = pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
    today = now.date()
    method = dict(DEFAULT_METHOD)
    by_target = {}
    own_use = {}           # místo -> veličina -> "all" | "night" | "none" (ze zpětného vyhodnocení)
    try:
        with open(os.path.join(outdir, "skill.json"), encoding="utf-8") as f:
            sk = json.load(f)
        for k, v in (sk.get("method") or {}).items():
            method[k] = (v["mode"], int(v["window"]))
        for tk, tv in (sk.get("targets") or {}).items():
            by_target[tk] = {k: (v["mode"], int(v["window"])) for k, v in (tv.get("method") or {}).items()}
            own_use[tk] = {k: v.get("use") for k, v in (tv.get("transfer") or {}).items()}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    log("  způsob kalibrace: %s %s" % (method, by_target))
    maxwin = max([w for _, w in method.values()] + [w for t in by_target.values() for _, w in t.values()])
    start = today - dt.timedelta(days=maxwin + 20)
    cal_site = SITES["cerna"]
    log("== Předpověď, vydáno %s UTC" % now.strftime("%Y-%m-%d %H:%M"))

    def build(site_fc, obs_k, meth, var_keys=("T", "W", "G"), minp=MINP, fc=None):
        if fc is None:
            fc = fetch_previous_runs(site_fc, start, today, var_keys=tuple(var_keys), leads=[1, 2, 3, 5])
        cal, rm = {}, {}
        for vk in var_keys:
            kind = VARS[vk][1]
            for L in (1, 2, 3, 5):
                E = fc.get((vk, L), pd.DataFrame())
                if E.empty or vk not in obs_k or obs_k[vk].notna().sum() == 0:
                    continue
                c, rmse = current_calibration(E, obs_k[vk], kind, mode=meth[vk][0], window=meth[vk][1], minp=minp)
                cal[(vk, L)] = c
                rm[(vk, L)] = rmse
        return cal, rm, fc

    log("-- měření ČHMÚ za kalibrační okno")
    obs = obs_hourly(fetch_chmi_10min(cal_site["chmi"], start, today))
    log("-- poslední předpovědi modelů za kalibrační okno")
    calib0, rmse0, fc0 = build(cal_site, obs, method)
    ncal = len(calib0.get(("T", 1), {}))
    log("  modelů s kalibrací (teplota, +1 den): %d" % ncal)
    per_site = {}
    station_last = {}
    vnames = {"T": "teplota", "W": "vítr", "G": "nárazy"}
    for key, site in SITES.items():
        per_site[key] = (calib0, rmse0, "stanice ČHMÚ Černá v Pošumaví", None)
        raw = station_update(key)
        try:
            if raw is not None and len(raw) and raw["T"].notna().any():
                lt = raw["T"].dropna().index.max()
                if (now - lt) <= pd.Timedelta(hours=8):
                    r = raw.loc[lt]
                    station_last[key] = {"time_utc": lt.isoformat(), "temp": round(float(r["T"]), 1),
                                         "wind": None if pd.isna(r["W"]) else round(float(r["W"]), 1),
                                         "gust": None if pd.isna(r["G"]) else round(float(r["G"]), 1)}
        except Exception as e:      # jen doplněk pro stránku, nesmí shodit výpočet
            log("  %s: poslední měření stanice se nepodařilo připravit (%s)" % (key, e))
        own = [v for v in (site.get("own") or ()) if v in vnames]
        if not own or raw is None or not len(raw):
            continue
        st, _ = station_qc(raw, obs)
        use = {}
        for vk in own:
            if st is None or vk not in st or st[vk].notna().sum() == 0:
                continue
            how = own_use.get(key, {}).get(vk) or ("night" if vk == "T" else "none")
            if (now - st[vk].dropna().index.max()) > pd.Timedelta(days=OWN_MAX_AGE):
                log("  %s: %s z vlastní stanice je starší než %d dní, kalibruji podle ČHMÚ" % (key, vnames[vk], OWN_MAX_AGE))
            elif how == "none":
                log("  %s: %s podle vlastní stanice podle zpětného vyhodnocení nevychází líp, kalibruji podle ČHMÚ" % (key, vnames[vk]))
            else:
                use[vk] = how
        if not use:
            continue
        meth = dict(method)
        meth.update(by_target.get(key, {}))
        log("-- kalibrace podle vlastní stanice: %s (%s)" % (site["name"], ", ".join("%s: %s" % (vnames[v], h) for v, h in use.items())))
        stc = st.copy()
        if use.get("T") == "night":
            stc["T"] = stc["T"].where(sun_elev(stc.index, site["lat"], site["lon"]) < NIGHT_ELEV)
        c2, r2, _ = build(site, stc, meth, var_keys=list(use), minp=NIGHT_MINP if "night" in use.values() else MINP,
                          fc=fc0 if key == "cerna" else None)
        cal, rm, done, night_cal = dict(calib0), dict(rmse0), [], None
        for vk, how in use.items():
            if len(c2.get((vk, 1), {})) < 3:
                continue
            if how == "night":
                night_cal = {k: v for k, v in c2.items() if k[0] == vk}
                done.append("teplota v noci")
                continue
            for L in (1, 2, 3, 5):
                cal.pop((vk, L), None)
                rm.pop((vk, L), None)
                if (vk, L) in c2:
                    cal[(vk, L)] = c2[(vk, L)]
                    rm[(vk, L)] = r2[(vk, L)]
            done.append(vnames[vk])
        if done:
            per_site[key] = (cal, rm, "%s podle vlastní stanice, ostatní podle stanice ČHMÚ Černá v Pošumaví" % " a ".join(done), night_cal)
    calib_errors = list(STATE["errors"])
    STATE["errors"] = []

    result = {"issued_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "sites": {}, "errors": []}
    md = []
    issued_local = dt.datetime.now(TZ)
    md.append("# Předpověď pro Lipno – kalibrovaná směs modelů")
    md.append("")
    md.append("Vydáno %s %s." % (DAYS[issued_local.weekday()], issued_local.strftime("%-d. %-m. %Y %H:%M")))
    md.append("")

    for key, site in SITES.items():
        log("-- aktuální modely: %s" % site["name"])
        per = fetch_current(site)
        if len(per) < 2:
            md.append("## %s\n\nNepodařilo se načíst dost modelů.\n" % site["name"])
            continue
        calib, blend_rmse, src, night_cal = per_site[key]
        cal = apply_calibration(per, calib, now)
        if night_cal:
            # v noci (slunce pod obzorem) teplotu opravit podle vlastní stanice
            C, W = cal["T"]
            C2, W2 = apply_calibration(per, night_cal, now)["T"]
            have = set()
            for k, v in night_cal.items():
                have |= set(v)
            night = sun_elev(C.index, site["lat"], site["lon"]) < NIGHT_ELEV
            for m in C.columns:
                if m in have and m in C2.columns:
                    sel = night & C2[m].reindex(C.index).notna().to_numpy()
                    C.loc[sel, m] = C2[m].reindex(C.index)[sel]
                    W.loc[sel, m] = W2[m].reindex(C.index)[sel]
            cal["T"] = (C, W)
        Tm, Ts, Tn = wmean_std(*cal["T"])
        Wm, Ws, _ = wmean_std(*cal["W"])
        Gm, Gs, _ = wmean_std(*cal["G"])
        blend_models = [m for m in per if m in BLEND]
        P = pd.DataFrame({m: per[m]["precipitation"] for m in blend_models if "precipitation" in per[m]})
        P = P[P.index >= now.floor("h")]
        Dx = pd.DataFrame({m: np.sin(np.deg2rad(per[m]["wind_direction_10m"])) for m in blend_models if "wind_direction_10m" in per[m]})
        Dy = pd.DataFrame({m: np.cos(np.deg2rad(per[m]["wind_direction_10m"])) for m in blend_models if "wind_direction_10m" in per[m]})
        wdir = (np.rad2deg(np.arctan2(Dx.mean(axis=1), Dy.mean(axis=1))) + 360) % 360
        cape = pd.DataFrame({m: per[m]["cape"] for m in blend_models if "cape" in per[m]}).max(axis=1)

        idx = Tm.index
        local = idx.tz_localize("UTC").tz_convert(TZ)
        # bloky po 3 hodinách na 48 h
        rows = []
        hourly_json = []
        t0 = now.ceil("h")
        for k in range(0, 48, 3):
            a = t0 + pd.Timedelta(hours=k)
            b = a + pd.Timedelta(hours=3)
            sel = (idx > a) & (idx <= b)
            if not sel.any():
                continue
            la = (a.tz_localize("UTC").tz_convert(TZ))
            lb = (b.tz_localize("UTC").tz_convert(TZ))
            t = float(Tm[sel].mean())
            ts = float(Ts[sel].mean())
            L = lead_bucket(k + 1.5)
            unc = blend_rmse.get(("T", min(L, 3)), np.nan)
            half = 1.28 * math.sqrt((ts if not np.isnan(ts) else 0) ** 2 + (unc if not np.isnan(unc) else 1.5) ** 2)
            w = float(Wm[sel].mean())
            g = float(Gm[sel].max())
            gs = float(Gs[sel].mean())
            psel = P[(P.index > a) & (P.index <= b)]
            psum = psel.sum(axis=0, min_count=2).dropna()
            pamt = float(psum.mean()) if len(psum) else np.nan
            pprob = float((psum >= 0.3).mean() * 100) if len(psum) else np.nan
            d = wdir[(wdir.index > a) & (wdir.index <= b)]
            dname = DIRS[int(((float(d.iloc[len(d) // 2]) + 22.5) % 360) // 45)] if len(d) and not np.isnan(d.iloc[len(d) // 2]) else ""
            cp = cape[(cape.index > a) & (cape.index <= b)]
            storm = len(cp) and float(cp.max()) >= 600 and not np.isnan(pprob) and pprob >= 30
            rows.append(["%s %02d–%02d" % (DAYS[la.weekday()], la.hour, lb.hour),
                         "%s °C (%s až %s)" % (cz(t, 0), cz(t - half, 0), cz(t + half, 0)),
                         "%s / %s m/s %s" % (cz(w, 0), cz(g, 0), dname),
                         ("%s mm (%s %%)" % (cz(pamt, 1), cz(pprob, 0))) if not np.isnan(pamt) and (pamt >= 0.1 or pprob >= 20) else "–",
                         agreement(ts, 0.8) + (" ⚡" if storm else "")])
            hourly_json.append({"from_utc": a.isoformat(), "to_utc": b.isoformat(), "temp": round(t, 1),
                                "temp_lo": round(t - half, 1), "temp_hi": round(t + half, 1),
                                "wind": round(w, 1), "gust": round(g, 1), "gust_spread": None if np.isnan(gs) else round(gs, 1),
                                "dir": dname, "precip_mm": None if np.isnan(pamt) else round(pamt, 1),
                                "precip_prob": None if np.isnan(pprob) else round(pprob),
                                "models": int(Tn[sel].max())})
        md.append("## %s" % site["name"])
        md.append("")
        md.append(md_table(["Kdy", "Teplota", "Vítr / nárazy", "Srážky (shoda modelů)", "Jistota teploty"], rows))
        md.append("")
        # dny 1-7
        rows = []
        daily_json = []
        ldate = pd.Series(local.date, index=idx)
        for d in sorted(set(ldate.values))[:8]:
            sel = (ldate == d).to_numpy()
            if sel.sum() < 12:
                continue
            tmin, tmax = float(Tm[sel].min()), float(Tm[sel].max())
            gmax = float(Gm[sel].max())
            psel = P[np.isin(P.index, idx[sel])]
            psum = psel.sum(axis=0, min_count=12).dropna()
            pamt = float(psum.median()) if len(psum) else np.nan
            pprob = float((psum >= 1.0).mean() * 100) if len(psum) else np.nan
            rng = (float(psum.quantile(0.1)), float(psum.quantile(0.9))) if len(psum) >= 3 else (np.nan, np.nan)
            ts = float(Ts[sel].mean())
            nmod = int(Tn[sel].max())
            dd = pd.Timestamp(d)
            rows.append(["%s %d. %d." % (DAYS[dd.weekday()], dd.day, dd.month),
                         "%s / %s °C" % (cz(tmin, 0), cz(tmax, 0)),
                         "%s m/s" % cz(gmax, 0),
                         ("%s mm (%s–%s), %s %%" % (cz(pamt, 1), cz(rng[0], 0), cz(rng[1], 0), cz(pprob, 0))) if not np.isnan(pamt) else "–",
                         agreement(ts, 0.8), str(nmod)])
            daily_json.append({"date": str(d), "tmin": round(tmin, 1), "tmax": round(tmax, 1), "gust_max": round(gmax, 1),
                               "precip_mm": None if np.isnan(pamt) else round(pamt, 1),
                               "precip_prob_1mm": None if np.isnan(pprob) else round(pprob), "models": nmod})
        md.append(md_table(["Den", "Min / max", "Max. náraz", "Srážky: medián (rozpětí), pravděp. ≥ 1 mm",
                            "Shoda modelů", "Modelů"], rows))
        md.append("")
        md.append("Kalibrace: %s." % src)
        md.append("")
        # hodinové řady pro grafy (7 dní)
        series = []
        try:
            cloud = pd.DataFrame({m: per[m]["cloud_cover"] for m in blend_models if "cloud_cover" in per[m]}).median(axis=1)
            snow = pd.DataFrame({m: per[m]["snowfall"] for m in blend_models if "snowfall" in per[m]})
            snowshare = (snow > 0).sum(axis=1) / snow.notna().sum(axis=1).clip(lower=1) if snow.shape[1] else pd.Series(dtype=float)
            pn = P.notna().sum(axis=1)
            pmean = P.mean(axis=1).where(pn >= 2)
            pshare = ((P >= 0.1).sum(axis=1) / pn.clip(lower=1) * 100).where(pn >= 2)
            elev = pd.Series(sun_elev(idx, site["lat"], site["lon"]), index=idx)

            def val(sr, t, nd=1):
                v = sr.get(t, np.nan) if len(sr) else np.nan
                return None if v is None or pd.isna(v) else round(float(v), nd)

            for k in range(0, 168):
                t = t0 + pd.Timedelta(hours=k)
                if t not in idx or pd.isna(Tm.get(t, np.nan)):
                    continue
                ts = float(Ts.get(t, np.nan))
                unc = blend_rmse.get(("T", min(lead_bucket(k), 3)), np.nan)
                half = 1.28 * math.sqrt((ts if not np.isnan(ts) else 0) ** 2 + (unc if not np.isnan(unc) else 1.5) ** 2)
                tv = float(Tm[t])
                pm, ps = val(pmean, t, 2), val(pshare, t, 0)
                cp = val(cape, t, 0)
                sn = val(snowshare, t, 2)
                series.append({"t": t.strftime("%Y-%m-%dT%H:00Z"), "T": round(tv, 1), "lo": round(tv - half, 1), "hi": round(tv + half, 1),
                               "W": val(Wm, t), "G": val(Gm, t), "D": val(wdir, t, 0), "P": pm, "Pp": ps,
                               "C": val(cloud, t, 0), "night": bool(elev[t] < 0),
                               "snow": bool(sn is not None and sn >= 0.5) or bool(pm and pm > 0 and tv <= 0.3),
                               "storm": bool(cp is not None and cp >= 600 and ps is not None and ps >= 30),
                               "n": int(Tn.get(t, 0))})
        except Exception as e:      # grafy jsou doplněk, tabulková předpověď musí vyjít vždy
            log("  hodinové řady pro grafy se nepodařilo připravit: %s" % e)
            series = []
        result["sites"][key] = {"name": site["name"], "blocks_3h": hourly_json, "daily": daily_json, "hourly": series,
                                "station_last": station_last.get(key),
                                "models": sorted(per.keys()), "calibration_source": src}

    result["errors"] = STATE["errors"]
    result["calibration"] = {"%s+%d" % k: v for k, v in calib0.items()}
    md.append("Vítr a nárazy platí pro volné prostranství 10 m nad zemí (jako na stanici ČHMÚ); mezi stromy a u budov "
              "je průměrný vítr výrazně slabší. Srážky nejsou kalibrované, procento udává, kolik modelů srážky dává.")
    md.append("")
    if STATE["errors"]:
        md.append("Modely bez dat: " + "; ".join(sorted(set(e.split(" (")[0].split(":")[0] for e in STATE["errors"]))) + ".")
        md.append("")
    if calib_errors:
        md.append("Bez kalibrace (chybí historie předpovědí): "
                  + "; ".join(sorted(set(e.split(" (")[0].split(":")[0] for e in calib_errors))) + ".")
        md.append("")
    md.append("Zdroje: předpovědi Open-Meteo.com (CC BY 4.0), měření ČHMÚ (opendata.chmi.cz).")
    text = "\n".join(md) + "\n"
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "predpoved.md"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(outdir, "predpoved.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(text)
    log("\n" + text)
    log("dotazů na Open-Meteo: %d, váha: %.0f, zbývá: %s" % (STATE["om_calls"], STATE["om_cost"], STATE["om_remaining"]))
    cards = []
    try:
        import web
        cards = web.write_all(result, "docs")
        log("stránka: docs/index.html, obrázků pro Telegram: %d" % len(cards))
    except Exception as e:
        log("stránku s grafy se nepodařilo vytvořit: %s" % e)
    if not send_telegram_cards(cards):
        send_telegram(text)


def send_telegram_cards(cards):
    """Pošle do Telegramu obrázky s grafem (jeden na místo). Vrací True, když odešel aspoň jeden."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat or not cards:
        return False
    ok = False
    for path, cap in cards:
        try:
            with open(path, "rb") as f:
                r = requests.post("https://api.telegram.org/bot%s/sendPhoto" % token,
                                  data={"chat_id": chat, "caption": cap[:1000]}, files={"photo": f}, timeout=60)
            log("Telegram obrázek: HTTP %d" % r.status_code)
            ok = ok or r.status_code == 200
        except (requests.RequestException, OSError) as e:
            log("Telegram obrázek selhal: %s" % type(e).__name__)
    return ok


def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        return
    try:
        r = requests.post("https://api.telegram.org/bot%s/sendMessage" % token,
                          json={"chat_id": chat, "text": text[:3900]}, timeout=30)
        log("Telegram: HTTP %d" % r.status_code)
    except requests.RequestException as e:
        log("Telegram selhal: %s" % type(e).__name__)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["verify", "forecast", "both"])
    ap.add_argument("--start", default="2025-10-01")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    if a.mode in ("verify", "both"):
        run_verify(dt.date.fromisoformat(a.start), a.out)
    if a.mode in ("forecast", "both"):
        STATE["errors"] = []
        run_forecast(a.out)


if __name__ == "__main__":
    main()
