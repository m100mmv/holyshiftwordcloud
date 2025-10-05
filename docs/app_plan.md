# Word Cloud App Plan

## Goals

Build a local web application that lets a user upload a Ghost export, tweak text-processing parameters, and immediately preview/download the theological word cloud.

## Key Features

- **Data input:** Upload a Ghost JSON file or reuse the last dataset already on the server.
- **Stop-word management:** Provide quick toggles for predefined stopword groups and a text area for custom words to ignore.
- **Weighting controls:** Allow adjustments for global size curve (min/max font size, curvature) and optional per-phrase boost overrides.
- **Typography & palette:** Let users pick font families from a short list and switch between colour themes, plus fine-tune canvas size.
- **Export:** Keep the existing PNG download button and optionally expose an HTML download.

## Architecture

- **Backend:** A lightweight Flask app that keeps the existing Python tokenisation/weighting logic. An `/api/generate` endpoint accepts JSON payloads describing parameters (paths, overrides) and returns the processed word list (text/size/weight). Existing `wordcloud.py` functions move into a reusable module.
- **Frontend:** A single-page interface (plain HTML + vanilla JS) served from Flask. Controls update a shared configuration object; submitting runs `fetch('/api/generate', { method: 'POST', body: JSON.stringify(config) })`. The response re-renders the canvas using the current D3 layout logic.
- **Static assets:** `templates/index.html`, `static/app.js`, `static/style.css`. d3 and d3-cloud still load from a CDN; all other JS lives locally.
- **State handling:** The browser keeps the active stopword/weight settings in memory and syncs them with the backend request. The backend recomputes the word list per request (fast enough for local use).

## Implementation Steps

1. Refactor `wordcloud.py` into a module (`wordcloud_core.py`) exposing `generate_words(config)` and retaining the CLI entrypoint for batch use.
2. Add Flask dependency, build `app.py` with `index` route and `/api/generate` POST endpoint (handling file upload or stored JSON path plus parameter overrides).
3. Create frontend controls for stopwords, weighting sliders, palette selector, fonts, and wiring to fetch the generated data.
4. Update `README.md` with app instructions, dependencies (`pip install flask numpy`), and how to run `flask --app app run`.

## Open Questions

- Should uploads persist on disk or stay in memory? (Initial pass: save to `/tmp`-like folder under `data/uploads/` and reuse path per session.)
- How advanced should per-phrase boosting edits be? (Maybe simple textarea keyed by `phrase:multiplier`.)
- Do we need authentication? (Probably no; local use only.)

## Recent Enhancements

- Added support for plain-text ingestion alongside JSON, with automatic or manual input-type selection.
- Introduced flexible JSON extraction controls (specific keys or collect-all) plus an option to disable reference weighting entirely.
- Exposed theme presets from the backend so the UI and CLI share the same palette catalog.
- Added an analysis workflow that surfaces base/final counts and accepts manual per-word adjustments before regeneration.
- Introduced an opt-out cache for token/reference extraction to speed up iterative tweaking (see `WORDCLOUD_CACHE*` env vars).

The next commits will address these steps incrementally.
