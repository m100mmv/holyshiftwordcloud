# Holy Shift Word Cloud Studio

Generate and customise rich word clouds from Ghost exports, arbitrary JSON payloads, or plain-text documents—either via the interactive web studio or the Python CLI.

## Requirements

- Python 3.10+
- Virtual environment recommended (`python3 -m venv .venv && source .venv/bin/activate`)
- Install dependencies:

  ```bash
  pip install numpy flask
  ```

## Project layout

```
Wordcloud/
├── app.py                    # Flask app entrypoint
├── wordcloud.py              # CLI entrypoint (batch HTML generation)
├── wordcloud_core.py         # Shared processing utilities
├── templates/index.html      # Web UI shell
├── static/app.js             # Front-end logic
├── static/styles.css         # Web UI styling
├── data/                     # Drop Ghost exports here (uploads saved to data/uploads/)
├── output/                   # CLI-generated HTML
├── docs/app_plan.md          # Architecture notes
└── README.md
```

## Using the web studio

1. Activate your environment and install requirements.
2. Launch the app:

   ```bash
   flask --app app run --debug
   ```

   (Or `python app.py` for a simple development server.)

3. Open `http://127.0.0.1:5000/` in your browser.

4. Upload a `.json`, `.txt`, `.md`, etc. file (or point to an existing path inside the project), choose the input mode, and tweak:
   - Stopword groups, custom stop lists, and forced keeps
   - Size curve (min/max font, curve power, reference weight) and optional reference weighting
   - Palette presets (muted, forest, sunrise, ocean, citrus, grayscale) or your own colour list and font stack
   - JSON-only options: supply specific keys to read, or aggregate every string value in the payload
   - Run **Analyze Tokens** to inspect counts, set new target totals for key words, then apply and re-render
   - Canvas size, title/heading, and output downloads (PNG & HTML)

5. Click **Render Cloud** to fetch a fresh layout. You can download either the PNG (from the canvas) or the full HTML your configuration produced.

## CLI usage

The command-line workflow still works for automated runs:

```bash
python wordcloud.py data/holy-shift.ghost.2025-10-01-17-44-39.json output/holy_shift_wordcloud_portfolio_muted.html \
  --max-items 420 --min-font 9 --max-font 180 --curve-power 0.75 --json-key plaintext
```

Optional flags:

- `--input-type text` to force plain-text processing (skip JSON parsing)
- `--json-key body --json-key content` to target specific keys inside JSON
- `--json-all-strings` to ingest every string value from a structured payload
- `--no-references` to disable scripture/reference boosting entirely
- `--disable-stop-group personal` / `--extra-stop holyshift` (repeatable)
- `--boost "kingdom of god=3.5"`
- `--palette forest` (use built-in theme names) or `--palette "#0f172a,#334155,#475569"`
- `--width 2048 --height 1152`
- `--dump-json output/words.json`

## Notes

- CDN access is required when previewing the HTML because the page loads `d3`/`d3-cloud` from `unpkg`. The Flask app itself runs locally.
- Uploads (JSON or text) are stored under `data/uploads/` so you can reuse them without re-uploading.
- The compile check (`python -m compileall`) may fail on macOS if Python cannot write to `~/Library/Caches/com.apple.python/`. Set `PYTHONPYCACHEPREFIX` to a writable folder if you need bytecode caches.
- When processing unfamiliar JSON, start with `--json-all-strings` (or toggle the checkbox in the studio) to confirm the content mix, then narrow down with specific keys for cleaner clouds.
- Token and reference extraction results are cached per file/configuration for faster re-analysis. Disable by exporting `WORDCLOUD_CACHE=0` or set capacity via `WORDCLOUD_CACHE_MAX`.

Feel free to extend the presets in `static/app.js` or expose more configuration knobs from `wordcloud_core.WordCloudConfig`.
