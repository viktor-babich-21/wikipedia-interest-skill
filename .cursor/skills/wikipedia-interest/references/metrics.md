# Metric definitions

`report` writes these fields to `analysis.json`. Stored values are not rounded. Presentation may round later, but that must not replace the stored numbers.

Included days are `observed` and `missing`. `unavailable` days stay out of every calculation below. There is no cutoff on R², on how complete the range is, or on the busiest day's share. Report the values as calculated. Do not turn R² or the busiest-day share into a pass/fail flag.

## Days

- `observed`: the API returned a view count.
- `missing`: no row for a day inside the published span. Views are 0.
- `unavailable`: that requested day is not published yet. Views are null.

`days_expected` is the number of calendar days from `start` through `end`, inclusive. `days_observed`, `days_missing`, and `days_unavailable` count the three statuses. The three counts sum to `days_expected`.

## Per series

- `total_views`: sum of observed counts. Missing days add nothing. Unavailable days are excluded.
- `mean_daily_views`: mean of included days, with missing days as 0. Null when no included day exists.
- `median_daily_views`: median of the same days. Use the average of the two middle values when the count is even. Null when no included day exists.
- `start_views`: views on the first included day. Null when no included day exists.
- `end_views`: views on the last included day. Null when no included day exists.
- `percent_change`: `(end_views - start_views) / start_views * 100`. Null when `start_views` is 0 or fewer than two included days exist. `notes` states which arithmetic case applied. If both apply, the note is the fewer-than-two case. This is not a quality judgment.
- `slope_views_per_day`: ordinary least-squares slope of views against the day index 0, 1, 2, ... of included days in series order. An unavailable day is left out of that sequence. It is not a hole in x. Null when fewer than two included days exist.
- `r_squared`: coefficient of determination of that same line. Null when fewer than two included days exist. Also null when every included value is the same: the slope is then 0, but R² divides by zero variance, so it is undefined. Store null, not 0, 1, or NaN. Do not label the trend.
- `busiest_day`: the included day with the most views. Ties use the earliest date. Null when no included day exists.
- `busiest_day_views`: views on `busiest_day`. Null when `busiest_day` is null.
- `busiest_day_share`: `busiest_day_views / total_views`. Null when `busiest_day` is null or `total_views` is 0.

## Chart

The chart draws daily views from `analysis.json` and a 7-day moving average. Missing days are drawn as zero. Unavailable days are gaps, not zeros. For each included day, that average is the mean of the day and the six preceding included days. The first days use however many included days exist. Unavailable days are left out of the window. The moving average is a line on the chart, not a summary field, and it is not stored in `analysis.json`.

## Caveats

The PDF copies these sentences from `analysis.json`:

- Page views measure attention to a Wikipedia article, not willingness to pay.
- Wikipedia editions differ in size. These figures are article pageviews.
- Similar movement between series is not causation.
