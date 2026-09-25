# Ambiguous topic

User: "How popular was Mercury on English and Ukrainian Wikipedia in March 2024?"

`resolve` is expected to return a per-topic result like:

```json
{
  "query": "Mercury",
  "lang": "en",
  "status": "ambiguous",
  "candidates": [
    {
      "title": "Mercury (planet)",
      "pageid": 19007,
      "description": "innermost planet",
      "langlinks": [{ "lang": "uk", "title": "Меркурій (планета)" }]
    },
    {
      "title": "Mercury (element)",
      "pageid": 19019,
      "description": "chemical element",
      "langlinks": [{ "lang": "uk", "title": "Меркурій" }]
    }
  ],
  "notes": []
}
```

Stop. Ask which subject the user means. Do not call `report`. Do not choose the busier page. Do not treat a disambiguation page as the article.

After the user chooses the planet, `series.json` may contain only that candidate's English title and its Ukrainian langlink, both with the requested dates.
