# Metric definitions

`report` will compute these fields. This milestone only checks that `analysis.json` has the right shape. It does not calculate them.

Included days are `observed` and `missing`. `unavailable` days stay out of every calculation below. There is no cutoff on R², on how complete the range is, or on the busiest day's share. Report the values as calculated.

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
- `percent_change`: `(end_views - start_views) / start_views * 100`. Null when `start_views` is 0 or fewer than two included days exist.
- `slope_views_per_day`: ordinary least-squares slope of views against the day index 0, 1, 2, ... of included days. Null when fewer than two included days exist.
- `r_squared`: coefficient of determination of that line. Null in the same case.
- `busiest_day`: the included day with the most views. Ties use the earliest date. Null when no included day exists.
- `busiest_day_views`: views on `busiest_day`. Null when `busiest_day` is null.
- `busiest_day_share`: `busiest_day_views / total_views`. Null when `busiest_day` is null or `total_views` is 0.

## Chart

The chart will draw daily views and a 7-day moving average. For each included day, that average is the mean of the day and the six preceding included days. The first days use however many included days exist. The moving average is a line on the chart, not a summary field.

## Caveats

The PDF copies these sentences from `analysis.json`:

- Page views measure attention to a Wikipedia article, not willingness to pay.
- Wikipedia editions differ in size.
- Similar movement between series is not causation.
