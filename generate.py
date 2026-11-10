"""Builds the synthetic Halcyon Pay data, the expected KPI values and the page backgrounds.

    python generate.py

Writes data/*.csv, tests/expected_kpis.csv, design/backgrounds/*.png and a copy of the
backgrounds into the report's registered resources. Seed 2026, so every run gives the same files.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SEED = 2026

START, END = "2024-11-01", "2026-10-31"

# iso2, country, region, hex_col, hex_row, share of volume (relative)
COUNTRIES = [
    ("IS", "Iceland", "Nordics", 0, 0, 0.3),
    ("NO", "Norway", "Nordics", 3, 0, 2.5),
    ("SE", "Sweden", "Nordics", 4, 0, 4.0),
    ("FI", "Finland", "Nordics", 5, 0, 2.0),
    ("IE", "Ireland", "EU", 0, 1, 2.5),
    ("GB", "United Kingdom", "UK", 1, 1, 15.0),
    ("DK", "Denmark", "Nordics", 3, 1, 3.0),
    ("NL", "Netherlands", "EU", 2, 2, 7.0),
    ("DE", "Germany", "EU", 3, 2, 21.0),
    ("PL", "Poland", "EU", 4, 2, 5.0),
    ("FR", "France", "EU", 1, 3, 12.0),
    ("BE", "Belgium", "EU", 2, 3, 3.5),
    ("CZ", "Czechia", "EU", 3, 3, 2.0),
    ("AT", "Austria", "EU", 4, 3, 3.0),
    ("PT", "Portugal", "EU", 0, 4, 2.0),
    ("ES", "Spain", "EU", 1, 4, 8.0),
    ("IT", "Italy", "EU", 3, 4, 8.0),
    ("HU", "Hungary", "EU", 4, 4, 1.2),
    ("RO", "Romania", "EU", 5, 4, 1.5),
    ("GR", "Greece", "EU", 4, 5, 1.2),
]

# segment_id, name, volume share, take-rate factor, avg ticket €, fraud bps, merchant share
SEGMENTS = [
    (1, "Marketplaces", 0.255, 0.90, 45.0, 3.5, 0.30),
    (2, "SaaS & subscriptions", 0.205, 1.20, 30.0, 2.5, 0.25),
    (3, "Travel & mobility", 0.165, 1.05, 80.0, 5.0, 0.12),
    (4, "Retail chains", 0.150, 0.80, 35.0, 3.0, 0.18),
    (5, "Gaming", 0.225, 1.10, 20.0, 7.0, 0.15),
]

ACQUIRERS = ["acq_north", "acq_central", "acq_south"]

# Monthly net revenue in € million, Nov 2024 .. Oct 2026
REVENUE_M = [29.0, 33.5, 27.0, 27.5, 29.5, 30.0, 31.0, 31.5, 31.0, 32.0, 33.5, 35.0,
             34.5, 39.0, 32.0, 32.5, 35.0, 36.0, 37.5, 39.0, 38.5, 41.0, 44.0, 48.2]
# Actual / plan for revenue: behind in 2025, ahead for the last three months
PLAN_RATIO = [0.95, 0.94, 0.93, 0.94, 0.95, 0.95, 0.96, 0.96, 0.97, 0.97, 0.98, 0.98,
              0.99, 0.99, 0.98, 0.985, 0.99, 0.99, 0.995, 0.99, 0.99, 1.02, 1.03, 1.048]
# Fraud loss in bps for the whole book (May 2026 gets a Gaming spike on top)
FRAUD_BPS = [4.4, 4.9, 3.9, 3.7, 4.2, 4.5, 4.0, 3.8, 4.3, 4.6, 4.1, 4.4,
             4.7, 5.2, 4.0, 3.9, 4.3, 4.4, 4.6, 4.2, 4.5, 4.3, 4.8, 4.1]
PLAN_TAKE_RATE = 0.021
FRAUD_SPIKE = ("2026-05", 5, 4.5)  # month, segment, multiplier
GAMING_SHRINK = {"2026-09": 0.85, "2026-10": 0.75}
MERCHANTS_SEP, MERCHANTS_OCT, MERCHANTS_START = 36_308, 38_214, 24_000

RECON_BREAK = ("2026-03", 2, 38_412.60)  # ledger lower than daily revenue by this amount
MISSING_ROWS = [("2026-08-14", "PL", 3), ("2026-08-22", "NL", 5)]
PENDING_ACQUIRER = "acq_south"
LAST_LOAD = "2026-11-01 06:02:00"


def build(rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    months = pd.period_range(START[:7], END[:7], freq="M")
    dates = pd.date_range(START, END, freq="D")
    n_m = len(months)

    dim_country = pd.DataFrame(
        [(c[0], c[1], c[2], c[3], c[4]) for c in COUNTRIES],
        columns=["iso2", "country", "region", "hex_col", "hex_row"])
    dim_segment = pd.DataFrame(
        [(s[0], s[1], i + 1) for i, s in enumerate(SEGMENTS)], columns=["segment_id", "segment", "sort"])

    c_share = np.array([c[5] for c in COUNTRIES])
    c_share = c_share / c_share.sum()
    seg_ids = np.array([s[0] for s in SEGMENTS])
    seg_vol = np.array([s[2] for s in SEGMENTS])
    seg_tr = np.array([s[3] for s in SEGMENTS])
    seg_ticket = np.array([s[4] for s in SEGMENTS])
    seg_fraud = np.array([s[5] for s in SEGMENTS])

    take_rate = 0.0200 + rng.normal(0, 0.0003, n_m).clip(-0.0005, 0.0005)
    take_rate[-2], take_rate[-1] = 0.0194, 0.0200
    dow_w = np.array([1.00, 1.00, 1.02, 1.05, 1.12, 1.00, 0.85])

    rows = []
    for mi, m in enumerate(months):
        key = str(m)
        shares = seg_vol.copy()
        if key in GAMING_SHRINK:
            shares[4] *= GAMING_SHRINK[key]
        shares = shares / shares.sum()
        tr_seg = seg_tr / (shares * seg_tr).sum() * take_rate[mi]
        fraud_seg = seg_fraud / (shares * seg_fraud).sum() * FRAUD_BPS[mi]
        if key == FRAUD_SPIKE[0]:
            fraud_seg[FRAUD_SPIKE[1] - 1] *= FRAUD_SPIKE[2]

        volume_m = REVENUE_M[mi] * 1e6 / take_rate[mi]
        m_dates = dates[(dates.year == m.year) & (dates.month == m.month)]
        day_w = dow_w[m_dates.dayofweek] * (1 + rng.normal(0, 0.03, len(m_dates)))
        day_w = day_w / day_w.sum()

        # date x country x segment, multiplicative noise, then rescaled to the month total
        base = (day_w[:, None, None] * c_share[None, :, None] * shares[None, None, :])
        noise = rng.lognormal(0, 0.06, base.shape)
        vol = base * noise
        vol = vol / vol.sum() * volume_m
        d_idx, c_idx, s_idx = np.indices(vol.shape)
        v = vol.ravel()
        rev = v * tr_seg[s_idx.ravel()] * rng.normal(1, 0.01, v.size)
        fraud = v * fraud_seg[s_idx.ravel()] / 1e4 * rng.lognormal(0, 0.25, v.size) / np.exp(0.25 ** 2 / 2)
        trx = np.round(v / seg_ticket[s_idx.ravel()] * rng.normal(1, 0.02, v.size)).astype(int)
        rows.append(pd.DataFrame({
            "date": m_dates[d_idx.ravel()],
            "iso2": dim_country["iso2"].to_numpy()[c_idx.ravel()],
            "segment_id": seg_ids[s_idx.ravel()],
            "transactions": trx,
            "volume_eur": np.round(v, 2),
            "net_revenue_eur": np.round(rev, 2),
            "fraud_loss_eur": np.round(fraud, 2),
        }))
    fact = pd.concat(rows, ignore_index=True)

    # Planted issue: two country x segment days missing in August 2026
    drop = pd.Series(False, index=fact.index)
    for d, iso, seg in MISSING_ROWS:
        drop |= (fact["date"] == d) & (fact["iso2"] == iso) & (fact["segment_id"] == seg)
    assert drop.sum() == len(MISSING_ROWS)
    fact = fact[~drop].reset_index(drop=True)

    fact["month"] = fact["date"].dt.to_period("M")
    rev_ms = fact.groupby(["month", "segment_id"])["net_revenue_eur"].sum()
    vol_ms = fact.groupby(["month", "segment_id"])["volume_eur"].sum()
    rev_m = fact.groupby("month")["net_revenue_eur"].sum()

    # Merchants: smooth growth, Sep and Oct 2026 pinned
    growth = np.geomspace(MERCHANTS_START, MERCHANTS_SEP, n_m - 1)
    merch_total = np.append(np.round(growth), MERCHANTS_OCT).astype(int)
    merch_ratio = np.linspace(0.95, 0.975, n_m)
    merch_ratio[-1] = 0.93

    monthly = []
    for mi, m in enumerate(months):
        key = str(m)
        m_share = np.array([s[6] for s in SEGMENTS])
        if key in GAMING_SHRINK:
            m_share[4] *= GAMING_SHRINK[key]
        m_share = m_share / m_share.sum()
        merch = np.floor(merch_total[mi] * m_share).astype(int)
        merch[0] += merch_total[mi] - merch.sum()
        # plan uses the base segment mix, so a shrinking segment shows as behind plan
        plan_total = rev_m[m] / PLAN_RATIO[mi]
        plan_rev = plan_total * (seg_vol * seg_tr) / (seg_vol * seg_tr).sum()
        for si, sid in enumerate(seg_ids):
            monthly.append({
                "month": m.start_time,
                "segment_id": sid,
                "active_merchants": int(merch[si]),
                "plan_revenue_eur": round(plan_rev[si], 2),
                "plan_volume_eur": round(plan_rev[si] / PLAN_TAKE_RATE, 2),
                "plan_merchants": int(round(merch[si] / merch_ratio[mi])),
            })
    fact_monthly = pd.DataFrame(monthly)

    # Ledger: sum in integer cents so it matches the model to the cent
    cents = (fact["net_revenue_eur"] * 100).round().astype(np.int64)
    ledger = cents.groupby([fact["month"], fact["segment_id"]]).sum().reset_index(name="cents")
    brk = (ledger["month"] == pd.Period(RECON_BREAK[0], "M")) & (ledger["segment_id"] == RECON_BREAK[1])
    ledger.loc[brk, "cents"] -= int(round(RECON_BREAK[2] * 100))
    fact_ledger = pd.DataFrame({
        "month": ledger["month"].dt.start_time,
        "segment_id": ledger["segment_id"],
        "ledger_revenue_eur": ledger["cents"] / 100,
    })

    # Load log: one file per acquirer per day, expected 05:30 next morning
    trx_day = fact.groupby("date")["transactions"].sum()
    log = []
    last_day = dates[-1]
    for d in dates:
        for acq in ACQUIRERS:
            expected = d + pd.Timedelta(days=1, hours=5, minutes=30)
            minutes = int(np.clip(rng.normal(12, 7), 1, 28))
            if rng.random() < 0.01:  # an occasional slow file, still loaded
                minutes = int(rng.integers(40, 95))
            loaded = expected + pd.Timedelta(minutes=minutes)
            status = "loaded"
            n_rows = int(trx_day[d] / 3 * rng.normal(1, 0.05))
            if d == last_day:
                if acq == PENDING_ACQUIRER:
                    loaded, status, n_rows = pd.NaT, "pending", None
                elif acq == "acq_central":
                    loaded = pd.Timestamp(LAST_LOAD)
                else:
                    loaded = pd.Timestamp("2026-11-01 05:48:00")
            log.append({
                "date": d, "acquirer": acq, "file_name": f"{acq}_{d:%Y%m%d}.csv",
                "expected_at": expected, "loaded_at": loaded, "rows": n_rows, "status": status,
            })
    load_log = pd.DataFrame(log)
    load_log["rows"] = load_log["rows"].astype("Int64")

    return {
        "dim_country": dim_country,
        "dim_segment": dim_segment,
        "fact_daily": fact.drop(columns="month"),
        "fact_monthly_segment": fact_monthly,
        "fact_ledger": fact_ledger,
        "load_log": load_log,
    }


def write_csv(tables: dict[str, pd.DataFrame]) -> None:
    DATA.mkdir(exist_ok=True)
    fmt = {"fact_daily": "%Y-%m-%d", "fact_monthly_segment": "%Y-%m-%d", "fact_ledger": "%Y-%m-%d"}
    for name, df in tables.items():
        out = df.copy()
        for col in out.columns:
            if pd.api.types.is_datetime64_any_dtype(out[col]):
                f = "%Y-%m-%d" if col in ("date", "month") else "%Y-%m-%d %H:%M:%S"
                out[col] = out[col].dt.strftime(f).fillna("")
        out.to_csv(DATA / f"{name}.csv", index=False, float_format="%.2f", lineterminator="\n")
        print(f"  data/{name}.csv  {len(out):>6} rows")


def expected_kpis(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """KPIs computed straight from the CSV tables, independent of the model."""
    f = t["fact_daily"].copy()
    f["month"] = f["date"].dt.to_period("M")
    for col in ("net_revenue_eur", "volume_eur", "fraud_loss_eur"):
        f[col] = (f[col] * 100).round().astype(np.int64)  # cents, so sums are exact
    ms = t["fact_monthly_segment"].copy()
    ms["month"] = ms["month"].dt.to_period("M")
    led = t["fact_ledger"].copy()
    led["month"] = led["month"].dt.to_period("M")
    by_m = f.groupby("month")[["net_revenue_eur", "volume_eur", "transactions", "fraud_loss_eur"]].sum()
    by_m[["net_revenue_eur", "volume_eur", "fraud_loss_eur"]] = by_m[["net_revenue_eur", "volume_eur", "fraud_loss_eur"]] / 100
    plan = ms.groupby("month")[["plan_revenue_eur", "active_merchants"]].sum()

    def p(s):
        return pd.Period(s, "M")

    o26, s26, o25 = p("2026-10"), p("2026-09"), p("2025-10")
    rows = []

    def add(kpi, period, value, tol):
        rows.append({"kpi": kpi, "period": period, "value": value, "tolerance": tol})

    for per, lbl in [(o26, "Oct 2026"), (o25, "Oct 2025")]:
        r = by_m.loc[per]
        add("net_revenue", lbl, round(r.net_revenue_eur, 2), 0.01)
        add("volume", lbl, round(r.volume_eur, 2), 0.01)
        add("transactions", lbl, int(r.transactions), 0)
        add("take_rate", lbl, round(r.net_revenue_eur / r.volume_eur, 8), 1e-7)
        add("active_merchants", lbl, int(plan.loc[per].active_merchants), 0)
        add("fraud_loss_bps", lbl, round(r.fraud_loss_eur / r.volume_eur * 1e4, 6), 1e-5)
    add("net_revenue_mom_pct", "Oct 2026",
        round(by_m.loc[o26].net_revenue_eur / by_m.loc[s26].net_revenue_eur - 1, 8), 1e-7)
    add("net_revenue_vs_plan_pct", "Oct 2026",
        round(by_m.loc[o26].net_revenue_eur / plan.loc[o26].plan_revenue_eur - 1, 8), 1e-7)
    ytd = by_m.loc[p("2026-01"):o26].net_revenue_eur.sum()
    add("net_revenue_ytd", "Oct 2026", round(ytd, 2), 0.01)
    add("net_revenue_yoy_pct", "Oct 2026",
        round(by_m.loc[o26].net_revenue_eur / by_m.loc[o25].net_revenue_eur - 1, 8), 1e-7)
    gap = f.groupby("month").net_revenue_eur.sum() / 100 - led.groupby("month").ledger_revenue_eur.sum()
    add("reconciliation_gap", "Mar 2026", round(gap.loc[p("2026-03")], 2), 0.01)
    add("reconciliation_gap", "Oct 2026", round(gap.loc[o26], 2), 0.01)
    aug = f[f["month"] == p("2026-08")]
    add("completeness_pct", "Aug 2026", round(len(aug) / (20 * 5 * 31), 8), 1e-7)
    add("net_revenue_no_month_selected", "latest month", round(by_m.loc[o26].net_revenue_eur, 2), 0.01)
    add("late_files", "latest", int((t["load_log"]["status"] == "pending").sum()), 0)
    add("last_load", "latest", t["load_log"]["loaded_at"].max().strftime("%Y-%m-%d %H:%M"), 0)
    return pd.DataFrame(rows)


MEASURE_FOR = {
    "net_revenue": "[Net Revenue CM]",
    "volume": "[Volume CM]",
    "transactions": "[Transactions CM]",
    "take_rate": "[Take Rate CM]",
    "active_merchants": "[Active Merchants CM]",
    "fraud_loss_bps": "[Fraud Loss bps CM]",
    "net_revenue_mom_pct": "[Net Revenue MoM %]",
    "net_revenue_vs_plan_pct": "[Net Revenue vs Plan %]",
    "net_revenue_ytd": "[Net Revenue YTD]",
    "net_revenue_yoy_pct": "[Net Revenue YoY %]",
    "reconciliation_gap": "[Reconciliation Gap CM]",
    "completeness_pct": "[Completeness CM]",
    "net_revenue_no_month_selected": "[Net Revenue CM]",
    "late_files": "[Late Files]",
    "last_load": 'FORMAT ( [Last Load At], "yyyy-mm-dd hh:nn", "en-US" )',
}


def validation_queries(exp: pd.DataFrame) -> str:
    """One EVALUATE per expected KPI. Each returns expected, actual and a pass flag."""
    rows = []
    for r in exp.itertuples():
        measure = MEASURE_FOR[r.kpi]
        if r.period[:3] in ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"):
            actual = f'CALCULATE ( {measure}, DimDate[Month] = "{r.period}" )'
        else:
            actual = measure
        if r.kpi == "last_load":
            expected, check = f'"{r.value}"', "_actual = _expected"
        else:
            expected, check = f"{float(r.value)!r}", f"ABS ( _actual - _expected ) <= {float(r.tolerance)!r}"
        rows.append((r.kpi, r.period, actual, expected, check))
    out = ["// Validation queries: the model against tests/expected_kpis.csv.",
           "// Run each EVALUATE against the open model. Every row must return pass = TRUE.",
           "// Written by generate.py from expected_kpis.csv; do not edit by hand.", ""]
    for kpi, period, actual, expected, check in rows:
        out += [f"// {kpi}, {period}",
                "EVALUATE",
                f"VAR _expected = {expected}",
                f"VAR _actual = {actual}",
                "RETURN",
                f'    ROW ( "kpi", "{kpi}", "period", "{period}", "expected", _expected, "actual", _actual, "pass", {check} )',
                ""]
    return "\n".join(out)


def main() -> None:
    rng = np.random.default_rng(SEED)
    print("Data")
    tables = build(rng)
    write_csv(tables)
    exp = expected_kpis(tables)
    exp.to_csv(ROOT / "tests" / "expected_kpis.csv", index=False, lineterminator="\n")
    print(f"  tests/expected_kpis.csv  {len(exp)} KPIs")
    (ROOT / "tests" / "validation_queries.dax").write_text(validation_queries(exp), encoding="utf-8")
    print("  tests/validation_queries.dax")

    print("Backgrounds")
    sys.path.insert(0, str(ROOT / "design"))
    import backgrounds  # noqa: E402

    out = ROOT / "design" / "backgrounds"
    files = backgrounds.draw_all(out)
    res = ROOT / "powerbi" / "Halcyon_Executive.Report" / "StaticResources" / "RegisteredResources"
    if res.parent.parent.exists():
        res.mkdir(parents=True, exist_ok=True)
        for fpath in files:
            shutil.copy2(fpath, res / fpath.name)
    for fpath in files:
        print(f"  {fpath.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
