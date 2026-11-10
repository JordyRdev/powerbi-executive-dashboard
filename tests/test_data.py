"""Checks on the CSV files: keys, ranges, the shape of the story and the planted data-trust issues."""
from pathlib import Path

import pandas as pd
import pytest

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def t():
    d = {p.stem: pd.read_csv(p) for p in DATA.glob("*.csv")}
    d["fact_daily"]["date"] = pd.to_datetime(d["fact_daily"]["date"])
    d["fact_daily"]["month"] = d["fact_daily"]["date"].dt.to_period("M")
    for k in ("fact_monthly_segment", "fact_ledger"):
        d[k]["month"] = pd.to_datetime(d[k]["month"]).dt.to_period("M")
    d["load_log"]["date"] = pd.to_datetime(d["load_log"]["date"])
    d["load_log"]["loaded_at"] = pd.to_datetime(d["load_log"]["loaded_at"])
    return d


def monthly(t):
    f = t["fact_daily"]
    return f.groupby("month")[["net_revenue_eur", "volume_eur", "fraud_loss_eur"]].sum()


# ---------------------------------------------------------------- keys and shape

def test_files_and_row_counts(t):
    assert set(t) == {"dim_country", "dim_segment", "fact_daily", "fact_monthly_segment", "fact_ledger", "load_log"}
    assert len(t["dim_country"]) == 20
    assert len(t["dim_segment"]) == 5
    assert len(t["fact_daily"]) == 730 * 100 - 2
    assert len(t["fact_monthly_segment"]) == 120
    assert len(t["fact_ledger"]) == 120
    assert len(t["load_log"]) == 730 * 3


def test_keys_unique(t):
    assert t["dim_country"]["iso2"].is_unique
    assert t["dim_segment"]["segment_id"].is_unique
    assert not t["fact_daily"].duplicated(["date", "iso2", "segment_id"]).any()
    assert not t["fact_monthly_segment"].duplicated(["month", "segment_id"]).any()
    assert not t["fact_ledger"].duplicated(["month", "segment_id"]).any()
    assert not t["load_log"].duplicated(["date", "acquirer"]).any()


def test_foreign_keys(t):
    f = t["fact_daily"]
    assert f["iso2"].isin(t["dim_country"]["iso2"]).all()
    for k in ("fact_daily", "fact_monthly_segment", "fact_ledger"):
        assert t[k]["segment_id"].isin(t["dim_segment"]["segment_id"]).all()


def test_date_range(t):
    f = t["fact_daily"]
    assert f["date"].min() == pd.Timestamp("2024-11-01")
    assert f["date"].max() == pd.Timestamp("2026-10-31")


def test_hex_grid_has_no_overlap(t):
    c = t["dim_country"]
    assert not c.duplicated(["hex_col", "hex_row"]).any()
    assert set(c["region"]) == {"EU", "UK", "Nordics"}


def test_no_negative_values(t):
    f = t["fact_daily"]
    assert (f[["transactions", "volume_eur", "net_revenue_eur", "fraud_loss_eur"]] >= 0).all().all()


# ---------------------------------------------------------------- ranges and story

def test_monthly_revenue_range(t):
    rev = monthly(t)["net_revenue_eur"] / 1e6
    assert rev.min() > 26 and rev.max() < 49


def test_take_rate_about_two_percent(t):
    m = monthly(t)
    tr = m["net_revenue_eur"] / m["volume_eur"]
    assert tr.between(0.0190, 0.0210).all()


def test_fraud_range_with_one_bad_month(t):
    m = monthly(t)
    bps = m["fraud_loss_eur"] / m["volume_eur"] * 1e4
    bad = bps[bps > 6]
    assert list(bad.index.astype(str)) == ["2026-05"]
    assert bps.drop(bad.index).between(3, 6).all()
    g = t["fact_daily"][t["fact_daily"]["segment_id"] == 5].groupby("month")[["fraud_loss_eur", "volume_eur"]].sum()
    g_bps = g["fraud_loss_eur"] / g["volume_eur"] * 1e4
    assert g_bps.idxmax() == pd.Period("2026-05", "M")


def test_december_peak_and_quiet_january(t):
    rev = monthly(t)["net_revenue_eur"]
    for y in (2024, 2025):
        dec = rev[pd.Period(f"{y}-12", "M")]
        assert dec > rev[pd.Period(f"{y}-11", "M")]
        assert rev[pd.Period(f"{y + 1}-01", "M")] < dec


def test_plan_story(t):
    rev = monthly(t)["net_revenue_eur"]
    plan = t["fact_monthly_segment"].groupby("month")["plan_revenue_eur"].sum()
    ahead = rev >= plan
    assert not ahead[pd.Period("2025-01", "M"):pd.Period("2025-06", "M")].any(), "behind plan in early 2025"
    assert ahead.iloc[-3:].all(), "last three months at or above plan"
    assert not ahead.iloc[-4], "the run starts three months ago"


def test_gaming_shrinks_last_two_months(t):
    g = t["fact_daily"][t["fact_daily"]["segment_id"] == 5].groupby("month")["volume_eur"].sum()
    assert g.iloc[-1] < g.iloc[-2] < g.iloc[-3]


def test_country_sizes(t):
    v = t["fact_daily"].groupby("iso2")["volume_eur"].sum()
    assert v.idxmax() == "DE"
    assert v.idxmin() == "IS"


# ---------------------------------------------------------------- planted data-trust issues

def test_reconciliation_break_only_in_march_2026(t):
    f = t["fact_daily"]
    daily = f.groupby(["month", "segment_id"])["net_revenue_eur"].sum()
    led = t["fact_ledger"].set_index(["month", "segment_id"])["ledger_revenue_eur"]
    gap = (daily - led).round(2)
    breaks = gap[gap.abs() >= 1]
    assert len(breaks) == 1
    (month, seg), value = next(iter(breaks.items()))
    assert str(month) == "2026-03"
    assert 37_000 < value < 39_000


def test_two_missing_rows_in_august_2026(t):
    f = t["fact_daily"]
    rows = f.groupby("month").size()
    days = pd.Series(rows.index.days_in_month, index=rows.index)
    missing = days * 100 - rows
    assert missing[missing > 0].to_dict() == {pd.Period("2026-08", "M"): 2}


def test_one_pending_file_on_last_day(t):
    log = t["load_log"]
    pending = log[log["status"] == "pending"]
    assert len(pending) == 1
    assert pending["date"].iloc[0] == pd.Timestamp("2026-10-31")
    assert pending["loaded_at"].isna().all()
    assert set(log["status"]) == {"loaded", "pending"}


def test_latest_load_passes_freshness(t):
    last = t["load_log"]["loaded_at"].max()
    assert last == pd.Timestamp("2026-11-01 06:02:00")
    assert last < pd.Timestamp("2026-11-01 07:00:00")


def test_expected_kpis_file():
    exp = pd.read_csv(Path(__file__).with_name("expected_kpis.csv"))
    assert {"kpi", "period", "value", "tolerance"} <= set(exp.columns)
    assert 12 <= len(exp) <= 25
