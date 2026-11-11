# Report spec

Canvas 1600 × 900 px, three pages. Positions are in pixels from the top-left corner and were measured on `design/design_reference.png`, which is drawn at the same size. The PBIR files use these numbers as they are.

## Look

| Used for | Hex |
|---|---|
| Canvas | `#0A0D12` |
| Panels | `#10151C` |
| Panel borders and grid lines (white, 7% opacity) | `#1F242B` |
| Values and labels | `#E9EDF2` |
| Secondary labels, axes | `#8C96A5` |
| Actuals, good news (mint) | `#3DDBB4` |
| Plan lines, warnings (amber) | `#F2B45A` |
| Bad news (coral) | `#FF8A7A` |

- Font Segoe UI; numbers in Segoe UI Semibold.
- Every visual has background, border, title and header turned off. The panels, the navigation rail and all static labels are part of the page background PNG (`design/backgrounds/`).
- Panel titles are small caps in muted text, 11 px, letter-spaced. They are drawn in the background, not as visuals.
- Panels have a 16 px radius and a hairline border.

## Shared on every page

| Visual | Type | Fields | x | y | w | h |
|---|---|---|---|---|---|---|
| Nav: overview | Button (blank, page navigation) | – | 16 | 86 | 44 | 44 |
| Nav: segments | Button (blank, page navigation) | – | 16 | 140 | 44 | 44 |
| Nav: data trust | Button (blank, page navigation) | – | 16 | 194 | 44 | 44 |
| Page title | Image (measure) | `SVG Title <page>` | 104 | 40 | 560 | 44 |
| Month | Slicer, dropdown, single select, synced | `DimDate[Month]` | 900 | 34 | 148 | 36 |
| Region | Slicer, horizontal tiles, single select with "Select all", synced | `DimCountry[region]` | 1060 | 33 | 320 | 36 |

The rail icons and the highlight on the active page are drawn in the background. The buttons on top are transparent.

## Page 1 – Executive overview

Follows the reference image.

| # | Visual | Type | Fields | x | y | w | h |
|---|---|---|---|---|---|---|---|
| 1 | Data trust pill | Button, text from measure, goes to page 3 | `Data Trust Pill`, colour `Data Trust Pill Colour` | 1404 | 35 | 166 | 32 |
| 2 | Hero | Image (measure): value, sub-line and daily trend | `SVG Hero Sparkline` | 126 | 128 | 352 | 200 |
| 3 | Hero hover text | Button (blank), tooltip with the definition, opens Segments | – | 107 | 93 | 391 | 238 |
| 4 | Volume tile | Image (measure): value, ring, sub-lines, spark | `SVG KPI Volume` | 529 | 108 | 226 | 130 |
| 5 | Volume hover text | Button (blank), tooltip, opens Segments | – | 514 | 93 | 252 | 238 |
| 6 | Take rate tile | Image (measure) | `SVG KPI Take Rate` | 797 | 108 | 226 | 130 |
| 7 | Take rate hover text | Button (blank) | – | 782 | 93 | 252 | 238 |
| 8 | Merchants tile | Image (measure) | `SVG KPI Merchants` | 1065 | 108 | 226 | 130 |
| 9 | Merchants hover text | Button (blank) | – | 1050 | 93 | 252 | 238 |
| 10 | Fraud tile | Image (measure) | `SVG KPI Fraud` | 1333 | 108 | 226 | 130 |
| 11 | Fraud hover text | Button (blank) | – | 1318 | 93 | 252 | 238 |
| 12 | Plan status line | Image (measure) | `SVG Plan Status Line` | 128 | 384 | 520 | 30 |
| 13 | Net revenue vs plan | Line and stacked column | axis `TrendMonth[Month]`, columns `Trend Revenue Other Months` (mint at 40%, `#226459`) and `Trend Revenue Selected Month` (mint); only one has a value per month, so each month is one bar. Line `Trend Plan Revenue` (amber, dashed) | 118 | 420 | 966 | 222 |
| 14 | Volume by country | Image (measure) | `SVG Hex Map` | 1126 | 366 | 429 | 250 |
| 15 | Merchant segment table | Table | `DimSegment[segment]`, `Volume Label Short`, `Volume MoM %` (font `MoM Colour`), `SVG Segment Spark`, `SVG Bullet vs Plan`; filter `DimSegment[sort] <= 4` | 118 | 676 | 966 | 206 |
| 16 | Trust score | Image (measure), right aligned, mint | `SVG Trust Score` | 1412 | 680 | 135 | 26 |
| 17 | Data trust table | Table | `SVG Check Status`, `DQ_Checks[check]`, `Check Detail` | 1126 | 708 | 429 | 174 |

Panels drawn in the background (x, y, w, h): hero 107, 93, 391, 238 · KPI tiles at x 514 / 782 / 1050 / 1318, y 93, 252 × 238 · net revenue vs plan 107, 349, 988, 302 · volume by country 1111, 349, 459, 302 · merchant segment 107, 669, 988, 215 · data trust 1111, 669, 459, 215.

Static text in the background: kicker "HALCYON PAY · EXECUTIVE OVERVIEW" (107, 27), KPI labels, "Daily, this month" chip (362, 112), chart legend (Actual / Plan) at (959, 383), hex legend "Low – High" at y 629, a hairline separator at x 1389 and the pill outline.

Interactions: a click on a segment row filters the page. The hex map reacts to the month and region slicers; it cannot be clicked to filter, because an image visual has no data points. The month slicer does not filter the 12-month chart directly; the chart reads the selected month through its measures.

## Page 2 – Segments

| # | Visual | Type | Fields | x | y | w | h |
|---|---|---|---|---|---|---|---|
| 1 | Segment chips | Slicer, horizontal tiles, single select | `DimSegment[segment]` | 104 | 96 | 900 | 38 |
| 2 | Monthly revenue | Line chart, 24 months | axis `DimDate[Month]`, `Selected Segment Revenue` (mint), `Average Segment Revenue` (muted) | 118 | 192 | 878 | 296 |
| 3 | Segment table | Table | segment, `Volume Label Short`, `Volume MoM %`, `Net Revenue Label Short`, `Take Rate CM`, `Fraud Loss bps CM`, `SVG Segment Spark`, `SVG Bullet vs Plan` | 118 | 528 | 878 | 346 |
| 4 | Country × segment | Matrix | rows `DimCountry[country]`, columns `DimSegment[segment]`, value `Volume Label Short` with background `Heat Colour` and font `Heat Font Colour` | 1034 | 192 | 525 | 682 |

Panels (x, y, w, h): chart 107, 149, 900, 350 · table 107, 515, 900, 369 · matrix 1023, 149, 547, 735.

The segment chips filter only the line chart: the selected segment is drawn against the average of all five, which the measure computes with the segment filter removed. The table and the matrix always show all five segments. The month slicer does not filter the line chart (it always shows 24 months).

## Page 3 – Data trust

| # | Visual | Type | Fields | x | y | w | h |
|---|---|---|---|---|---|---|---|
| 1–4 | Check tile | Image (measure), filter `DQ_Checks[check_id] = n`: value and status icon | `SVG Check Tile` | 107 + 369·i + 23 | 97 | 340 | 110 |
| 9 | Reconciliation | Line and clustered column, 24 months | axis `DimDate[Month]`, columns `Daily Revenue All Regions` (mint) and `Ledger Revenue` (muted), line `Reconciliation Gap` (amber, secondary axis) | 118 | 322 | 878 | 278 |
| 10 | Completeness heatmap | Matrix | rows `DimDate[Month]`, columns `DimSegment[segment]`, value `Completeness %` with background `Completeness Colour` | 1034 | 322 | 525 | 552 |
| 11 | Load log | Table, filter `LoadLog[status]` is not `loaded` | `date`, `acquirer`, `file_name`, `expected_at`, `status` | 118 | 668 | 878 | 206 |

Tiles (i = 0..3) are drawn at x 107 + 369·i, y 93, 356 × 170, each with its label and its rule in the background. Panels (x, y, w, h): reconciliation 107, 279, 900, 330 · completeness 1023, 279, 547, 605 · load log 107, 625, 900, 259.

The month slicer does not filter the reconciliation chart or the heatmap: they show every month, so March 2026 (ledger gap) and August 2026 (missing rows) are visible whatever month is selected. The four tiles use the selected month, except freshness and late files, which always look at the latest load.

## Number formats

Numeric measures use plain formats (`€#,0`, `0.00%`). Cards and table columns that need compact values (`€48.2M`, `€2.41B`) show the text measures in the `KPI\Labels` folder, because cards add their own display units on top of a scaled format string. Chart axes use the visual's display units (millions).

Table image columns use `grid.imageHeight` 28 and `grid.imageWidth` 150, and the SVGs are drawn at that size.

## Visual count and speed

Desktop runs only a few visual queries at a time, so every extra query visual waits in line, and the new card visual takes 150–240 ms to render against about 60 ms for an Image visual. Values, titles and short text lines are therefore drawn inside SVG measures, and the KPI definitions sit in the hover text of transparent buttons, which send no queries. Page 1 has 23 visuals, of which 15 query the model; page 2 has 7 query visuals; page 3 has 10.
