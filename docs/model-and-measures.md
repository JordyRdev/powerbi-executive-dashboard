# Model and measures

Import mode, one star schema per grain. The CSVs are loaded as they are: Power Query only reads the file and sets types.

## Tables

| Table | Source | Grain | Visible fields |
|---|---|---|---|
| `DimCountry` | `data/dim_country.csv` | Country (20) | iso2, country, region |
| `DimSegment` | `data/dim_segment.csv` | Merchant segment (5) | segment |
| `FactDaily` | `data/fact_daily.csv` | Date × country × segment | none (all hidden) |
| `FactMonthlySegment` | `data/fact_monthly_segment.csv` | Month × segment | none (all hidden) |
| `FactLedger` | `data/fact_ledger.csv` | Month × segment | none (all hidden) |
| `LoadLog` | `data/load_log.csv` | Date × acquirer | date, acquirer, file_name, expected_at, loaded_at, status |
| `DimDate` | DAX | Day, 1 Nov 2024 – 31 Oct 2026 | Date, Month start, Month, Year, IsLatestMonth |
| `TrendMonth` | DAX | Month (chart axis only) | Month |
| `DQ_Checks` | DAX | Data-trust check (4) | check, description |
| `_Measures` | DAX | Holds the measures | none (all hidden) |

Fact columns and keys are hidden, so report authors only see measures and dimension fields. `LoadLog` stays visible because the Data trust page lists its rows.

### Calculated tables

**DimDate**

```dax
VAR _first = MIN ( FactDaily[date] )
VAR _last = MAX ( FactDaily[date] )
RETURN
    ADDCOLUMNS (
        CALENDAR ( DATE ( YEAR ( _first ), MONTH ( _first ), 1 ), EOMONTH ( _last, 0 ) ),
        "Month start", DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ),
        "Month", FORMAT ( [Date], "mmm yyyy", "en-US" ),
        "Month key", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
        "Year", YEAR ( [Date] ),
        "IsLatestMonth", EOMONTH ( [Date], 0 ) = EOMONTH ( _last, 0 )
    )
```

**TrendMonth**

```dax
SELECTCOLUMNS (
    SUMMARIZE ( DimDate, DimDate[Month start], DimDate[Month key] ),
    "Month start", DimDate[Month start],
    "Month key", DimDate[Month key],
    "Month", FORMAT ( DimDate[Month start], "mmm yy", "en-US" )
)
```

**DQ_Checks**

```dax
DATATABLE (
    "check_id", INTEGER,
    "check", STRING,
    "description", STRING,
    "sort", INTEGER,
    {
        { 1, "Freshness", "Latest file loaded before 07:00 CET on the day after the last business date", 1 },
        { 2, "Reconciliation", "Daily revenue equals the finance ledger for the month, within 1 euro", 2 },
        { 3, "Completeness", "Every country and segment has a row for every day of the month", 3 },
        { 4, "Late files", "No acquirer file is still pending", 4 }
    }
)
```

**_Measures**

```dax
ROW ( "x", 0 )
```

`TrendMonth` has no relationship. It is the axis of the 12-month chart, so the month slicer can pick the end month without cutting the chart down to one bar.

## Relationships

All one-to-many, single direction, from dimension to fact. Monthly facts join `DimDate` on the month start date.

| From (many) | To (one) |
|---|---|
| `FactDaily[date]` | `DimDate[Date]` |
| `FactDaily[iso2]` | `DimCountry[iso2]` |
| `FactDaily[segment_id]` | `DimSegment[segment_id]` |
| `FactMonthlySegment[month]` | `DimDate[Date]` |
| `FactMonthlySegment[segment_id]` | `DimSegment[segment_id]` |
| `FactLedger[month]` | `DimDate[Date]` |
| `FactLedger[segment_id]` | `DimSegment[segment_id]` |
| `LoadLog[date]` | `DimDate[Date]` |

## How "current month" works

Every `CM` measure reads `MAX ( DimDate[Month start] )`. With one month picked in the slicer that is the selected month; with nothing picked it is the latest month in the data. The measure then removes all date filters and filters that one month. No date is written into any measure.

Plan values are set per segment, not per country. When a region is selected, the plan measures that compare against country-level actuals (revenue, volume) return blank instead of a misleading gap.

## Measures

### KPI

**Net Revenue** – Net revenue in euro: fees kept after interchange and scheme costs. (format `€#,0`)

```dax
SUM ( FactDaily[net_revenue_eur] )
```

**Volume** – Total payment volume processed, in euro. (format `€#,0`)

```dax
SUM ( FactDaily[volume_eur] )
```

**Transactions** – Number of card and wallet transactions. (format `#,0`)

```dax
SUM ( FactDaily[transactions] )
```

**Fraud Loss** – Fraud losses written off, in euro. (format `€#,0`)

```dax
SUM ( FactDaily[fraud_loss_eur] )
```

**Take Rate** – Net revenue divided by volume. (format `0.00%`)

```dax
DIVIDE ( [Net Revenue], [Volume] )
```

**Fraud Loss bps** – Fraud loss divided by volume, in basis points. (format `0.0`)

```dax
DIVIDE ( [Fraud Loss], [Volume] ) * 10000
```

**Active Merchants** – Merchants with at least one transaction in the month. For a period longer than a month, the last month is shown. (format `#,0`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( SUM ( FactMonthlySegment[active_merchants] ), DimDate[Month start] = _m )
```

**Net Revenue CM** – Net Revenue in the selected month. With no month selected, the latest month. (format `€#,0.0,,\M`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Net Revenue], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Net Revenue PM** – Net Revenue in the month before the selected month. (format `€#,0.0,,\M`)

```dax
VAR _m = EDATE ( MAX ( DimDate[Month start] ), -1 )
RETURN
    CALCULATE ( [Net Revenue], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Volume CM** – Volume in the selected month. With no month selected, the latest month. (format `€#,0.00,,,\B`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Volume], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Volume PM** – Volume in the month before the selected month. (format `€#,0.00,,,\B`)

```dax
VAR _m = EDATE ( MAX ( DimDate[Month start] ), -1 )
RETURN
    CALCULATE ( [Volume], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Transactions CM** – Transactions in the selected month. With no month selected, the latest month. (format `#,0`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Transactions], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Transactions PM** – Transactions in the month before the selected month. (format `#,0`)

```dax
VAR _m = EDATE ( MAX ( DimDate[Month start] ), -1 )
RETURN
    CALCULATE ( [Transactions], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Take Rate CM** – Take Rate in the selected month. With no month selected, the latest month. (format `0.00%`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Take Rate], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Take Rate PM** – Take Rate in the month before the selected month. (format `0.00%`)

```dax
VAR _m = EDATE ( MAX ( DimDate[Month start] ), -1 )
RETURN
    CALCULATE ( [Take Rate], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Active Merchants CM** – Active Merchants in the selected month. With no month selected, the latest month. (format `#,0`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Active Merchants], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Active Merchants PM** – Active Merchants in the month before the selected month. (format `#,0`)

```dax
VAR _m = EDATE ( MAX ( DimDate[Month start] ), -1 )
RETURN
    CALCULATE ( [Active Merchants], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Fraud Loss bps CM** – Fraud Loss bps in the selected month. With no month selected, the latest month. (format `0.0 \b\p\s`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Fraud Loss bps], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Fraud Loss bps PM** – Fraud Loss bps in the month before the selected month. (format `0.0 \b\p\s`)

```dax
VAR _m = EDATE ( MAX ( DimDate[Month start] ), -1 )
RETURN
    CALCULATE ( [Fraud Loss bps], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Net Revenue MoM %** – Change in net revenue against the previous month. (format `+0.0%;-0.0%;0.0%`)

```dax
VAR _cur = [Net Revenue CM]
VAR _prev = [Net Revenue PM]
RETURN
    DIVIDE ( _cur - _prev, _prev )
```

**Volume MoM %** – Change in volume against the previous month. (format `+0.0%;-0.0%;0.0%`)

```dax
VAR _cur = [Volume CM]
VAR _prev = [Volume PM]
RETURN
    DIVIDE ( _cur - _prev, _prev )
```

**Transactions MoM %** – Change in transactions against the previous month. (format `+0.0%;-0.0%;0.0%`)

```dax
VAR _cur = [Transactions CM]
VAR _prev = [Transactions PM]
RETURN
    DIVIDE ( _cur - _prev, _prev )
```

**Take Rate MoM bps** – Change in take rate against the previous month, in basis points. (format `+0;-0;0`)

```dax
( [Take Rate CM] - [Take Rate PM] ) * 10000
```

**Active Merchants MoM** – Change in active merchants against the previous month. (format `+#,0;-#,0;0`)

```dax
[Active Merchants CM] - [Active Merchants PM]
```

**Active Merchants MoM %** – Change in active merchants against the previous month, in percent. (format `+0.0%;-0.0%;0.0%`)

```dax
VAR _cur = [Active Merchants CM]
VAR _prev = [Active Merchants PM]
RETURN
    DIVIDE ( _cur - _prev, _prev )
```

**Fraud Loss bps MoM** – Change in fraud loss against the previous month, in basis points. (format `+0.0;-0.0;0.0`)

```dax
[Fraud Loss bps CM] - [Fraud Loss bps PM]
```

**Net Revenue YTD** – Net revenue from 1 January to the end of the selected month. (format `€#,0.0,,\M`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE (
        [Net Revenue],
        REMOVEFILTERS ( DimDate ),
        DimDate[Year] = YEAR ( _m ),
        DimDate[Month start] <= _m
    )
```

**Net Revenue PY** – Net revenue in the same month one year earlier. (format `€#,0.0,,\M`)

```dax
VAR _m = EDATE ( MAX ( DimDate[Month start] ), -12 )
RETURN
    CALCULATE ( [Net Revenue], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Net Revenue YoY %** – Change in net revenue against the same month last year. (format `+0.0%;-0.0%;0.0%`)

```dax
VAR _cur = [Net Revenue CM]
VAR _prev = [Net Revenue PY]
RETURN
    DIVIDE ( _cur - _prev, _prev )
```

### KPI / Tooltips

**Tip Net Revenue** – Tooltip text for the net revenue tile.

```dax
"Net revenue: fees kept after interchange and scheme costs, for the selected month."
```

**Tip Volume** – Tooltip text for the volume tile.

```dax
"Payment volume: value of all approved payments, for the selected month."
```

**Tip Take Rate** – Tooltip text for the take rate tile.

```dax
"Take rate: net revenue divided by payment volume. Target from the plan."
```

**Tip Active Merchants** – Tooltip text for the active merchants tile.

```dax
"Active merchants: merchants with at least one payment in the month. Not split by country."
```

**Tip Fraud Loss** – Tooltip text for the fraud loss tile.

```dax
"Fraud loss: losses written off divided by volume, in basis points. Limit 10 bps."
```

### Plan

**Plan Revenue** – Net revenue plan for the months in context. (format `€#,0`)

```dax
SUM ( FactMonthlySegment[plan_revenue_eur] )
```

**Plan Volume** – Volume plan for the months in context. (format `€#,0`)

```dax
SUM ( FactMonthlySegment[plan_volume_eur] )
```

**Plan Merchants** – Active merchant plan for the last month in context. (format `#,0`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( SUM ( FactMonthlySegment[plan_merchants] ), DimDate[Month start] = _m )
```

**Plan Revenue CM** – Net revenue plan for the selected month. Blank when a region is selected, because the plan is set per segment only. (format `€#,0.0,,\M`)

```dax
-- plan is set per segment, not per country
IF (
    NOT ISFILTERED ( DimCountry ),
    VAR _m = MAX ( DimDate[Month start] )
    RETURN
        CALCULATE ( [Plan Revenue], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
)
```

**Plan Volume CM** – Volume plan for the selected month. Blank when a region is selected. (format `€#,0.00,,,\B`)

```dax
-- plan is set per segment, not per country
IF (
    NOT ISFILTERED ( DimCountry ),
    VAR _m = MAX ( DimDate[Month start] )
    RETURN
        CALCULATE ( [Plan Volume], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
)
```

**Plan Take Rate CM** – Planned take rate for the selected month (plan revenue divided by plan volume). (format `0.00%`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE (
        DIVIDE ( [Plan Revenue], [Plan Volume] ),
        REMOVEFILTERS ( DimDate ),
        DimDate[Month start] = _m
    )
```

**Plan Merchants CM** – Active merchant plan for the selected month. (format `#,0`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Plan Merchants], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Net Revenue vs Plan %** – Net revenue against plan for the selected month. (format `+0.0%;-0.0%;0.0%`)

```dax
VAR _plan = [Plan Revenue CM]
RETURN
    IF ( NOT ISBLANK ( _plan ), DIVIDE ( [Net Revenue CM], _plan ) - 1 )
```

**Volume vs Plan %** – Volume against plan for the selected month. (format `+0.0%;-0.0%;0.0%`)

```dax
VAR _plan = [Plan Volume CM]
RETURN
    IF ( NOT ISBLANK ( _plan ), DIVIDE ( [Volume CM], _plan ) - 1 )
```

**Take Rate vs Plan %** – Take rate against the planned take rate. (format `+0.0%;-0.0%;0.0%`)

```dax
VAR _plan = [Plan Take Rate CM]
RETURN
    IF ( NOT ISBLANK ( _plan ), DIVIDE ( [Take Rate CM], _plan ) - 1 )
```

**Active Merchants vs Plan %** – Active merchants against plan for the selected month. (format `+0.0%;-0.0%;0.0%`)

```dax
VAR _plan = [Plan Merchants CM]
RETURN
    IF ( NOT ISBLANK ( _plan ), DIVIDE ( [Active Merchants CM], _plan ) - 1 )
```

**Fraud Limit bps** – Agreed fraud loss limit, in basis points. (format `0 \b\p\s`)

```dax
10
```

**Fraud vs Limit %** – Fraud loss as a share of the limit. (format `0%`)

```dax
DIVIDE ( [Fraud Loss bps CM], [Fraud Limit bps] )
```

### Trend

**Selected Month Start** – First day of the selected month, or of the latest month when none is selected. (format `mmm yyyy`)

```dax
MAX ( DimDate[Month start] )
```

**Page Title Overview** – Header title for the overview page.

```dax
VAR _m = MAX ( DimDate[Month start] )
VAR _last = [Last Data Date]
RETURN
    "" & FORMAT ( _m, "mmmm yyyy", "en-US" )
        & IF ( _last < EOMONTH ( _m, 0 ), ", month to date", ", full month" )
```

**Page Title Segments** – Header title for the segments page.

```dax
VAR _m = MAX ( DimDate[Month start] )
VAR _last = [Last Data Date]
RETURN
    "Segments · " & FORMAT ( _m, "mmmm yyyy", "en-US" )
        & IF ( _last < EOMONTH ( _m, 0 ), ", month to date", ", full month" )
```

**Page Title Trust** – Header title for the trust page.

```dax
VAR _m = MAX ( DimDate[Month start] )
VAR _last = [Last Data Date]
RETURN
    "Data trust · " & FORMAT ( _m, "mmmm yyyy", "en-US" )
        & IF ( _last < EOMONTH ( _m, 0 ), ", month to date", ", full month" )
```

**Plan Status Line** – One line on how many months in a row net revenue has been at or above plan.

```dax
VAR _m = MAX ( DimDate[Month start] )
VAR _months =
    ADDCOLUMNS (
        FILTER ( ALL ( DimDate[Month start] ), DimDate[Month start] <= _m ),
        "@ahead",
            VAR _mm = DimDate[Month start]
            VAR _a = CALCULATE ( [Net Revenue], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _mm )
            VAR _p = CALCULATE ( [Plan Revenue], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _mm )
            RETURN
                _a >= _p
    )
VAR _lastBehind = MAXX ( FILTER ( _months, NOT [@ahead] ), DimDate[Month start] )
VAR _run = COUNTROWS ( FILTER ( _months, DimDate[Month start] > _lastBehind ) ) + 0
VAR _words = SWITCH ( _run, 2, "two", 3, "three", 4, "four", 5, "five", 6, "six", FORMAT ( _run, "0" ) )
RETURN
    SWITCH (
        TRUE (),
        ISFILTERED ( DimCountry ), "Plan is set for all regions only",
        _run = 0, "Behind plan this month",
        _run = 1, "Ahead of plan this month",
        "Ahead of plan for " & _words & " months running"
    )
```

**Trend Net Revenue** – Net revenue for the 12 months up to the selected month, on the TrendMonth axis. (format `€#,0.0,,\M`)

```dax
VAR _sel = MAX ( DimDate[Month start] )
VAR _ax = MAX ( TrendMonth[Month start] )
RETURN
    IF (
        _ax > EDATE ( _sel, -12 ) && _ax <= _sel,
        CALCULATE ( [Net Revenue], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _ax )
    )
```

**Trend Plan Revenue** – Net revenue plan for the 12 months up to the selected month. Blank when a region is selected. (format `€#,0.0,,\M`)

```dax
VAR _sel = MAX ( DimDate[Month start] )
VAR _ax = MAX ( TrendMonth[Month start] )
RETURN
    IF (
        NOT ISFILTERED ( DimCountry ) && _ax > EDATE ( _sel, -12 ) && _ax <= _sel,
        CALCULATE ( [Plan Revenue], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _ax )
    )
```

**Selected Segment Revenue** – Net revenue of the segments selected in the segment slicer. (format `€#,0.0,,\M`)

```dax
[Net Revenue]
```

**Average Segment Revenue** – Net revenue of all segments divided by the number of segments. (format `€#,0.0,,\M`)

```dax
DIVIDE ( CALCULATE ( [Net Revenue], REMOVEFILTERS ( DimSegment ) ), COUNTROWS ( ALL ( DimSegment ) ) )
```

### Data trust

**Last Data Date** – Latest business date in the daily fact. (format `d mmm yyyy`)

```dax
CALCULATE ( MAX ( FactDaily[date] ), REMOVEFILTERS () )
```

**Last Load At** – Time of the latest successful file load (CET). (format `d mmm yyyy hh:nn`)

```dax
CALCULATE ( MAX ( LoadLog[loaded_at] ), REMOVEFILTERS () )
```

**Freshness Pass** – 1 when the latest load is before 07:00 CET on the day after the last business date. (format `0`)

```dax
VAR _deadline = [Last Data Date] + 1 + TIME ( 7, 0, 0 )
RETURN
    IF ( [Last Load At] < _deadline, 1, 0 )
```

**Freshness Value** – Latest load time, as text.

```dax
FORMAT ( [Last Load At], "d mmm, hh:nn", "en-US" )
```

**Ledger Revenue** – Net revenue booked in the finance ledger. (format `€#,0`)

```dax
SUM ( FactLedger[ledger_revenue_eur] )
```

**Daily Revenue All Regions** – Net revenue from the daily fact, ignoring the region filter so it compares with the ledger. (format `€#,0`)

```dax
CALCULATE ( [Net Revenue], REMOVEFILTERS ( DimCountry ) )
```

**Reconciliation Gap** – Daily fact revenue minus ledger revenue. (format `€#,0;-€#,0;€0`)

```dax
[Daily Revenue All Regions] - [Ledger Revenue]
```

**Reconciliation Gap CM** – Reconciliation gap for the selected month. (format `€#,0;-€#,0;€0`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Reconciliation Gap], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Reconciliation Pass** – 1 when the absolute gap for the selected month is below €1. (format `0`)

```dax
IF ( ABS ( [Reconciliation Gap CM] ) < 1, 1, 0 )
```

**Rows Present** – Rows in the daily fact. (format `#,0`)

```dax
COUNTROWS ( FactDaily ) + 0
```

**Rows Expected** – Countries x segments x days up to the last business date. (format `#,0`)

```dax
VAR _last = [Last Data Date]
VAR _days = COUNTROWS ( FILTER ( VALUES ( DimDate[Date] ), DimDate[Date] <= _last ) )
RETURN
    _days * COUNTROWS ( DimCountry ) * COUNTROWS ( DimSegment )
```

**Completeness %** – Rows present divided by rows expected. (format `0.0%`)

```dax
DIVIDE ( [Rows Present], [Rows Expected] )
```

**Rows Present CM** – Rows present in the selected month. (format `#,0`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Rows Present], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Rows Expected CM** – Rows expected in the selected month. (format `#,0`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Rows Expected], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Completeness CM** – Completeness for the selected month. (format `0.0%`)

```dax
VAR _m = MAX ( DimDate[Month start] )
RETURN
    CALCULATE ( [Completeness %], REMOVEFILTERS ( DimDate ), DimDate[Month start] = _m )
```

**Completeness Pass** – 1 when every expected row is present in the selected month. (format `0`)

```dax
IF ( [Completeness CM] >= 1, 1, 0 )
```

**Late Files** – Acquirer files with status pending. (format `0`)

```dax
CALCULATE ( COUNTROWS ( LoadLog ), REMOVEFILTERS (), LoadLog[status] = "pending" ) + 0
```

**Late Files Pass** – 1 when no acquirer file is pending (a pending file is a warning). (format `0`)

```dax
IF ( [Late Files] = 0, 1, 0 )
```

**Checks Passed** – Number of the four checks that pass. (format `0`)

```dax
[Freshness Pass] + [Reconciliation Pass] + [Completeness Pass] + [Late Files Pass]
```

**Trust Score** – Weighted score 0-100: freshness 30, reconciliation 30, completeness 25 (pro rata), files loaded in the last 7 days 15 (pro rata). (format `0.0`)

```dax
VAR _last = [Last Data Date]
VAR _fileShare =
    CALCULATE (
        DIVIDE ( CALCULATE ( COUNTROWS ( LoadLog ), LoadLog[status] = "loaded" ), COUNTROWS ( LoadLog ) ),
        REMOVEFILTERS (),
        LoadLog[date] > _last - 7
    )
RETURN
    30 * [Freshness Pass]
        + 30 * [Reconciliation Pass]
        + 25 * MIN ( [Completeness CM], 1 )
        + 15 * _fileShare
```

**Trust Score Label** – Trust score as text for the panel header.

```dax
FORMAT ( [Trust Score], "0.0", "en-US" ) & " score"
```

**Data Trusted** – 1 when freshness, reconciliation and completeness pass. Late files only warn. (format `0`)

```dax
IF ( [Freshness Pass] * [Reconciliation Pass] * [Completeness Pass] = 1, 1, 0 )
```

**Data Trust Pill** – Text for the header pill.

```dax
IF ( [Data Trusted] = 1, "●  Data trusted · ", "●  Check data · " )
    & FORMAT ( [Last Load At], "hh:nn", "en-US" )
```

**Check Status** – Pass (1) or warn (0) for the check in context. (format `0`)

```dax
SWITCH (
    SELECTEDVALUE ( DQ_Checks[check_id] ),
    1, [Freshness Pass],
    2, [Reconciliation Pass],
    3, [Completeness Pass],
    4, [Late Files Pass]
)
```

**Check Detail** – One line of evidence for the check in context.

```dax
VAR _late = [Late Files]
RETURN
    SWITCH (
        SELECTEDVALUE ( DQ_Checks[check_id] ),
        1, "Loaded " & FORMAT ( [Last Load At], "hh:nn", "en-US" ) & " CET",
        2, "Ledger vs daily: " & FORMAT ( ABS ( [Reconciliation Gap CM] ), "€#,0", "en-US" ) & " gap",
        3, FORMAT ( [Rows Present CM], "#,0", "en-US" ) & " / " & FORMAT ( [Rows Expected CM], "#,0", "en-US" ) & " rows",
        4, IF ( _late = 0, "All acquirer files loaded", _late & IF ( _late = 1, " acquirer file pending", " acquirer files pending" ) )
    )
```

### Format

**Trend Bar Colour** – Full mint for the selected month, mint at 40% for the other months.

```dax
IF ( MAX ( TrendMonth[Month start] ) = MAX ( DimDate[Month start] ), "#3DDBB4", "#226459" )
```

**MoM Colour** – Mint when volume grew month on month, coral when it fell.

```dax
IF ( [Volume MoM %] >= 0, "#3DDBB4", "#FF8A7A" )
```

**Data Trust Pill Colour** – Mint when the data is trusted, amber otherwise.

```dax
IF ( [Data Trusted] = 1, "#3DDBB4", "#F2B45A" )
```

**Completeness Colour** – Cell colour for the completeness heatmap.

```dax
VAR _c = [Completeness %]
RETURN
    SWITCH ( TRUE (), ISBLANK ( _c ), BLANK (), _c >= 1, "#164C42", "#F2B45A" )
```

**Completeness Font Colour** – Dark text on amber cells, light text otherwise.

```dax
IF ( [Completeness %] < 1, "#0A0D12", "#E9EDF2" )
```

**Heat Colour** – Mint scale for the country x segment matrix, by share of the selected volume.

```dax
VAR _v = [Volume CM]
VAR _all = CALCULATE ( [Volume CM], ALLSELECTED ( DimCountry ), ALLSELECTED ( DimSegment ) )
VAR _t = MIN ( DIVIDE ( _v, _all ) / 0.06, 1 )
RETURN
    IF (
        NOT ISBLANK ( _v ),
        "rgb(" & ROUND ( 16 + 45 * _t, 0 ) & "," & ROUND ( 21 + 198 * _t, 0 ) & "," & ROUND ( 28 + 152 * _t, 0 ) & ")"
    )
```

**Heat Font Colour** – Dark text on bright heat cells.

```dax
VAR _all = CALCULATE ( [Volume CM], ALLSELECTED ( DimCountry ), ALLSELECTED ( DimSegment ) )
RETURN
    IF ( DIVIDE ( [Volume CM], _all ) / 0.06 > 0.55, "#0A0D12", "#E9EDF2" )
```

### SVG

**SVG Hero Sparkline** – Sub-line (MoM and vs plan) plus area and line of daily net revenue in the selected month. Canvas 352 x 140. (data category *Image URL*)

```dax
VAR _mint = "%233DDBB4"
VAR _amber = "%23F2B45A"
VAR _coral = "%23FF8A7A"
VAR _text = "%23E9EDF2"
VAR _soft = "%23B8C0CC"
VAR _muted = "%238C96A5"
VAR _track = "rgba(255,255,255,0.08)"
VAR _m = MAX ( DimDate[Month start] )
VAR _days =
    FILTER (
        CALCULATETABLE (
            ADDCOLUMNS ( VALUES ( DimDate[Date] ), "@v", [Net Revenue] ),
            REMOVEFILTERS ( DimDate ),
            DimDate[Month start] = _m
        ),
        NOT ISBLANK ( [@v] )
    )
VAR _n = COUNTROWS ( _days )
VAR _first = MINX ( _days, DimDate[Date] )
VAR _hi = MAXX ( _days, [@v] )
VAR _lo = MINX ( _days, [@v] )
VAR _floor = _lo - ( _hi - _lo ) * 0.35
VAR _pts =
    CONCATENATEX (
        _days,
        FORMAT ( 2 + DIVIDE ( DATEDIFF ( _first, DimDate[Date], DAY ), _n - 1, 0 ) * 346, "0.0", "en-US" ) & ","
            & FORMAT ( 138 - DIVIDE ( [@v] - _floor, _hi - _floor, 0.5 ) * 92, "0.0", "en-US" ),
        " ", DimDate[Date], ASC
    )
VAR _mom = [Net Revenue MoM %]
VAR _vp = [Net Revenue vs Plan %]
VAR _line =
    "<text x='2' y='13' font-size='12.5'>"
        & "<tspan font-weight='600' fill='" & IF ( _mom >= 0, _mint, _coral ) & "'>" & SUBSTITUTE ( FORMAT ( _mom, "+0.0%;-0.0%", "en-US" ), "%", "%25" ) & "</tspan>"
        & "<tspan fill='" & _soft & "'> vs " & FORMAT ( EDATE ( _m, -1 ), "mmmm", "en-US" ) & "</tspan>"
        & IF (
            NOT ISBLANK ( _vp ),
            "<tspan fill='" & _soft & "'> · </tspan><tspan font-weight='600' fill='" & _amber & "'>"
                & SUBSTITUTE ( FORMAT ( _vp, "+0.0%;-0.0%", "en-US" ), "%", "%25" ) & "</tspan><tspan fill='" & _soft & "'> vs plan</tspan>"
        )
        & "</text>"
RETURN
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='352' height='140' viewBox='0 0 352 140' font-family='Segoe UI'>"
        & "<defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='" & _mint & "' stop-opacity='0.30'/><stop offset='1' stop-color='" & _mint & "' stop-opacity='0.02'/></linearGradient></defs>"
        & _line
        & "<polygon points='2,138 " & _pts & " 348,138' fill='url(%23g)'/>"
        & "<polyline points='" & _pts & "' fill='none' stroke='" & _mint & "' stroke-width='2' stroke-linejoin='round'/>"
        & "</svg>"
```

**SVG KPI Volume** – Volume tile: ring = volume / plan, 16-week spark, MoM and share of plan. (data category *Image URL*)

```dax
VAR _mint = "%233DDBB4"
VAR _amber = "%23F2B45A"
VAR _coral = "%23FF8A7A"
VAR _text = "%23E9EDF2"
VAR _soft = "%23B8C0CC"
VAR _muted = "%238C96A5"
VAR _track = "rgba(255,255,255,0.08)"
VAR _m = MAX ( DimDate[Month start] )
VAR _end = MIN ( EOMONTH ( _m, 0 ), [Last Data Date] )
-- ring: share of plan or limit, capped at 100%
VAR _ratio = DIVIDE ( [Volume CM], [Plan Volume CM] )
VAR _arc = MIN ( MAX ( _ratio, 0 ), 1 ) * 75.4
VAR _ringColour = _mint
VAR _ring =
    "<circle cx='201' cy='21' r='12' fill='none' stroke='" & _track & "' stroke-width='3'/>"
        & IF (
            NOT ISBLANK ( _ratio ),
            "<circle cx='201' cy='21' r='12' fill='none' stroke='" & _ringColour
                & "' stroke-width='3' stroke-linecap='round' stroke-dasharray='"
                & FORMAT ( _arc, "0.0", "en-US" ) & " 75.4' transform='rotate(-90 201 21)'/>"
        )
-- spark: 16 points
VAR _series = ADDCOLUMNS (
        GENERATESERIES ( 0, 15, 1 ),
        "@v",
            VAR _e = _end - 7 * ( 15 - [Value] )
            RETURN
                CALCULATE ( [Volume], REMOVEFILTERS ( DimDate ), DimDate[Date] > _e - 7, DimDate[Date] <= _e )
    )
VAR _hi = MAXX ( _series, [@v] )
VAR _lo = MINX ( _series, [@v] )
VAR _pts =
    CONCATENATEX (
        _series,
        FORMAT ( 128 + [Value] * 6, "0.0", "en-US" ) & ","
            & FORMAT ( 124 - DIVIDE ( [@v] - _lo, _hi - _lo, 0.5 ) * 22, "0.0", "en-US" ),
        " ", [Value], ASC
    )
VAR _spark = "<polyline points='" & _pts & "' fill='none' stroke='" & _mint & "' stroke-width='1.6' stroke-linejoin='round' stroke-linecap='round'/>"
-- sub-lines
VAR _prev = FORMAT ( EDATE ( _m, -1 ), "mmm", "en-US" )
VAR _l1 = VAR _v = [Volume MoM %]
    RETURN
        "<tspan font-weight='600' fill='" & IF ( _v >= 0, _mint, _coral ) & "'>" & SUBSTITUTE ( FORMAT ( _v, "+0.0%;-0.0%", "en-US" ), "%", "%25" ) & "</tspan>"
VAR _l2 = VAR _r = DIVIDE ( [Volume CM], [Plan Volume CM] )
    RETURN
        IF ( ISBLANK ( _r ), "plan set for all regions", SUBSTITUTE ( FORMAT ( _r, "0%", "en-US" ), "%", "%25" ) & " of plan" )
VAR _txt =
    "<text x='0' y='108' font-size='12'>" & _l1 & "<tspan fill='" & _soft & "'> vs " & _prev & "</tspan></text>"
        & "<text x='0' y='125' font-size='11' fill='" & _muted & "'>" & _l2 & "</text>"
RETURN
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='226' height='130' viewBox='0 0 226 130' font-family='Segoe UI'>"
        & _ring & _spark & _txt & "</svg>"
```

**SVG KPI Take Rate** – Take rate tile: ring = take rate / target, 16-week spark, change in bps and target. (data category *Image URL*)

```dax
VAR _mint = "%233DDBB4"
VAR _amber = "%23F2B45A"
VAR _coral = "%23FF8A7A"
VAR _text = "%23E9EDF2"
VAR _soft = "%23B8C0CC"
VAR _muted = "%238C96A5"
VAR _track = "rgba(255,255,255,0.08)"
VAR _m = MAX ( DimDate[Month start] )
VAR _end = MIN ( EOMONTH ( _m, 0 ), [Last Data Date] )
-- ring: share of plan or limit, capped at 100%
VAR _ratio = DIVIDE ( [Take Rate CM], [Plan Take Rate CM] )
VAR _arc = MIN ( MAX ( _ratio, 0 ), 1 ) * 75.4
VAR _ringColour = _mint
VAR _ring =
    "<circle cx='201' cy='21' r='12' fill='none' stroke='" & _track & "' stroke-width='3'/>"
        & IF (
            NOT ISBLANK ( _ratio ),
            "<circle cx='201' cy='21' r='12' fill='none' stroke='" & _ringColour
                & "' stroke-width='3' stroke-linecap='round' stroke-dasharray='"
                & FORMAT ( _arc, "0.0", "en-US" ) & " 75.4' transform='rotate(-90 201 21)'/>"
        )
-- spark: 16 points
VAR _series = ADDCOLUMNS (
        GENERATESERIES ( 0, 15, 1 ),
        "@v",
            VAR _e = _end - 7 * ( 15 - [Value] )
            RETURN
                CALCULATE ( [Take Rate], REMOVEFILTERS ( DimDate ), DimDate[Date] > _e - 7, DimDate[Date] <= _e )
    )
VAR _hi = MAXX ( _series, [@v] )
VAR _lo = MINX ( _series, [@v] )
VAR _pts =
    CONCATENATEX (
        _series,
        FORMAT ( 128 + [Value] * 6, "0.0", "en-US" ) & ","
            & FORMAT ( 124 - DIVIDE ( [@v] - _lo, _hi - _lo, 0.5 ) * 22, "0.0", "en-US" ),
        " ", [Value], ASC
    )
VAR _spark = "<polyline points='" & _pts & "' fill='none' stroke='" & _mint & "' stroke-width='1.6' stroke-linejoin='round' stroke-linecap='round'/>"
-- sub-lines
VAR _prev = FORMAT ( EDATE ( _m, -1 ), "mmm", "en-US" )
VAR _l1 = VAR _v = [Take Rate MoM bps]
    RETURN
        "<tspan font-weight='600' fill='" & IF ( _v >= 0, _mint, _coral ) & "'>" & FORMAT ( _v, "+0;-0;0", "en-US" ) & " bps" & "</tspan>"
VAR _l2 = "target " & SUBSTITUTE ( FORMAT ( [Plan Take Rate CM], "0.00%", "en-US" ), "%", "%25" )
VAR _txt =
    "<text x='0' y='108' font-size='12'>" & _l1 & "<tspan fill='" & _soft & "'> vs " & _prev & "</tspan></text>"
        & "<text x='0' y='125' font-size='11' fill='" & _muted & "'>" & _l2 & "</text>"
RETURN
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='226' height='130' viewBox='0 0 226 130' font-family='Segoe UI'>"
        & _ring & _spark & _txt & "</svg>"
```

**SVG KPI Merchants** – Active merchants tile: ring = merchants / plan, 16-month spark (merchants are monthly), MoM change and share of plan. (data category *Image URL*)

```dax
VAR _mint = "%233DDBB4"
VAR _amber = "%23F2B45A"
VAR _coral = "%23FF8A7A"
VAR _text = "%23E9EDF2"
VAR _soft = "%23B8C0CC"
VAR _muted = "%238C96A5"
VAR _track = "rgba(255,255,255,0.08)"
VAR _m = MAX ( DimDate[Month start] )
VAR _end = MIN ( EOMONTH ( _m, 0 ), [Last Data Date] )
-- ring: share of plan or limit, capped at 100%
VAR _ratio = DIVIDE ( [Active Merchants CM], [Plan Merchants CM] )
VAR _arc = MIN ( MAX ( _ratio, 0 ), 1 ) * 75.4
VAR _ringColour = _mint
VAR _ring =
    "<circle cx='201' cy='21' r='12' fill='none' stroke='" & _track & "' stroke-width='3'/>"
        & IF (
            NOT ISBLANK ( _ratio ),
            "<circle cx='201' cy='21' r='12' fill='none' stroke='" & _ringColour
                & "' stroke-width='3' stroke-linecap='round' stroke-dasharray='"
                & FORMAT ( _arc, "0.0", "en-US" ) & " 75.4' transform='rotate(-90 201 21)'/>"
        )
-- spark: 16 points
VAR _series = ADDCOLUMNS (
        GENERATESERIES ( 0, 15, 1 ),
        "@v", CALCULATE ( [Active Merchants], REMOVEFILTERS ( DimDate ), DimDate[Month start] = EDATE ( _m, [Value] - 15 ) )
    )
VAR _hi = MAXX ( _series, [@v] )
VAR _lo = MINX ( _series, [@v] )
VAR _pts =
    CONCATENATEX (
        _series,
        FORMAT ( 128 + [Value] * 6, "0.0", "en-US" ) & ","
            & FORMAT ( 124 - DIVIDE ( [@v] - _lo, _hi - _lo, 0.5 ) * 22, "0.0", "en-US" ),
        " ", [Value], ASC
    )
VAR _spark = "<polyline points='" & _pts & "' fill='none' stroke='" & _mint & "' stroke-width='1.6' stroke-linejoin='round' stroke-linecap='round'/>"
-- sub-lines
VAR _prev = FORMAT ( EDATE ( _m, -1 ), "mmm", "en-US" )
VAR _l1 = VAR _v = [Active Merchants MoM]
    RETURN
        "<tspan font-weight='600' fill='" & IF ( _v >= 0, _mint, _coral ) & "'>" & FORMAT ( _v, "+#,0;-#,0;0", "en-US" ) & "</tspan>"
VAR _l2 = SUBSTITUTE ( FORMAT ( DIVIDE ( [Active Merchants CM], [Plan Merchants CM] ), "0%", "en-US" ), "%", "%25" ) & " of plan"
VAR _txt =
    "<text x='0' y='108' font-size='12'>" & _l1 & "<tspan fill='" & _soft & "'> vs " & _prev & "</tspan></text>"
        & "<text x='0' y='125' font-size='11' fill='" & _muted & "'>" & _l2 & "</text>"
RETURN
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='226' height='130' viewBox='0 0 226 130' font-family='Segoe UI'>"
        & _ring & _spark & _txt & "</svg>"
```

**SVG KPI Fraud** – Fraud tile: ring = fraud bps / limit, 16-week spark, change in bps and the limit. Lower is better. (data category *Image URL*)

```dax
VAR _mint = "%233DDBB4"
VAR _amber = "%23F2B45A"
VAR _coral = "%23FF8A7A"
VAR _text = "%23E9EDF2"
VAR _soft = "%23B8C0CC"
VAR _muted = "%238C96A5"
VAR _track = "rgba(255,255,255,0.08)"
VAR _m = MAX ( DimDate[Month start] )
VAR _end = MIN ( EOMONTH ( _m, 0 ), [Last Data Date] )
-- ring: share of plan or limit, capped at 100%
VAR _ratio = DIVIDE ( [Fraud Loss bps CM], [Fraud Limit bps] )
VAR _arc = MIN ( MAX ( _ratio, 0 ), 1 ) * 75.4
VAR _ringColour = IF ( _ratio < 1, _mint, _coral )
VAR _ring =
    "<circle cx='201' cy='21' r='12' fill='none' stroke='" & _track & "' stroke-width='3'/>"
        & IF (
            NOT ISBLANK ( _ratio ),
            "<circle cx='201' cy='21' r='12' fill='none' stroke='" & _ringColour
                & "' stroke-width='3' stroke-linecap='round' stroke-dasharray='"
                & FORMAT ( _arc, "0.0", "en-US" ) & " 75.4' transform='rotate(-90 201 21)'/>"
        )
-- spark: 16 points
VAR _series = ADDCOLUMNS (
        GENERATESERIES ( 0, 15, 1 ),
        "@v",
            VAR _e = _end - 7 * ( 15 - [Value] )
            RETURN
                CALCULATE ( [Fraud Loss bps], REMOVEFILTERS ( DimDate ), DimDate[Date] > _e - 7, DimDate[Date] <= _e )
    )
VAR _hi = MAXX ( _series, [@v] )
VAR _lo = MINX ( _series, [@v] )
VAR _pts =
    CONCATENATEX (
        _series,
        FORMAT ( 128 + [Value] * 6, "0.0", "en-US" ) & ","
            & FORMAT ( 124 - DIVIDE ( [@v] - _lo, _hi - _lo, 0.5 ) * 22, "0.0", "en-US" ),
        " ", [Value], ASC
    )
VAR _spark = "<polyline points='" & _pts & "' fill='none' stroke='" & _mint & "' stroke-width='1.6' stroke-linejoin='round' stroke-linecap='round'/>"
-- sub-lines
VAR _prev = FORMAT ( EDATE ( _m, -1 ), "mmm", "en-US" )
VAR _l1 = VAR _v = [Fraud Loss bps MoM]
    RETURN
        "<tspan font-weight='600' fill='" & IF ( _v <= 0, _mint, _coral ) & "'>" & FORMAT ( _v, "+0.0;-0.0;0.0", "en-US" ) & " bps" & "</tspan>"
VAR _l2 = "limit " & FORMAT ( [Fraud Limit bps], "0", "en-US" ) & " bps"
VAR _txt =
    "<text x='0' y='108' font-size='12'>" & _l1 & "<tspan fill='" & _soft & "'> vs " & _prev & "</tspan></text>"
        & "<text x='0' y='125' font-size='11' fill='" & _muted & "'>" & _l2 & "</text>"
RETURN
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='226' height='130' viewBox='0 0 226 130' font-family='Segoe UI'>"
        & _ring & _spark & _txt & "</svg>"
```

**SVG Hex Map** – Hexagon map of the 20 countries, fill by share of the largest country's volume, top country in the corner. Canvas 429 x 250. (data category *Image URL*)

```dax
VAR _mint = "%233DDBB4"
VAR _amber = "%23F2B45A"
VAR _coral = "%23FF8A7A"
VAR _text = "%23E9EDF2"
VAR _soft = "%23B8C0CC"
VAR _muted = "%238C96A5"
VAR _track = "rgba(255,255,255,0.08)"
VAR _panel = "%2310151C"
VAR _t =
    ADDCOLUMNS (
        ALL ( DimCountry[iso2], DimCountry[hex_col], DimCountry[hex_row] ),
        "@v", [Volume CM]
    )
VAR _max = MAXX ( _t, [@v] )
VAR _top = TOPN ( 1, FILTER ( _t, NOT ISBLANK ( [@v] ) ), [@v], DESC )
VAR _topIso = MAXX ( _top, DimCountry[iso2] )
VAR _topVal = MAXX ( _top, [@v] )
VAR _hexes =
    CONCATENATEX (
        _t,
        VAR _k = DIVIDE ( [@v], _max )
        VAR _x = 94 + DimCountry[hex_col] * 37.5 + IF ( ISODD ( DimCountry[hex_row] ), 18.75, 0 )
        VAR _y = 52 + DimCountry[hex_row] * 32.5
        VAR _fill =
            IF (
                ISBLANK ( [@v] ),
                "none",
                "rgb(" & ROUND ( 24 + 37 * _k, 0 ) & "," & ROUND ( 64 + 155 * _k, 0 ) & "," & ROUND ( 58 + 122 * _k, 0 ) & ")"
            )
        RETURN
            "<g transform='translate(" & FORMAT ( _x, "0.0", "en-US" ) & " " & FORMAT ( _y, "0.0", "en-US" ) & ")'>"
                & "<use href='%23h' fill='" & _fill & "'/>"
                & "<text y='3.5'" & IF ( _k > 0.62, " style='fill:%230A0D12'" ) & ">" & DimCountry[iso2] & "</text></g>",
        ""
    )
RETURN
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='429' height='250' viewBox='0 0 429 250' font-family='Segoe UI'>"
        & "<defs><path id='h' d='M0,-20L17.3,-10L17.3,10L0,20L-17.3,10L-17.3,-10Z'/></defs>"
        & "<style>use{stroke:" & _panel & ";stroke-width:1.5} text{font-size:10.5px;font-weight:600;fill:" & _text & ";text-anchor:middle}</style>"
        & IF (
            NOT ISBLANK ( _topIso ),
            "<text x='425' y='12' style='text-anchor:end;font-weight:400;font-size:12px;fill:" & _muted & "'>Top: <tspan style='font-weight:600;fill:" & _text & "'>"
                & _topIso & " " & FORMAT ( _topVal, "€#,0,,\M", "en-US" ) & "</tspan></text>"
        )
        & _hexes & "</svg>"
```

**SVG Segment Spark** – Line and soft area of monthly volume, 18 months to the selected month. Mint when MoM >= 0, coral otherwise. Canvas 106 x 28. (data category *Image URL*)

```dax
VAR _mint = "%233DDBB4"
VAR _amber = "%23F2B45A"
VAR _coral = "%23FF8A7A"
VAR _text = "%23E9EDF2"
VAR _soft = "%23B8C0CC"
VAR _muted = "%238C96A5"
VAR _track = "rgba(255,255,255,0.08)"
VAR _m = MAX ( DimDate[Month start] )
VAR _t =
    ADDCOLUMNS (
        GENERATESERIES ( 0, 17, 1 ),
        "@v", CALCULATE ( [Volume], REMOVEFILTERS ( DimDate ), DimDate[Month start] = EDATE ( _m, [Value] - 17 ) )
    )
VAR _hi = MAXX ( _t, [@v] )
VAR _lo = MINX ( _t, [@v] )
VAR _pts =
    CONCATENATEX (
        _t,
        FORMAT ( 2 + [Value] * 6, "0.0", "en-US" ) & ","
            & FORMAT ( 25 - DIVIDE ( [@v] - _lo, _hi - _lo, 0.5 ) * 21, "0.0", "en-US" ),
        " ", [Value], ASC
    )
VAR _c = IF ( [Volume MoM %] >= 0, _mint, _coral )
RETURN
    IF (
        HASONEVALUE ( DimSegment[segment_id] ),
        "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='106' height='28' viewBox='0 0 106 28'>"
            & "<polygon points='2,28 " & _pts & " 104,28' fill='" & _c & "' fill-opacity='0.14'/>"
            & "<polyline points='" & _pts & "' fill='none' stroke='" & _c & "' stroke-width='1.5' stroke-linejoin='round'/>"
            & "</svg>"
    )
```

**SVG Bullet vs Plan** – Bar of volume / plan on a 0-110% scale with an amber target tick at 100%. Canvas 150 x 12. (data category *Image URL*)

```dax
VAR _mint = "%233DDBB4"
VAR _amber = "%23F2B45A"
VAR _coral = "%23FF8A7A"
VAR _text = "%23E9EDF2"
VAR _soft = "%23B8C0CC"
VAR _muted = "%238C96A5"
VAR _track = "rgba(255,255,255,0.08)"
VAR _r = DIVIDE ( [Volume CM], [Plan Volume CM] )
VAR _w = MIN ( _r, 1.1 ) / 1.1 * 150
RETURN
    IF (
        HASONEVALUE ( DimSegment[segment_id] ),
        "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='150' height='12' viewBox='0 0 150 12'>"
            & "<rect x='0' y='4' width='150' height='4' rx='2' fill='" & _track & "'/>"
            & IF (
                NOT ISBLANK ( _r ),
                "<rect x='0' y='4' width='" & FORMAT ( _w, "0.0", "en-US" ) & "' height='4' rx='2' fill='" & _mint & "'/>"
                    & "<rect x='135.4' y='0' width='2' height='12' rx='1' fill='" & _amber & "'/>"
            )
            & "</svg>"
    )
```

**SVG Check Status** – Rounded square with a check mark (pass, mint) or an exclamation mark (warn, amber). Canvas 24 x 24. (data category *Image URL*)

```dax
VAR _mint = "%233DDBB4"
VAR _amber = "%23F2B45A"
VAR _coral = "%23FF8A7A"
VAR _text = "%23E9EDF2"
VAR _soft = "%23B8C0CC"
VAR _muted = "%238C96A5"
VAR _track = "rgba(255,255,255,0.08)"
VAR _s = [Check Status]
VAR _icon =
    IF (
        _s = 1,
        "<rect width='24' height='24' rx='6' fill='rgba(61,219,180,0.14)'/><path d='M7.5 12.4l3 3 6-6.4' fill='none' stroke='" & _mint & "' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/>",
        "<rect width='24' height='24' rx='6' fill='rgba(242,180,90,0.16)'/><rect x='11' y='6.5' width='2' height='7.5' rx='1' fill='" & _amber & "'/><circle cx='12' cy='17' r='1.2' fill='" & _amber & "'/>"
    )
RETURN
    IF (
        NOT ISBLANK ( _s ),
        "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'>" & _icon & "</svg>"
    )
```
