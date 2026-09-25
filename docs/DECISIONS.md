# Decisions

## Case requirements

The case requires an Agent Skill that compares Wikipedia article attention across topics, languages, and time, resolves real pages, handles ambiguous topics, fetches pageviews, calculates metrics in code, draws a chart, and writes a concise one-page PDF. Tests include fixtures and a manual cheap-model review. The model explains results and does not invent titles or numbers.

## Implementation choices

These are our choices. The case does not name the parameter values.

### agent=user

Pageviews will be requested with `agent=user` so the series counts human readers. Spider and automated traffic is a different question. The case asks for interest, and this parameter is how the Wikimedia API separates human traffic.

### access=all-access

`access=all-access` sums desktop and mobile. The case does not ask for a device split, so one access value keeps a single definition of article attention.

### Daily granularity

Daily rows make a busiest day and a moving-average line possible. Monthly mode is out of scope. The 7-day line is a chart aid, not a summary metric.

### Langlinks

The case requires the same topic to keep its own title in each language edition, and it forbids silently binding a different article. MediaWiki search, redirect resolution, and langlinks do that. Wikidata is not used. A language with no langlink is recorded as `missing langlink: <lang>`.

### Deterministic calculations

The case requires code to compute the numbers. `analysis.json` is the only source the model may quote. The PDF is rendered from that file. Quality thresholds on R², coverage, or spike share are not part of the case and are not used.

### Date floor

Requests that start before 2015-07-01 are rejected. That is the first day of the current pageview definition. Earlier pagecounts are a different metric.

### Fail closed

HTTP and JSON failures stop the command. The pipeline does not invent titles or estimate missing values. Pageview 429/5xx retry is not implemented yet; that belongs with the pageview milestone.

### Resolve selection

Search uses MediaWiki `list=search` in namespace 0 only. The first hit wins when it is not a disambiguation page and its title matches the query (case-insensitive), including when that hit redirects to a canonical title. Otherwise one remaining article resolves, several become `ambiguous`, and none become `not_found`. Pageviews are never used to pick a candidate.
