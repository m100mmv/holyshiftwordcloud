"""Flask application exposing an interactive interface for the Holy Shift word cloud."""
from __future__ import annotations

import json
import os
import time
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from wordcloud_core import (
    DEFAULT_PALETTE,
    DEFAULT_STOP_GROUPS,
    STOP_GROUPS,
    THEME_PRESETS,
    WordCloudConfig,
    WordCountStat,
    generate_words_and_stats_from_file,
    render_html,
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")

CACHE_ENABLED = os.environ.get("WORDCLOUD_CACHE", "1").lower() not in {"0", "false", "no"}
CACHE_CAPACITY = max(1, int(os.environ.get("WORDCLOUD_CACHE_MAX", "8") or 8))
TOKEN_CACHE: OrderedDict[tuple, Dict[str, object]] = OrderedDict()


def parse_stopword_groups(payload: Mapping[str, Any]) -> Iterable[str]:
    requested = payload.get("stopwordGroups")
    if requested is None:
        return DEFAULT_STOP_GROUPS
    allowed = set(STOP_GROUPS.keys())
    return [group for group in requested if group in allowed]


def parse_boosts(payload: Mapping[str, Any]) -> Dict[str, float]:
    boosts = payload.get("boosts", {})
    parsed: Dict[str, float] = {}
    if isinstance(boosts, Mapping):
        for key, value in boosts.items():
            try:
                parsed[str(key).lower()] = float(value)
            except (TypeError, ValueError):
                continue
    elif isinstance(boosts, Sequence):
        for item in boosts:
            if not isinstance(item, Mapping):
                continue
            phrase = str(item.get("phrase", "")).strip().lower()
            factor = item.get("factor")
            try:
                parsed[phrase] = float(factor)
            except (TypeError, ValueError):
                continue
    return parsed


def parse_manual_adjustments(payload: Mapping[str, Any]) -> Dict[str, float]:
    adjustments = payload.get("manualAdjustments", {})
    parsed: Dict[str, float] = {}
    if isinstance(adjustments, Mapping):
        for key, value in adjustments.items():
            key_str = str(key).strip()
            if not key_str:
                continue
            try:
                parsed[key_str] = float(value)
            except (TypeError, ValueError):
                continue
    elif isinstance(adjustments, Sequence):
        for item in adjustments:
            if not isinstance(item, Mapping):
                continue
            key_str = str(item.get("word", "")).strip()
            if not key_str:
                continue
            value = item.get("adjustment")
            try:
                parsed[key_str] = float(value)
            except (TypeError, ValueError):
                continue
    return parsed


def build_config(payload: Mapping[str, Any]) -> WordCloudConfig:
    config = WordCloudConfig(
        enabled_stop_groups=set(parse_stopword_groups(payload)),
        extra_stopwords={str(word).lower() for word in payload.get("extraStopwords", [])},
        remove_stopwords={str(word).lower() for word in payload.get("removeStopwords", [])},
        keep_short_extra={str(word).lower() for word in payload.get("keepShort", [])},
        max_items=int(payload.get("maxItems", 420)),
        max_font_size=int(payload.get("maxFont", 180)),
        min_font_size=int(payload.get("minFont", 9)),
        size_curve_power=float(payload.get("curvePower", 0.75)),
        reference_weight=int(payload.get("referenceWeight", 4)),
        collect_all_json_strings=bool(payload.get("collectAllJsonStrings", False)),
        detect_references=bool(payload.get("detectReferences", True)),
    )

    boosts = parse_boosts(payload)
    if boosts:
        config.boost_map.update(boosts)

    json_keys = payload.get("jsonKeys")
    if isinstance(json_keys, (list, tuple, set)):
        config.json_text_keys = {str(key).lower() for key in json_keys if str(key).strip()}
    elif isinstance(json_keys, str) and json_keys.strip():
        config.json_text_keys = {segment.strip().lower() for segment in json_keys.split(",") if segment.strip()}

    manual_adjustments = parse_manual_adjustments(payload)
    if manual_adjustments:
        config.manual_weight_adjustments = manual_adjustments
    return config


def build_token_cache_key(path: Path, file_type: str, config: WordCloudConfig) -> tuple:
    stat = path.stat()
    stopwords_key = tuple(sorted(config.stopwords()))
    keep_key = tuple(sorted(config.keep_short()))
    json_keys = tuple(sorted(config.json_text_keys)) if config.json_text_keys else ()
    return (
        str(path),
        file_type,
        int(stat.st_mtime_ns),
        stopwords_key,
        keep_key,
        config.min_token_length,
        config.collect_all_json_strings,
        json_keys,
        config.detect_references,
    )


def get_cached_prepared(
    path: Path, file_type: str, config: WordCloudConfig
) -> tuple[Optional[tuple], Optional[Dict[str, object]]]:
    if not CACHE_ENABLED:
        return None, None
    try:
        key = build_token_cache_key(path, file_type, config)
    except OSError:
        return None, None
    entry = TOKEN_CACHE.get(key)
    if entry is not None:
        TOKEN_CACHE.move_to_end(key)
        return key, entry
    return key, None


def store_cache_entry(cache_key: Optional[tuple], entry: Dict[str, object]) -> None:
    if not CACHE_ENABLED or cache_key is None:
        return
    if "tokens" not in entry or "references" not in entry:
        return
    TOKEN_CACHE[cache_key] = entry
    TOKEN_CACHE.move_to_end(cache_key)
    while len(TOKEN_CACHE) > CACHE_CAPACITY:
        TOKEN_CACHE.popitem(last=False)


def build_analysis_payload(
    stats: Dict[str, WordCountStat],
    final_counts: Dict[str, int],
    references: Iterable[str],
) -> Dict[str, Any]:
    sorted_stats = sorted(stats.values(), key=lambda stat: stat.final_count, reverse=True)
    words_payload = [
        {
            "text": stat.key,
            "baseCount": stat.base_count,
            "referenceBonus": stat.reference_bonus,
            "bigramCount": stat.bigram_count,
            "boostMultiplier": stat.boost_multiplier,
            "manualAdjustment": stat.manual_adjustment,
            "finalCount": stat.final_count,
        }
        for stat in sorted_stats
    ]

    total_tokens = sum(stat.base_count for stat in stats.values())
    final_total = sum(final_counts.values())
    reference_counter = Counter(references)

    return {
        "totalTokens": int(total_tokens),
        "totalFinal": int(final_total),
        "uniqueTokens": len(stats),
        "referenceMatches": sum(reference_counter.values()),
        "referenceCounts": dict(reference_counter),
        "words": words_payload,
    }


def resolve_input_path(path_str: str) -> Path:
    candidate = (BASE_DIR / path_str).resolve() if not Path(path_str).is_absolute() else Path(path_str).resolve()
    if BASE_DIR not in candidate.parents and candidate != BASE_DIR:
        raise ValueError("Input path must stay within the project directory")
    if not candidate.exists():
        raise FileNotFoundError(candidate)
    return candidate


@app.get("/")
def index() -> str:
    return render_template(
        "index.html",
        stop_groups=list(STOP_GROUPS.keys()),
        default_palette=DEFAULT_PALETTE,
        default_font="Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial",
        theme_presets=THEME_PRESETS,
    )


@app.post("/api/upload")
def upload() -> Any:
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename) or f"upload-{int(time.time())}.json"
    timestamp = int(time.time())
    stored_name = f"{timestamp}-{filename}"
    destination = UPLOAD_DIR / stored_name
    file.save(destination)

    relative_path = destination.relative_to(BASE_DIR)
    return jsonify({
        "jsonPath": str(relative_path),
        "filename": filename,
        "stored": str(destination),
    })


@app.post("/api/generate")
def generate() -> Any:
    if request.mimetype == "application/json":
        payload = request.get_json(silent=True) or {}
        supplementary_form = {}
    else:
        payload = {}
        supplementary_form = request.form.to_dict(flat=True)
        if "config" in supplementary_form:
            try:
                payload = json.loads(supplementary_form["config"])
            except json.JSONDecodeError:
                payload = {}

    json_path = payload.get("jsonPath") or supplementary_form.get("jsonPath")
    if not json_path:
        return jsonify({"error": "jsonPath missing"}), 400

    try:
        path = resolve_input_path(json_path)
    except FileNotFoundError:
        return jsonify({"error": f"Input file not found: {json_path}"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    config = build_config(payload)
    file_type = str(payload.get("fileType", "auto")).lower()
    if file_type not in {"auto", "json", "text"}:
        file_type = "auto"
    if file_type == "auto":
        file_type = None

    resolved_kind = file_type or ("json" if path.suffix.lower() == ".json" else "text")

    skip_cache = bool(payload.get("skipCache"))
    use_cache = CACHE_ENABLED and not skip_cache
    cache_key: Optional[tuple] = None
    prepared_entry: Optional[Dict[str, object]] = None

    if use_cache:
        cache_key, prepared_entry = get_cached_prepared(path, resolved_kind, config)

    if prepared_entry is None and use_cache:
        prepared_entry = {}

    words, stats, raw_counts, references = generate_words_and_stats_from_file(
        path,
        config=config,
        file_type=file_type,
        prepared=prepared_entry if use_cache else None,
    )

    if use_cache and prepared_entry is not None:
        store_cache_entry(cache_key, prepared_entry)

    analysis = build_analysis_payload(stats, raw_counts, references)

    if payload.get("analysisOnly"):
        return jsonify({"analysis": analysis})

    if payload.get("returnHtml"):
        html = render_html(
            words,
            palette=payload.get("palette", DEFAULT_PALETTE),
            width=int(payload.get("width", 1920)),
            height=int(payload.get("height", 1080)),
            title=payload.get("title", "Holy Shift — Portfolio Word Cloud (Muted)"),
            heading=payload.get("heading"),
            font_family=payload.get("fontFamily", "Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial"),
        )
        return jsonify({"words": words, "html": html, "analysis": analysis})

    return jsonify({"words": words, "analysis": analysis})


if __name__ == "__main__":
    app.run(debug=True)
