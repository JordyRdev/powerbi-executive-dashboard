# SVG measures

The small charts in this report (sparklines, progress rings, the hex map, bullet bars and status icons) are DAX measures that return an SVG image as text. Power BI shows them with native visuals only: the Image visual, or a table column. No custom visuals, so the report opens anywhere.

## How it works

1. The measure returns a string that starts with `data:image/svg+xml;utf8,` followed by SVG markup.
2. The measure's data category is **Image URL** (`dataCategory: ImageUrl` in TMDL). Without it, Power BI shows the text instead of the picture.
3. Show it in one of two ways:
   - **Image visual**: Format > Image > Image style *Image URL* > fx > the measure. In PBIR: `objects.image.sourceType = 'imageData'` and `sourceField` = the measure.
   - **Table or matrix column**: add the measure as a value. Set the size under *Image size* (PBIR `grid.imageHeight`).

## Rules that save debugging time

| Rule | Why |
|---|---|
| Write `#` as `%23` (`%233DDBB4`, `url(%23g)`) | `#` ends a URL. Everything after it is dropped and the image is blank. |
| Write `%` in text as `%25` | A bare `%` starts an escape sequence. `SUBSTITUTE ( FORMAT ( x, "0%" ), "%", "%25" )`. |
| Use single quotes inside the SVG | The DAX string is in double quotes. |
| Format every number with `FORMAT ( x, "0.0", "en-US" )` | Without the locale, a Dutch or German machine writes `12,5` and the coordinates break. |
| Round coordinates to one decimal | Shorter strings. Power BI limits the length of a text value in a visual, and short strings are faster. Keep a measure under about 4,000 characters. |
| Put all colours in one `VAR` block at the top | One place to change the palette. |
| Set `width`, `height` and `viewBox` to the size of the visual | The image is then drawn at 1:1 with no scaling blur. |
| Return `BLANK ()` for totals and empty rows | Use `HASONEVALUE` in table measures so the total row stays empty. |

## The pattern

Every chart measure follows the same four steps: build a small table of points, find its range, map each point to pixels, join the points with `CONCATENATEX`.

```dax
SVG Spark Template =
-- 1. colours (URL-safe)
VAR _mint = "%233DDBB4"
VAR _coral = "%23FF8A7A"
-- 2. a small table of points: 18 months up to the selected month
VAR _m = MAX ( DimDate[Month start] )
VAR _t =
    ADDCOLUMNS (
        GENERATESERIES ( 0, 17, 1 ),
        "@v", CALCULATE ( [Volume], REMOVEFILTERS ( DimDate ), DimDate[Month start] = EDATE ( _m, [Value] - 17 ) )
    )
-- 3. range
VAR _hi = MAXX ( _t, [@v] )
VAR _lo = MINX ( _t, [@v] )
-- 4. map to pixels (canvas 106 x 28, 2 px margin) and join
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
            & "<polyline points='" & _pts & "' fill='none' stroke='" & _c & "' stroke-width='1.5'/>"
            & "</svg>"
    )
```

To reuse it: change the base measure in step 2, the number of points (`GENERATESERIES ( 0, n - 1, 1 )` and the x step), and the canvas size. `DIVIDE ( …, _hi - _lo, 0.5 )` puts a flat series in the middle instead of failing.

## Building blocks used in this report

**Progress ring.** Two circles with the same centre. The second has `stroke-dasharray` set to the share times the circumference (2πr; for r = 12 that is 75.4) and is rotated −90° so it starts at the top.

```dax
"<circle cx='201' cy='21' r='12' fill='none' stroke='rgba(255,255,255,0.08)' stroke-width='3'/>"
    & "<circle cx='201' cy='21' r='12' fill='none' stroke='%233DDBB4' stroke-width='3' stroke-linecap='round'"
    & " stroke-dasharray='" & FORMAT ( MIN ( _ratio, 1 ) * 75.4, "0.0", "en-US" ) & " 75.4'"
    & " transform='rotate(-90 201 21)'/>"
```

**Area under a line.** The same points as the line, closed along the bottom edge: `"x0,bottom " & _pts & " xN,bottom"` in a `<polygon>`, filled with a vertical gradient or a low opacity.

**Hex map.** One hexagon is defined once in `<defs>` and placed with `<use href='%23h'>` at each country's grid position (odd rows shifted by half a hexagon). Shared styles sit in a `<style>` block, so each country adds about 110 characters. The fill is an `rgb(…)` value mixed between a dark and a bright mint by the country's share of the largest country. Countries outside the region filter return blank and are drawn as an outline.

**Bullet bar.** A full-width track, a bar for actual ÷ plan on a 0–110% scale, and a 2 px amber tick at 100%.

**Status icon.** A rounded square with a check path (pass) or an exclamation mark (warning). The state comes from `[Check Status]`, so the same measure works in a table of checks and in a single tile with a visual-level filter.

## Measures in this report

| Measure | Canvas | Used in |
|---|---|---|
| `SVG Hero Sparkline` | 352 × 200 | Overview, net revenue tile: value, sub-line and daily area chart for the selected month |
| `SVG KPI Volume`, `SVG KPI Take Rate`, `SVG KPI Merchants`, `SVG KPI Fraud` | 226 × 130 | Overview KPI tiles: value, ring, two sub-lines and a 16-point spark (weeks; months for merchants) |
| `SVG Hex Map` | 429 × 250 | Overview, volume by country |
| `SVG Segment Spark` | 106 × 28 | Segment tables, per row |
| `SVG Bullet vs Plan` | 150 × 12 | Segment tables, per row |
| `SVG Check Status` | 24 × 24 | Data trust table on the overview |
| `SVG Check Tile` | 340 × 110 | Data trust page: check value and status icon in one image |
| `SVG Title …`, `SVG Plan Status Line`, `SVG Trust Score` | various | Text lines drawn as SVG instead of card visuals |

The full DAX of each one is in [model-and-measures.md](model-and-measures.md).

## Performance

Text is cheaper as SVG than as a card. In Performance Analyzer the new card visual spent 150–240 ms rendering each value, an Image visual about 60 ms, so the KPI values and the page titles are drawn inside the SVGs.


Each SVG measure runs a handful of storage-engine queries (16 to 31 small `CALCULATE`s over a 73,000-row table) and some string work in the formula engine. Keep the number of points small, filter with `REMOVEFILTERS` plus simple column filters, and avoid iterating the fact table inside `CONCATENATEX`.
